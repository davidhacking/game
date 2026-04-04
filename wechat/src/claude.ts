/**
 * Claude Code 会话管理 — 通过 claude-internal CLI 的 -p 模式交互
 * 每个微信用户维护独立的会话 (session)
 *
 * 始终在项目根目录 (/Users/winnieshi/MF/github/game) 下启动 claude-internal，
 * 这样 CLI 会自动加载该目录下的 .claude/settings.json 和 CLAUDE.md 配置。
 */
import { spawn } from "node:child_process";
import path from "node:path";

/** 可配置的 CLI 命令名，默认 claude-internal */
const CLAUDE_CLI = process.env.CLAUDE_CLI ?? "claude-internal";

/** Claude Code 工作目录 — 即项目根目录，确保读取 .claude 和 CLAUDE.md */
const CLAUDE_CWD = process.env.CLAUDE_CWD ?? path.resolve("/Users/winnieshi/MF/github/game");

/** 微信场景的系统提示词 — 定义助手人设，通过 --append-system-prompt 追加 */
const WECHAT_SYSTEM_PROMPT = `你是 davidshi 的个人助手，正在通过微信和用户对话。

【重要：交互环境约束】
用户在手机微信里跟你聊天，他看不到终端，不能运行命令，不能打开浏览器链接，不能看到文件内容。
你和用户之间唯一的交互方式就是微信文字消息。因此：
- 绝对不要让用户去"运行xxx命令"、"打开xxx文件"、"访问xxx链接"
- 如果用户想玩游戏（比如中国象棋），你要直接在对话中和他玩，用文字描述棋盘、接收他的走法、计算你的走法
- 如果需要执行代码或查看结果，你自己在后台执行，只把最终结果用文字告诉用户
- 回复要简洁，适合手机阅读，避免过长的代码块

【人设】
- 用简洁友好的中文回复，适合微信聊天的风格
- 首次打招呼时说"你好，我是 davidshi 的个人助手，开始我们的协助之旅吧"
- 你可以帮用户回答问题、写代码、分析问题、玩游戏、提供建议等`;

interface Session {
  sessionId?: string;
  lastActiveAt: number;
}

/** 会话存储：userId -> session */
const sessions = new Map<string, Session>();

/** 会话过期时间：30 分钟 */
const SESSION_TTL_MS = 30 * 60 * 1000;

function getOrCreateSession(userId: string): Session {
  let session = sessions.get(userId);
  if (session && Date.now() - session.lastActiveAt < SESSION_TTL_MS) {
    session.lastActiveAt = Date.now();
    return session;
  }
  session = { lastActiveAt: Date.now() };
  sessions.set(userId, session);
  return session;
}

/**
 * 调用 Claude Code CLI (JSON 格式)，返回回复文本
 * 自动维护 session_id 实现多轮对话
 *
 * 关键：cwd 固定为项目根目录，这样 claude-internal 会：
 *   1. 读取 .claude/settings.json 中的配置
 *   2. 读取 CLAUDE.md 中的项目指令
 *   3. 在项目上下文中执行（能访问项目代码）
 */
export async function askClaude(userId: string, message: string): Promise<string> {
  const session = getOrCreateSession(userId);

  const args: string[] = [
    "-p", message,
    "--output-format", "json",
    "--append-system-prompt", WECHAT_SYSTEM_PROMPT,
  ];

  // 如果有已有 session，继续对话
  if (session.sessionId) {
    args.push("--resume", session.sessionId);
  }

  console.log(`[Claude] 用户 ${userId.substring(0, 8)}... -> "${message.substring(0, 80)}"`);
  console.log(`[Claude] 工作目录: ${CLAUDE_CWD}`);

  return new Promise<string>((resolve, reject) => {
    let stdout = "";
    let stderr = "";

    const proc = spawn(CLAUDE_CLI, args, {
      cwd: CLAUDE_CWD,              // ← 在项目根目录下启动
      stdio: ["pipe", "pipe", "pipe"],
      env: { ...process.env },
      timeout: 300_000, // 5 分钟超时
    });

    proc.stdout.on("data", (data: Buffer) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data: Buffer) => {
      stderr += data.toString();
    });

    proc.on("close", (code: number | null) => {
      try {
        const result = JSON.parse(stdout);

        // 提取 session_id 用于后续对话
        if (result.session_id) {
          session.sessionId = result.session_id;
          console.log(`[Claude] 会话 ID: ${session.sessionId}`);
        }

        // 提取文本回复（JSON 格式的 result 字段）
        const text = result.result ?? "";
        if (text) {
          console.log(`[Claude] 回复 (${text.length} 字): "${text.substring(0, 100)}..."`);
          resolve(text);
        } else if (result.is_error) {
          reject(new Error(`Claude 返回错误: ${JSON.stringify(result)}`));
        } else {
          resolve("（Claude 没有返回内容）");
        }
      } catch {
        // JSON 解析失败，回退到原始输出
        const text = stdout.trim();
        if (text) {
          resolve(text);
        } else if (code !== 0) {
          reject(new Error(`Claude 错误 (code=${code}): ${stderr.substring(0, 500)}`));
        } else {
          resolve("（Claude 没有返回内容）");
        }
      }
    });

    proc.on("error", (err: Error) => {
      reject(new Error(`无法启动 Claude CLI (${CLAUDE_CLI}): ${err.message}`));
    });
  });
}

/** 清除用户会话（开启新对话） */
export function clearSession(userId: string): void {
  sessions.delete(userId);
  console.log(`[Claude] 已清除用户 ${userId.substring(0, 8)}... 的会话`);
}

/** 清理所有过期会话 */
export function cleanupSessions(): void {
  const now = Date.now();
  for (const [userId, session] of sessions) {
    if (now - session.lastActiveAt > SESSION_TTL_MS) {
      sessions.delete(userId);
    }
  }
}
