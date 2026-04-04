/**
 * 象棋游戏管理 — 通过 Python 子进程调用 chinese_chess/chess_engine.py
 * 每个微信用户维护独立的棋局
 */
import { execFile } from "node:child_process";
import path from "node:path";

const PYTHON = process.env.PYTHON ?? "python3";
const ENGINE_PATH = path.resolve("/Users/winnieshi/MF/github/game/chinese_chess/chess_engine.py");
const ENGINE_CWD = path.dirname(ENGINE_PATH);

// ---------------------------------------------------------------------------
// 棋盘渲染：将 "." 替换为 "~"，微信中宽度更接近字母，对齐更好
// ---------------------------------------------------------------------------

/** 将 ASCII 棋盘的空位 "." 替换为 "~" 以适配微信显示 */
function boardToWechat(ascii: string): string {
  return ascii.replace(/\./g, "~");
}

interface EngineResult {
  ok: boolean;
  error?: string;
  fen?: string;
  board?: string;
  move?: string | null;
  in_check?: boolean;
  checkmate?: boolean;
  winner?: string | null;
  red_moves?: string[];
  legal_moves?: string[];
}

interface GameState {
  fen: string;
  redTurn: boolean;       // 当前该谁走
  playerIsRed: boolean;   // 用户是红方还是黑方
  aiDepth: number;
  moveHistory: string[];  // 走法历史
  lastActiveAt: number;
}

/** 每个用户的棋局: userId -> GameState */
const games = new Map<string, GameState>();

/** 棋局超时: 2 小时 */
const GAME_TTL_MS = 2 * 60 * 60 * 1000;

/** 调用 Python 引擎 */
function callEngine(cmd: Record<string, unknown>): Promise<EngineResult> {
  return new Promise((resolve, reject) => {
    const proc = execFile(PYTHON, [ENGINE_PATH], {
      cwd: ENGINE_CWD,
      timeout: 60_000,
    }, (err, stdout, stderr) => {
      if (err) {
        reject(new Error(`引擎错误: ${err.message}\n${stderr}`));
        return;
      }
      try {
        resolve(JSON.parse(stdout) as EngineResult);
      } catch {
        reject(new Error(`引擎输出解析失败: ${stdout}`));
      }
    });
    proc.stdin?.write(JSON.stringify(cmd));
    proc.stdin?.end();
  });
}

/** 判断是否是象棋命令 */
export function isChessCommand(text: string): boolean {
  const t = text.trim().toLowerCase();
  // 明确的命令
  if (t.startsWith("/chess") || t.startsWith("/move") ||
      t.startsWith("/board") || t.startsWith("/resign") ||
      t.startsWith("/quit")) {
    return true;
  }
  // 走棋格式: 4个字符如 b0c2, e3e4
  if (/^[a-i][0-9][a-i][0-9]$/.test(t)) {
    return true;
  }
  return false;
}

/** 检查用户是否有进行中的棋局 */
export function hasActiveGame(userId: string): boolean {
  const game = games.get(userId);
  if (!game) return false;
  if (Date.now() - game.lastActiveAt > GAME_TTL_MS) {
    games.delete(userId);
    return false;
  }
  return true;
}

/** 处理象棋命令，返回回复文本 */
export async function handleChessCommand(userId: string, text: string): Promise<string> {
  const t = text.trim().toLowerCase();

  // /chess — 开新局
  if (t === "/chess" || t.startsWith("/chess ")) {
    return await startNewGame(userId);
  }

  // /board — 显示棋盘
  if (t === "/board") {
    return showBoard(userId);
  }

  // /resign 或 /quit — 认输
  if (t === "/resign" || t === "/quit") {
    return resignGame(userId);
  }

  // 走棋: 4字符 ICCS 格式
  if (/^[a-i][0-9][a-i][0-9]$/.test(t)) {
    return await makeMove(userId, t);
  }

  // /move xxxx
  if (t.startsWith("/move ")) {
    const move = t.substring(6).trim().toLowerCase();
    if (/^[a-i][0-9][a-i][0-9]$/.test(move)) {
      return await makeMove(userId, move);
    }
    return "走法格式错误，请用 ICCS 格式如: e3e4, b0c2";
  }

  return "未知象棋命令。可用:\n/chess - 开新局\n/board - 显示棋盘\n/resign - 认输\n直接输入走法如 b0c2";
}

