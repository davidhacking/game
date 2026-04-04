/**
 * 微信 HTTP API — 从 openclaw-weixin 提取的核心 API 调用逻辑，不依赖 OpenClaw 框架
 */
import crypto from "node:crypto";
import type {
  GetUpdatesResp,
  SendMessageReq,
  QRCodeResponse,
  QRStatusResponse,
  BaseInfo,
} from "./types.js";

const ILINK_APP_ID = "bot";
const CHANNEL_VERSION = "2.1.6";
const FIXED_QR_BASE_URL = "https://ilinkai.weixin.qq.com";

// ---------------------------------------------------------------------------
// 通用 HTTP 工具
// ---------------------------------------------------------------------------

function randomWechatUin(): string {
  const uint32 = crypto.randomBytes(4).readUInt32BE(0);
  return Buffer.from(String(uint32), "utf-8").toString("base64");
}

function buildClientVersion(version: string): number {
  const parts = version.split(".").map((p) => parseInt(p, 10));
  return (((parts[0] ?? 0) & 0xff) << 16) | (((parts[1] ?? 0) & 0xff) << 8) | ((parts[2] ?? 0) & 0xff);
}

function ensureTrailingSlash(url: string): string {
  return url.endsWith("/") ? url : `${url}/`;
}

function buildBaseInfo(): BaseInfo {
  return { channel_version: CHANNEL_VERSION };
}

function buildHeaders(token?: string, body?: string): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    AuthorizationType: "ilink_bot_token",
    "X-WECHAT-UIN": randomWechatUin(),
    "iLink-App-Id": ILINK_APP_ID,
    "iLink-App-ClientVersion": String(buildClientVersion(CHANNEL_VERSION)),
  };
  if (body) {
    headers["Content-Length"] = String(Buffer.byteLength(body, "utf-8"));
  }
  if (token?.trim()) {
    headers.Authorization = `Bearer ${token.trim()}`;
  }
  return headers;
}

/** 带重试的 fetch 封装 */
async function fetchWithRetry(
  url: string,
  init: RequestInit,
  opts: { timeoutMs: number; retries?: number; label?: string },
): Promise<Response> {
  const maxRetries = opts.retries ?? 3;
  let lastError: Error | undefined;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), opts.timeoutMs);
    try {
      const res = await fetch(url, { ...init, signal: controller.signal });
      clearTimeout(t);
      return res;
    } catch (err) {
      clearTimeout(t);
      lastError = err instanceof Error ? err : new Error(String(err));
      const cause = (lastError as NodeJS.ErrnoException).cause as { code?: string } | undefined;
      const code = cause?.code ?? "";
      console.warn(
        `[${opts.label ?? "fetch"}] 第 ${attempt}/${maxRetries} 次请求失败: ${lastError.message}` +
        (code ? ` (${code})` : ""),
      );
      if (attempt < maxRetries) {
        // 指数退避：1s, 2s, 4s...
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
        await new Promise((r) => setTimeout(r, delay));
      }
    }
  }
  throw lastError!;
}

async function apiGet(baseUrl: string, endpoint: string, timeoutMs = 30_000): Promise<string> {
  const url = new URL(endpoint, ensureTrailingSlash(baseUrl)).toString();
  const res = await fetchWithRetry(url, {
    method: "GET",
    headers: {
      "iLink-App-Id": ILINK_APP_ID,
      "iLink-App-ClientVersion": String(buildClientVersion(CHANNEL_VERSION)),
    },
  }, { timeoutMs, label: `GET ${endpoint}` });
  const text = await res.text();
  if (!res.ok) throw new Error(`GET ${endpoint} ${res.status}: ${text}`);
  return text;
}

async function apiPost(
  baseUrl: string,
  endpoint: string,
  body: string,
  token?: string,
  timeoutMs = 15_000,
  retries = 1,
): Promise<string> {
  const url = new URL(endpoint, ensureTrailingSlash(baseUrl)).toString();
  const headers = buildHeaders(token, body);
  const res = await fetchWithRetry(url, {
    method: "POST",
    headers,
    body,
  }, { timeoutMs, retries, label: `POST ${endpoint}` });
  const text = await res.text();
  if (!res.ok) throw new Error(`POST ${endpoint} ${res.status}: ${text}`);
  return text;
}

// ---------------------------------------------------------------------------
// QR 登录 API
// ---------------------------------------------------------------------------

export async function fetchQRCode(botType = "3"): Promise<QRCodeResponse> {
  console.log(`[API] 正在请求二维码 (${FIXED_QR_BASE_URL})...`);
  const raw = await apiGet(
    FIXED_QR_BASE_URL,
    `ilink/bot/get_bot_qrcode?bot_type=${encodeURIComponent(botType)}`,
  );
  return JSON.parse(raw) as QRCodeResponse;
}

export async function pollQRStatus(
  baseUrl: string,
  qrcode: string,
  timeoutMs = 35_000,
): Promise<QRStatusResponse> {
  try {
    const url = new URL(
      `ilink/bot/get_qrcode_status?qrcode=${encodeURIComponent(qrcode)}`,
      ensureTrailingSlash(baseUrl),
    ).toString();
    // 长轮询不重试，超时直接返回 wait
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(url, {
        method: "GET",
        headers: {
          "iLink-App-Id": ILINK_APP_ID,
          "iLink-App-ClientVersion": String(buildClientVersion(CHANNEL_VERSION)),
        },
        signal: controller.signal,
      });
      clearTimeout(t);
      const text = await res.text();
      if (!res.ok) throw new Error(`pollQRStatus ${res.status}: ${text}`);
      return JSON.parse(text) as QRStatusResponse;
    } catch (err) {
      clearTimeout(t);
      throw err;
    }
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      return { status: "wait" };
    }
    console.warn(`[pollQRStatus] 网络错误，将重试: ${String(err)}`);
    return { status: "wait" };
  }
}

// ---------------------------------------------------------------------------
// 消息收发 API
// ---------------------------------------------------------------------------

/** 长轮询获取新消息 */
export async function getUpdates(params: {
  baseUrl: string;
  token?: string;
  get_updates_buf?: string;
  timeoutMs?: number;
}): Promise<GetUpdatesResp> {
  const timeout = params.timeoutMs ?? 35_000;
  try {
    const raw = await apiPost(
      params.baseUrl,
      "ilink/bot/getupdates",
      JSON.stringify({
        get_updates_buf: params.get_updates_buf ?? "",
        base_info: buildBaseInfo(),
      }),
      params.token,
      timeout,
      1, // 长轮询不重试
    );
    return JSON.parse(raw) as GetUpdatesResp;
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      return { ret: 0, msgs: [], get_updates_buf: params.get_updates_buf };
    }
    throw err;
  }
}

/** 发送文本消息，返回服务端原始响应 */
export async function sendMessage(params: {
  baseUrl: string;
  token?: string;
  body: SendMessageReq;
}): Promise<string> {
  const raw = await apiPost(
    params.baseUrl,
    "ilink/bot/sendmessage",
    JSON.stringify({ ...params.body, base_info: buildBaseInfo() }),
    params.token,
    15_000,
    3, // 发消息重试 3 次
  );
  return raw;
}
