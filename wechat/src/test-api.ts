/**
 * 快速测试：验证能否连通微信 API 获取二维码
 */
import { fetchQRCode } from "./weixin-api.js";

async function test() {
  console.log("🧪 测试微信 API 连通性...\n");
  try {
    const qr = await fetchQRCode();
    console.log("✅ 获取二维码成功!");
    console.log(`   qrcode: ${qr.qrcode}`);
    console.log(`   链接: ${qr.qrcode_img_content}`);
  } catch (err) {
    console.error("❌ 连接失败:", err);
    process.exit(1);
  }
}

test();