/** 开新局 */
async function startNewGame(userId: string): Promise<string> {
  const result = await callEngine({ action: "new" });
  if (!result.ok) return `开局失败: ${result.error}`;

  const game: GameState = {
    fen: result.fen!,
    redTurn: true,
    playerIsRed: true,
    aiDepth: 3,
    moveHistory: [],
    lastActiveAt: Date.now(),
  };
  games.set(userId, game);

  return `♟ 象棋对弈开始！
你执红方（小写），AI 执黑方（大写）
红方先行，请输入走法（如 b0c2）

${boardToWechat(result.board!)}

提示: /board 看棋盘, /resign 认输`;
}

/** 用户走棋 + AI 回应 */
async function makeMove(userId: string, move: string): Promise<string> {
  const game = games.get(userId);
  if (!game) {
    return "没有进行中的棋局，发 /chess 开新局";
  }
  game.lastActiveAt = Date.now();

  // 1. 用户走棋
  const moveResult = await callEngine({
    action: "move",
    fen: game.fen,
    move,
    red_turn: game.playerIsRed,
  });

  if (!moveResult.ok) {
    return `非法走法 ${move}: ${moveResult.error}\n\n发 /board 查看棋盘`;
  }

  game.fen = moveResult.fen!;
  game.moveHistory.push(move);

  // 检查用户走完后是否将杀
  if (moveResult.checkmate) {
    const winner = game.playerIsRed ? "红方（你）" : "黑方（你）";
    const reply = `你走: ${move}\n\n${boardToWechat(moveResult.board!)}\n\n🎉 ${winner}获胜！对方被将杀！\n\n发 /chess 再来一局`;
    games.delete(userId);
    return reply;
  }

  // 2. AI 走棋
  const aiResult = await callEngine({
    action: "ai_move",
    fen: game.fen,
    red_turn: !game.playerIsRed,
    depth: game.aiDepth,
  });

  if (!aiResult.ok) {
    return `AI 计算出错: ${aiResult.error}`;
  }

  if (!aiResult.move) {
    // AI 无路可走
    const winner = game.playerIsRed ? "红方（你）" : "黑方（你）";
    const reply = `你走: ${move}\nAI 无路可走\n\n${boardToWechat(aiResult.board!)}\n\n🎉 ${winner}获胜！\n\n发 /chess 再来一局`;
    games.delete(userId);
    return reply;
  }

  game.fen = aiResult.fen!;
  game.moveHistory.push(aiResult.move);

  let status = "";
  if (aiResult.checkmate) {
    const winner = game.playerIsRed ? "黑方（AI）" : "红方（AI）";
    status = `\n\n💀 ${winner}获胜！你被将杀了！\n\n发 /chess 再来一局`;
    games.delete(userId);
  } else if (aiResult.in_check) {
    status = "\n\n⚠️ 将军！";
  }

  const checkNote = moveResult.in_check ? " (将军!)" : "";

  return `你走: ${move}${checkNote}\nAI走: ${aiResult.move}\n\n${boardToWechat(aiResult.board!)}${status}`;
}

/** 显示棋盘 */
async function showBoard(userId: string): Promise<string> {
  const game = games.get(userId);
  if (!game) return "没有进行中的棋局，发 /chess 开新局";

  game.lastActiveAt = Date.now();
  const side = game.playerIsRed ? "红方（你走）" : "黑方（你走）";
  const history = game.moveHistory.length > 0
    ? `\n走法记录: ${game.moveHistory.join(" ")}`
    : "";

  try {
    const r = await callEngine({ action: "board", fen: game.fen, red_turn: game.playerIsRed });
    return `${side}${history}\n\n${boardToWechat(r.board!)}`;
  } catch {
    return "获取棋盘失败";
  }
}

/** 认输 */
function resignGame(userId: string): string {
  const game = games.get(userId);
  if (!game) return "没有进行中的棋局";

  games.delete(userId);
  return `🏳️ 你认输了！共 ${game.moveHistory.length} 步\n\n发 /chess 再来一局`;
}

/** 清理过期棋局 */
export function cleanupGames(): void {
  const now = Date.now();
  for (const [userId, game] of games) {
    if (now - game.lastActiveAt > GAME_TTL_MS) {
      games.delete(userId);
    }
  }
}
