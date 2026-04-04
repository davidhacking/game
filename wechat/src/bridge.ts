/**
 * 微信消息监听 + Claude Code 桥接
 * 长轮询 getUpdates -> 解析消息 -> 调用 Claude -> sendMessage 回复
 */
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { getUpdates, sendMessage } from "./weixin-api.js";
import { askClaude, clearSession, cleanupSessions } from "./claude.js";
import { isChessCommand, hasActiveGame, handleChessCommand, cleanupGames } from "./chess-game.js";
import type { AccountCredentials, WeixinMessage } from "./types.js";
import { MessageType, MessageItemType, MessageState } from "./types.js";

const MAX_CONSECUTIVE_FAILURES = 5;
const BACKOFF_DELAY_MS = 30_000;
const RETRY_DELAY_MS = 2_000;

/** contextToken 缓存: userId -> token */
const contextTokens = new Map<string, string>();

// ---------------------------------------------------------------------------
// 同步游标持久化 — 重启后能从上次位置继续收消息，不丢不重复
// ---------------------------------------------------------------------------

const DATA_DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "data");
const SYNC_BUF_FILE = path.join(DATA_DIR, "sync_buf.txt");
const CONTEXT_TOKENS_FILE = path.join(DATA_DIR, "context_tokens.json");
const PROCESSED_IDS_FILE = path.join(DATA_DIR, "processed_ids.json");

/** 最多记住多少条已处理消息（防止文件无限增长） */
const MAX_PROCESSED_IDS = 500;

function ensureDataDir(): void {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
}

function loadSyncBuf(): string {
  try {
    if (fs.existsSync(SYNC_BUF_FILE)) {
      return fs.readFileSync(SYNC_BUF_FILE, "utf-8").trim();
    }
  } catch { /* ignore */ }
  return "";
}

function saveSyncBuf(buf: string): void {
  ensureDataDir();
  fs.writeFileSync(SYNC_BUF_FILE, buf, "utf-8");
}

function loadContextTokens(): void {
  try {
    if (fs.existsSync(CONTEXT_TOKENS_FILE)) {
      const data = JSON.parse(fs.readFileSync(CONTEXT_TOKENS_FILE, "utf-8")) as Record<string, string>;
      for (const [k, v] of Object.entries(data)) {
        contextTokens.set(k, v);
      }
      console.log(`[Bridge] 已恢复 ${contextTokens.size} 个 contextToken`);
    }
  } catch { /* ignore */ }
}

function saveContextTokens(): void {
  ensureDataDir();
  const data: Record<string, string> = {};
  for (const [k, v] of contextTokens) {
    data[k] = v;
  }
  fs.writeFileSync(CONTEXT_TOKENS_FILE, JSON.stringify(data, null, 2), "utf-8");
}

// ---------------------------------------------------------------------------
// 消息去重 — 防止重启后重复处理已回复过的消息
// ---------------------------------------------------------------------------

/** 已处理的消息 ID 集合 (message_id 或 seq) */
const processedIds = new Set<string>();

function loadProcessedIds(): void {
  try {
    if (fs.existsSync(PROCESSED_IDS_FILE)) {
      const arr = JSON.parse(fs.readFileSync(PROCESSED_IDS_FILE, "utf-8")) as string[];
      for (const id of arr) processedIds.add(id);
      console.log(`[Bridge] 已恢复 ${processedIds.size} 条已处理消息 ID`);
    }
  } catch { /* ignore */ }
}

function saveProcessedIds(): void {
  ensureDataDir();
  // 只保留最近的 N 条，防止无限增长
  const arr = [...processedIds];
  const trimmed = arr.length > MAX_PROCESSED_IDS ? arr.slice(arr.length - MAX_PROCESSED_IDS) : arr;
  fs.writeFileSync(PROCESSED_IDS_FILE, JSON.stringify(trimmed), "utf-8");
}

/** 生成消息的唯一标识：优先 message_id，其次 seq，最后用 from+timestamp 兜底 */
function getMsgDedupeKey(msg: WeixinMessage): string {
  if (msg.message_id != null) return `mid:${msg.message_id}`;
  if (msg.seq != null) return `seq:${msg.seq}`;
  return `ts:${msg.from_user_id ?? ""}:${msg.create_time_ms ?? 0}`;
}

function isProcessed(key: string): boolean {
  return processedIds.has(key);
}

function markProcessed(key: string): void {
  processedIds.add(key);
  // 超过上限时清理旧的
  if (processedIds.size > MAX_PROCESSED_IDS * 1.2) {
    const arr = [...processedIds];
    const toRemove = arr.slice(0, arr.length - MAX_PROCESSED_IDS);
    for (const id of toRemove) processedIds.delete(id);
  }
  saveProcessedIds();
}

function generateClientId(): string {
  return `wx-claude:${Date.now()}-${crypto.randomBytes(4).toString("hex")}`;
}

