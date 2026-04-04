#!/usr/bin/env node
/**
 * 微信 <-> Claude Code 桥接服务 入口
 *
 * 使用方式:
 *   npx tsx src/index.ts          # 首次运行会引导扫码登录
 *   npx tsx src/index.ts login    # 强制重新登录
 *   npx tsx src/index.ts start    # 直接启动（使用已保存的凭据）
 */
import fs from "node:fs";
import path from "node:path";
import { loadCredentials, loginWithQR } from "./auth.js";
import { startBridge } from "./bridge.js";

const PID_FILE = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "data", "bridge.pid");

function writePidFile(): void {
  const dir = path.dirname(PID_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(PID_FILE, String(process.pid), "utf-8");
  console.log(`[PID] ${process.pid} -> ${PID_FILE}`);
}

function removePidFile(): void {
  try { fs.unlinkSync(PID_FILE); } catch { /* ignore */ }
}

async function main() {
  const command = process.argv[2] ?? "auto";

  console.log("╔══════════════════════════════════════╗");
  console.log("║   微信 <-> Claude Code 桥接服务      ║");
  console.log("╚══════════════════════════════════════╝\n");

  let creds = loadCredentials();

  if (command === "login" || !creds) {
    if (command !== "login" && !creds) {
      console.log("未找到已保存的凭据，需要先登录。\n");
    }
    creds = await loginWithQR();
  } else {
    console.log(`已加载凭据 (账号: ${creds.accountId}, 保存于: ${creds.savedAt})`);
  }

  // 写入 PID 文件，供 restart.sh 使用
  writePidFile();
  process.on("exit", removePidFile);

  await startBridge(creds);
}

main().catch((err) => {
  console.error("\n💀 致命错误:", err);
  process.exit(1);
});
