/**
 * 微信 QR 扫码登录 — 独立实现，不依赖 OpenClaw
 */
import fs from "node:fs";
import path from "node:path";
import { fetchQRCode, pollQRStatus } from "./weixin-api.js";
import type { AccountCredentials } from "./types.js";

const FIXED_QR_BASE_URL = "https://ilinkai.weixin.qq.com";
const MAX_QR_REFRESH = 3;
const CREDENTIALS_FILE = "credentials.json";

export function getCredentialsPath(): string {
  return path.join(process.cwd(), CREDENTIALS_FILE);
}

/** 从本地文件加载已保存的凭据 */
export function loadCredentials(): AccountCredentials | null {
  const p = getCredentialsPath();
  try {
    if (fs.existsSync(p)) {
      return JSON.parse(fs.readFileSync(p, "utf-8")) as AccountCredentials;
    }
  } catch { /* ignore */ }
  return null;
}

/** 保存凭据到本地文件 */
export function saveCredentials(creds: AccountCredentials): void {
  const p = getCredentialsPath();
  fs.writeFileSync(p, JSON.stringify(creds, null, 2), "utf-8");
  try { fs.chmodSync(p, 0o600); } catch { /* best-effort */ }
  console.log(`✅ 凭据已保存到 ${p}`);
}

/** 交互式 QR 扫码登录流程 */
export async function loginWithQR(): Promise<AccountCredentials> {
  console.log("🔄 正在获取微信登录二维码...\n");
  let qr = await fetchQRCode();
  console.log(`请用微信扫描以下二维码：\n`);

  // 显示 QR 码
  try {
    const qrterm = await import("qrcode-terminal");
    await new Promise<void>((resolve) => {
      qrterm.default.generate(qr.qrcode_img_content, { small: true }, (code: string) => {
        console.log(code);
        resolve();
      });
    });
  } catch {
    // fallback
  }
  console.log(`如果二维码未显示，请在浏览器打开：\n${qr.qrcode_img_content}\n`);

  let currentBaseUrl = FIXED_QR_BASE_URL;
  let refreshCount = 1;
  let scannedShown = false;
  const deadline = Date.now() + 480_000;

  while (Date.now() < deadline) {
    const status = await pollQRStatus(currentBaseUrl, qr.qrcode);

    switch (status.status) {
      case "wait":
        break;
      case "scaned":
        if (!scannedShown) {
          console.log("👀 已扫码，请在微信上确认...");
          scannedShown = true;
        }
        break;
      case "scaned_but_redirect":
        if (status.redirect_host) {
          currentBaseUrl = `https://${status.redirect_host}`;
          console.log(`🔀 IDC 重定向到 ${currentBaseUrl}`);
        }
        break;
      case "expired":
        refreshCount++;
        if (refreshCount > MAX_QR_REFRESH) {
          throw new Error("二维码多次过期，请重新运行程序。");
        }
        console.log(`\n⏳ 二维码过期，正在刷新 (${refreshCount}/${MAX_QR_REFRESH})...\n`);
        qr = await fetchQRCode();
        scannedShown = false;
        try {
          const qrterm = await import("qrcode-terminal");
          qrterm.default.generate(qr.qrcode_img_content, { small: true });
        } catch { /* ignore */ }
        console.log(`浏览器打开：${qr.qrcode_img_content}\n`);
        break;
      case "confirmed": {
        if (!status.ilink_bot_id || !status.bot_token) {
          throw new Error("登录确认但缺少必要信息 (bot_id 或 bot_token)");
        }
        const creds: AccountCredentials = {
          token: status.bot_token,
          baseUrl: status.baseurl || FIXED_QR_BASE_URL,
          accountId: status.ilink_bot_id,
          userId: status.ilink_user_id,
          savedAt: new Date().toISOString(),
        };
        saveCredentials(creds);
        console.log("\n✅ 微信登录成功！\n");
        return creds;
      }
    }

    await new Promise((r) => setTimeout(r, 1000));
  }

  throw new Error("登录超时，请重试。");
}