/** 从消息中提取文本内容 */
function extractText(msg: WeixinMessage): string {
  if (!msg.item_list?.length) return "";
  for (const item of msg.item_list) {
    if (item.type === MessageItemType.TEXT && item.text_item?.text) {
      // 处理引用消息
      const ref = item.ref_msg;
      if (ref?.title) {
        return `[引用: ${ref.title}]\n${item.text_item.text}`;
      }
      return item.text_item.text;
    }
    // 语音转文字
    if (item.type === MessageItemType.VOICE && item.voice_item?.text) {
      return item.voice_item.text;
    }
  }
  return "";
}

/** 发送文本回复给微信用户 */
async function sendTextReply(
  creds: AccountCredentials,
  toUserId: string,
  text: string,
  contextToken?: string,
): Promise<void> {
  // 微信单条消息有长度限制，超过 4000 字符需要分段发送
  const MAX_CHUNK = 4000;
  const chunks: string[] = [];

  if (text.length <= MAX_CHUNK) {
    chunks.push(text);
  } else {
    // 按换行符分段
    let remaining = text;
    while (remaining.length > MAX_CHUNK) {
      let splitIdx = remaining.lastIndexOf("\n", MAX_CHUNK);
      if (splitIdx <= 0) splitIdx = MAX_CHUNK;
      chunks.push(remaining.substring(0, splitIdx));
      remaining = remaining.substring(splitIdx).trimStart();
    }
    if (remaining) chunks.push(remaining);
  }

  for (const chunk of chunks) {
    const body = {
      msg: {
        from_user_id: "",
        to_user_id: toUserId,
        client_id: generateClientId(),
        message_type: MessageType.BOT,
        message_state: MessageState.FINISH,
        item_list: [{ type: MessageItemType.TEXT, text_item: { text: chunk } }],
        context_token: contextToken,
      },
    };
    console.log(`[sendTextReply] to=${toUserId.substring(0, 12)}... context_token=${contextToken ? contextToken.substring(0, 20) + "..." : "NONE"}`);
    const resp = await sendMessage({
      baseUrl: creds.baseUrl,
      token: creds.token,
      body,
    });
    console.log(`[sendTextReply] 服务端响应: ${resp.substring(0, 200)}`);
  }
}

/** 处理收到的用户消息 */
async function handleIncomingMessage(
  msg: WeixinMessage,
  creds: AccountCredentials,
): Promise<void> {
  // 只处理用户发来的消息
  if (msg.message_type !== MessageType.USER) return;

  const fromUserId = msg.from_user_id ?? "";
  if (!fromUserId) return;

  // 消息去重：跳过已处理过的消息（防止重启后重复回复）
  const dedupeKey = getMsgDedupeKey(msg);
  if (isProcessed(dedupeKey)) {
    console.log(`[Bridge] 跳过已处理消息: ${dedupeKey}`);
    return;
  }

  // 优先使用当前消息携带的 context_token（最新鲜），否则用缓存
  const msgContextToken = msg.context_token;
  if (msgContextToken) {
    contextTokens.set(fromUserId, msgContextToken);
    saveContextTokens();
  }
  const contextToken = msgContextToken ?? contextTokens.get(fromUserId);

  const text = extractText(msg);
  if (!text) {
    console.log(`[Bridge] 收到非文本消息，跳过 (from: ${fromUserId.substring(0, 8)}...)`);
    return;
  }

  console.log(`\n📩 收到消息: [${fromUserId.substring(0, 8)}...] ${text.substring(0, 100)}`);
  console.log(`[Bridge] context_token: ${contextToken ? contextToken.substring(0, 20) + "..." : "NONE"} (来源: ${msgContextToken ? "当前消息" : "缓存"})`);

  // 特殊命令处理
  if (text.trim() === "/new" || text.trim() === "/reset") {
    clearSession(fromUserId);
    await sendTextReply(creds, fromUserId, "🔄 已开启新对话", contextToken);
    markProcessed(dedupeKey);
    return;
  }

  if (text.trim() === "/help") {
    await sendTextReply(
      creds,
      fromUserId,
      "🤖 微信 Claude 助手\n\n可用命令：\n/new - 开启新对话\n/reset - 重置会话\n/chess - 开始象棋对弈\n/board - 显示棋盘\n/resign - 认输\n/help - 显示帮助\n\n直接发送消息即可与 Claude 对话\n直接输入走法（如 b0c2）即可下棋",
      contextToken,
    );
    markProcessed(dedupeKey);
    return;
  }

  // 象棋命令：直接处理，不走 Claude
  if (isChessCommand(text) || hasActiveGame(fromUserId)) {
    // 如果有进行中的棋局，走法格式的消息当象棋处理
    const trimmed = text.trim().toLowerCase();
    const isMove = /^[a-i][0-9][a-i][0-9]$/.test(trimmed);

    if (isChessCommand(text) || (hasActiveGame(fromUserId) && isMove)) {
      try {
        const reply = await handleChessCommand(fromUserId, text);
        await sendTextReply(creds, fromUserId, reply, contextToken);
        markProcessed(dedupeKey);
        console.log(`♟ 象棋回复 [${fromUserId.substring(0, 8)}...]`);
      } catch (err) {
        console.error(`❌ 象棋处理失败:`, err);
        await sendTextReply(creds, fromUserId, `象棋引擎错误: ${err instanceof Error ? err.message : String(err)}`, contextToken);
        markProcessed(dedupeKey);
      }
      return;
    }
  }

  // 调用 Claude Code
  try {
    const reply = await askClaude(fromUserId, text);
    // 回复时再取一次最新的 contextToken（可能在等待 Claude 回复期间又收到了新消息更新了 token）
    const latestToken = contextTokens.get(fromUserId) ?? contextToken;
    await sendTextReply(creds, fromUserId, reply, latestToken);
    markProcessed(dedupeKey);
    console.log(`📤 已回复 [${fromUserId.substring(0, 8)}...]`);
  } catch (err) {
    console.error(`❌ Claude 处理失败:`, err);
    const latestToken = contextTokens.get(fromUserId) ?? contextToken;
    await sendTextReply(
      creds,
      fromUserId,
      `⚠️ 处理消息时出错: ${err instanceof Error ? err.message : String(err)}`,
      latestToken,
    );
    markProcessed(dedupeKey);
  }
}

