# 微信 <-> Claude Code 桥接服务

通过微信直接与 Claude Code 对话。微信发消息 → 自动调用 Claude Code → 回复结果到微信。

## 架构

```
微信用户 ──> 微信服务器 ──> [getUpdates 长轮询] ──> bridge ──> claude-internal -p
                                                                      ↓
微信用户 <── 微信服务器 <── [sendMessage]         <── bridge <── Claude 回复
```

## 前提条件

- Node.js >= 22
- `claude-internal` CLI 已全局安装（或通过 `CLAUDE_CLI` 环境变量指定其他命令名）
- iOS 微信 8.0.70+（目前仅支持 1:1 私聊）

## 安装

```bash
cd ~/MF/github/game/wechat
npm install
```

## 运行

```bash
# 1. 先测试网络连通性
npm run test:api

# 2. 首次运行（自动弹出二维码，用微信扫码登录）
npm run dev

# 3. 强制重新登录
npm run login

# 4. 编译后运行（生产模式）
npm run build
npm start
```

首次运行时终端会显示一个二维码，用微信扫码并在手机上确认授权。登录成功后凭据保存在 `credentials.json`，下次启动会自动加载。

## 微信中可用的命令

| 命令 | 说明 |
|------|------|
| `/new` 或 `/reset` | 开启新对话（清除上下文） |
| `/help` | 显示帮助 |
| 直接发文本 | 与 Claude 对话 |

每个微信用户有独立的 Claude 会话，支持多轮对话，30 分钟无活动自动重置。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CLAUDE_CLI` | `claude-internal` | Claude Code CLI 命令名 |

## 项目结构

```
src/
├── index.ts          # 入口：检测凭据 → 引导登录 → 启动服务
├── auth.ts           # QR 扫码登录，凭据持久化
├── bridge.ts         # 核心桥接：长轮询收消息 → 调 Claude → 回复
├── claude.ts         # Claude Code 会话管理（按用户维护独立 session）
├── weixin-api.ts     # 微信 HTTP API（自带重试机制，独立实现不依赖 OpenClaw）
├── types.ts          # 微信 API 类型定义
└── test-api.ts       # API 连通性测试
```

## 故障排查

### `fetch failed` / `ConnectTimeoutError`

网络连接超时，程序已内置自动重试（最多 3 次，指数退避）。如果持续失败：

```bash
# 确认能访问微信 API
curl "https://ilinkai.weixin.qq.com/ilink/bot/get_bot_qrcode?bot_type=3"
```

### 会话过期 (errcode -14)

微信登录凭据过期，需要重新扫码：

```bash
npm run login
```

## 注意事项

- 微信消息内容经过腾讯服务器中转
- 单条回复超过 4000 字符会自动分段发送
- 语音消息会使用微信的语音转文字结果
- 引用消息会带上引用上下文