/** 启动消息监听循环 */
export async function startBridge(creds: AccountCredentials): Promise<void> {
  console.log("\n🚀 微信 <-> Claude Code 桥接服务已启动");
  console.log(`   账号: ${creds.accountId}`);
  console.log(`   API: ${creds.baseUrl}`);
  console.log(`   数据目录: ${DATA_DIR}`);
  console.log("   等待微信消息...\n");

  // 从磁盘恢复状态
  let getUpdatesBuf = loadSyncBuf();
  if (getUpdatesBuf) {
    console.log(`[Bridge] 从磁盘恢复同步游标 (${getUpdatesBuf.length} bytes)`);
  }
  loadContextTokens();
  loadProcessedIds();
  let consecutiveFailures = 0;
  let nextTimeoutMs = 35_000;

  // 定期清理过期会话和棋局
  const cleanupTimer = setInterval(() => { cleanupSessions(); cleanupGames(); }, 5 * 60_000);

  const abortController = new AbortController();

  // 优雅退出：先保存状态再停止
  const cleanup = () => {
    console.log("\n🛑 正在停止服务...");
    if (getUpdatesBuf) {
      saveSyncBuf(getUpdatesBuf);
      console.log("[Bridge] 同步游标已保存");
    }
    saveContextTokens();
    console.log("[Bridge] contextToken 已保存");
    saveProcessedIds();
    console.log("[Bridge] 已处理消息 ID 已保存");
    abortController.abort();
    clearInterval(cleanupTimer);
  };
  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);

  while (!abortController.signal.aborted) {
    try {
      const resp = await getUpdates({
        baseUrl: creds.baseUrl,
        token: creds.token,
        get_updates_buf: getUpdatesBuf,
        timeoutMs: nextTimeoutMs,
      });

      // 更新长轮询超时
      if (resp.longpolling_timeout_ms && resp.longpolling_timeout_ms > 0) {
        nextTimeoutMs = resp.longpolling_timeout_ms;
      }

      // 检查 API 错误
      const isError = (resp.ret !== undefined && resp.ret !== 0) ||
                      (resp.errcode !== undefined && resp.errcode !== 0);
      if (isError) {
        consecutiveFailures++;
        console.error(`[Bridge] getUpdates 错误: ret=${resp.ret} errcode=${resp.errcode} errmsg=${resp.errmsg ?? ""}`);

        if (resp.errcode === -14) {
          console.error("❌ 会话过期，需要重新扫码登录！");
          break;
        }

        if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
          console.error(`[Bridge] 连续 ${MAX_CONSECUTIVE_FAILURES} 次失败，等待 30s...`);
          consecutiveFailures = 0;
          await sleep(BACKOFF_DELAY_MS, abortController.signal);
        } else {
          await sleep(RETRY_DELAY_MS, abortController.signal);
        }
        continue;
      }

      // 成功：重置失败计数
      consecutiveFailures = 0;

      // 更新同步游标并持久化
      if (resp.get_updates_buf) {
        getUpdatesBuf = resp.get_updates_buf;
        saveSyncBuf(getUpdatesBuf);
      }

      // 处理收到的消息
      const msgs = resp.msgs ?? [];
      for (const msg of msgs) {
        // 异步处理消息，不阻塞轮询
        handleIncomingMessage(msg, creds).catch((err) => {
          console.error("[Bridge] 消息处理异常:", err);
        });
      }
    } catch (err) {
      if (abortController.signal.aborted) break;

      consecutiveFailures++;
      console.error(`[Bridge] getUpdates 异常 (${consecutiveFailures}/${MAX_CONSECUTIVE_FAILURES}):`, err);

      if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
        console.error(`[Bridge] 连续失败，等待 30s...`);
        consecutiveFailures = 0;
        await sleep(BACKOFF_DELAY_MS, abortController.signal);
      } else {
        await sleep(RETRY_DELAY_MS, abortController.signal);
      }
    }
  }

  clearInterval(cleanupTimer);
  console.log("👋 桥接服务已停止");
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(t);
      resolve();
    }, { once: true });
  });
}
