# Chinese Chess (Xiangqi) Project - Comprehensive Analysis

## Project Overview

**Location:** `/Users/winnieshi/MF/github/game/`  
**Language:** Python (3.13+)  
**Framework:** Standard library + custom implementations (no external dependencies)  
**Total Lines:** 4,403 lines across 12 Python files

### Key Statistics
- Core modules: 4 (board, games, alpha_beta, main)
- Test files: 4 (test_moves, test_games, test_ai, test_self_play)
- Generators: 2 (gen_games, gen_endgames)
- Supporting: endgames, __init__

---

## 1. GEN_GAMES Module - Game Data Fetching

**File:** `/Users/winnieshi/MF/github/game/chinese_chess/gen_games.py` (228 lines)

### Purpose
Downloads professional game records from xqbase.com (象棋巫师棋谱仓库 - Elephant Wizard Game Repository), converts them to ICCS format, and generates a Python module with playable games.

### Function Signatures

#### `fetch_page(gameid: int) -> str | None`
- **URL Source:** `https://www.xqbase.com/xqbase/?gameid={gameid}`
- **Encoding:** GBK (site uses GBK encoding; decoded to UTF-8)
- **Headers:** User-Agent to avoid blocking
- **Timeout:** 15 seconds
- **Returns:** HTML page content or None on failure
- **Error Handling:** Catches and logs exceptions with friendly messages

```python
BASE_URL = "https://www.xqbase.com/xqbase/?gameid="
ENCODING = "gbk"
```

#### `parse_game(html: str, gameid: int) -> dict | None`
Extracts game metadata and moves from HTML using regex patterns.

**Extraction Details:**

1. **Moves Pattern:** `jsboard("",\s*"([^"]+)"\s*)`
   - Raw format: `"H2-E2 H9-G7 ..."`
   - Conversion: Remove hyphens, lowercase, split by whitespace
   - Filter: Only 4-character moves, discard if < 5 moves

2. **Title Pattern:** `<title>(.+?)\s*-\s*象棋巫师</title>`
   - Format: `"[Team] [Red Player] [Result] [Team] [Black Player]"`
   - Result Keywords: `先胜` (red wins), `先负` (red loses), `先和` (draw)
   - Maps to: `1-0`, `0-1`, `1/2-1/2`

3. **Event Pattern:** `<font size="2">(\d{4}年[^<]+(?:赛|杯|战|局)[^<]*)</font>`
   - Extracts year and tournament name
   - Keywords: 赛 (tournament), 杯 (cup), 战 (battle), 局 (match)

**Returns:**
```python
{
    "name": str,          # Full title with event
    "event": str,         # Tournament name
    "red": str,           # Red player name
    "black": str,         # Black player name
    "result": str,        # "1-0", "0-1", or "1/2-1/2"
    "moves": [str],       # List of ICCS moves like ["h2e2", "h9g7"]
    "url": str            # Direct link to game
}
```

#### `download_games(count=30, start_id=135, max_id=12000) -> list`
Main download loop with resilience features.

- **Default Parameters:**
  - Count: 30 games
  - Start ID: 135 (empirically chosen as first valid game)
  - Max ID: 12000 (safety limit)

- **Behavior:**
  - Downloads sequentially, trying each game ID
  - Tracks consecutive failures; stops after 20+ failures
  - Polite 0.5-second delay between requests
  - Resets failure counter on successful parse

#### `write_games_py(games: list, output_path="games.py") -> None`
Generates the `games.py` module with game data.

**Output Format:**
```python
"""中国象棋棋谱集 (ICCS 格式)
[documentation]
"""

GAMES = [
    {
        "name": "...",
        "red": "...",
        "black": "...",
        "result": "1-0",
        "url": "https://...",
        "moves": [
            "h2e2", "h9g7",
            "h0g2", "i9h9",
            ...
        ],
    },
    ...
]
```

- Escapes quotes in names
- Pairs moves for readability (2 per line)
- Includes source attribution

#### `main()`
CLI interface with argument parsing.

```bash
uv run python chinese_chess/gen_games.py [count] [start_id]
```

- **Args:**
  - `count`: Number of games to download (default: 30)
  - `start_id`: Starting gameid (default: 135)

- **Post-Download Validation:**
  - Automatically imports generated `games.py`
  - Runs each game through the Board simulator
  - Reports: Pass/fail count, step number of failure, error message
  - Ensures all games can be played to completion

### Output Location
- **Generated File:** `/Users/winnieshi/MF/github/game/chinese_chess/games.py`
- **Current Games in games.py:** 10 professional games
- **Validation:** All games verified playable

---

## 2. Project Structure Overview

### Directory Layout
```
chinese_chess/
├── __init__.py              (empty)
├── main.py                  (355 lines) - CLI menu & game modes
├── board.py                 (484 lines) - Game logic & board representation
├── games.py                 (1504 lines) - Game data (generated)
├── endgames.py              (27 lines) - Endgame puzzles
├── alpha_beta.py            (335 lines) - AI engine
├── gen_games.py             (228 lines) - Game downloader
├── gen_endgames.py          (322 lines) - Endgame generator
├── test_moves.py            (651 lines) - Movement validation tests
├── test_games.py            (111 lines) - Game replay tests
├── test_ai.py               (251 lines) - AI engine tests
└── test_self_play.py        (135 lines) - AI vs AI tests
```

### Key File Relationships

```
main.py (entry point)
    ↓
    ├── uses: board.Board
    ├── uses: games.GAMES
    └── uses: alpha_beta.ChessAI

board.py
    ├── INIT_BOARD (10×9 grid)
    ├── class Board:
    │   ├── move() - Apply moves
    │   ├── validate_move() - Check legality
    │   ├── generate_moves() - All legal moves
    │   └── display() - Show board state
    └── Piece constants: RED_PIECES, BLACK_PIECES

alpha_beta.py
    ├── evaluate() - Position evaluation
    ├── alphabeta() - Search algorithm
    └── class ChessAI:
        └── best_move() - Find best move

games.py
    └── GAMES = [list of game dicts]

endgames.py
    └── ENDGAMES = [list of puzzle dicts]
```

---

## 3. Coordinate System - ICCS (International Chinese Chess Standard)

### Axes
- **Columns:** `a` ~ `i` (left to right, 9 columns)
- **Rows:** `0` ~ `9` (red baseline to black baseline)
  - Row 0: Red team bottom line (帅/King for red)
  - Row 9: Black team top line (将/King for black)

### Internal Representation
- **Grid:** `grid[row][col]` where row 0 = black baseline, row 9 = red baseline
- **Conversion:** `ICCS row = 9 - internal row`

### Example Board Visualization
```
  a b c d e f g h i
9 R N B A K A B N R      大写 = 黑方 (Black)
8 . . . . . . . . .
7 . C . . . . . C .      R=车 N=马 B=象 A=士
6 P . P . P . P . P      K=将 C=炮 P=卒
5 . . . . . . . . .
  = = = = = = = = =      (River barrier)
4 . . . . . . . . .
3 p . p . p . p . p      小写 = 红方 (Red)
2 . c . . . . . c .      r=车 n=马 b=相 a=仕
1 . . . . . . . . .      k=帅 c=炮 p=兵
0 r n b a k a b n r
```

### Move Format
- **ICCS Move:** 4 characters: `[col][row][col][row]`
- **Examples:**
  - `b0c2` - Move from b0 to c2 (horse forward)
  - `h2e2` - Move from h2 to e2 (cannon/chariot)
  - `c9e7` - Black move (c9 to e7)

### Piece Encoding

| Red (小写) | Black (大写) | Name (English) | Name (中文) |
|-----------|-------------|---------|----------|
| `r` | `R` | Rook/Chariot | 车 |
| `n` | `N` | Knight/Horse | 马 |
| `b` | `B` | Bishop/Elephant | 相/象 |
| `a` | `A` | Advisor/Counselor | 仕/士 |
| `k` | `K` | King/General | 帅/将 |
| `c` | `C` | Cannon | 炮 |
| `p` | `P` | Pawn/Soldier | 兵/卒 |
| `.` | `.` | Empty | 空 |

---

## 4. Game Modes Implementation

All game modes are in **`main.py`** (355 lines), accessible via menu system.

### Mode 1: Play Mode (对弈模式)
**Function:** `play_mode() -> None`

**Features:**
- Two-player turn-based gameplay
- Real-time board display after each move
- Move input methods:
  1. Direct ICCS: `b0c2` (4-character format)
  2. Help system: Press `h` to list all red moves, `H` for black moves
  3. Numbered selection: Press `h`, then input move number `1`-`N`

**Game Loop:**
```python
while True:
    if check_game_over(board, red_turn):
        break
    # User input → Validation → Move execution → Board display
    red_turn = not red_turn
```

**Termination Conditions:**
- Manual quit (`q`, `quit`, `exit`)
- Checkmate (king captured)
- Stalemate (no legal moves)

### Mode 2: Replay Mode (棋谱模式)
**Function:** `replay_mode() -> None`

**Features:**
- View 10 pre-loaded professional games
- Step-by-step playback with pauses
- Game metadata display (players, result, move count)

**Flow:**
1. Display game list with headers: 序号, 名称, 红方, 黑方, 结果
2. User selects game by number (1-10)
3. For each move:
   - Display current step, side (红/黑), and ICCS move
   - Wait for user input (Enter=next, `q`=quit)
   - Execute move and redraw board
4. Show final result on completion

**Data Source:** `from games import GAMES` (loaded at startup)

### Mode 3: Human vs AI (人机对弈)
**Function:** `ai_mode() -> None`

**Features:**
- Choose side: Red (先手, first) or Black (后手)
- Configurable AI search depth: 1-8 (default: 5)
- AI statistics on each move:
  - Depth, nodes expanded, time elapsed (seconds), position score

**AI Selection:**
```python
human_is_red = side_choice != "2"  # 1=Red (default), 2=Black
```

**AI Move Calculation:**
```python
move, info = ai.best_move(board, red_turn)
# info = {
#   'depth': int,
#   'nodes': int,
#   'time': float (seconds),
#   'score': int (evaluation)
# }
```

**Human Input:** Same as Play Mode (ICCS, `h` for hints, numbers)

### Mode 4: AI vs AI Self-Play (AI 自对弈)
**Function:** `ai_vs_ai_mode() -> None`

**Features:**
- Independent search depths for each side (1-8)
- Configurable max moves (default: 200)
- Two playback modes:
  1. **Step-by-step:** Pause after each move, press Enter to continue
  2. **Auto:** Continuous playback (press `a` for auto)

**Configuration Dialog:**
```
红方搜索深度 (1~8, 默认3): [input]
黑方搜索深度 (1~8, 默认3): [input]
最大步数 (默认200): [input]
播放方式 (Enter=逐步, a=自动): [input]
```

**Output:** Step number, move, AI statistics, board state after each move

**Termination:**
- Checkmate/stalemate detected
- Max moves reached (draw)
- User quits during step-by-step mode

### Helper Function: `check_game_over(board, red_turn) -> bool`
Detects three win conditions:
1. **Checkmate (King captured):** `board._find_king(True/False) is None`
2. **Stalemate (No legal moves):** `len(generate_moves(red_turn)) == 0`

Returns: `True` if game over, prints winner message

---

## 5. Game Logic - Board Implementation

**File:** `/Users/winnieshi/MF/github/game/chinese_chess/board.py` (484 lines)

### Board Class: `class Board`

#### Initialization
```python
def __init__(self, board=None):
    if board is not None:
        self.grid = [row[:] for row in board]  # Deep copy
    else:
        self.grid = [row[:] for row in INIT_BOARD]
```

#### Piece Constants
```python
RED_PIECES = set("rnbakcp")      # 小写
BLACK_PIECES = set("RNBAKCP")    # 大写
ROWS, COLS = 10, 9
COL_LABELS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i']
```

### Coordinate Conversion

#### `pos_to_iccs(r: int, c: int) -> str`
Convert internal (row, col) to ICCS string.
- **Example:** `(9, 7)` → `'h0'`
- **Formula:** `f"{chr(ord('a') + c)}{9 - r}"`

#### `iccs_to_pos(iccs: str) -> tuple`
Convert ICCS string to internal (row, col).
- **Example:** `'h0'` → `(9, 7)`
- **Validation:** Column a-i, row 0-9
- **Formula:** `row = 9 - iccs_row, col = iccs_col - ord('a')`

#### `move_to_iccs(fr, fc, tr, tc) -> str`
Construct ICCS move from source/target coordinates.
- **Returns:** 4-character string like `'b0c2'`

### Move Validation: `validate_move(fr, fc, tr, tc) -> None`
Raises `ValueError` if move is illegal. Validates piece-specific rules:

**车 (Rook/Chariot)**
- Move: Straight lines only (horizontal/vertical)
- Cannot jump over other pieces
- Can capture enemy pieces

**马 (Knight/Horse)**
- Move: L-shaped (2+1 squares)
- Cannot jump obstacles ("蹩马腿" - blocked)
- 8 possible destinations

**相/象 (Bishop/Elephant)**
- Move: Diagonal only, exactly 2 squares
- Cannot jump corners ("塞象眼" - blocked diagonal)
- **River rule:** Red cannot cross to row < 5, Black cannot go to row > 4

**仕/士 (Advisor/Counselor)**
- Move: Diagonal, exactly 1 square
- **Palace rule:** Must stay in 3×3 palace (rows 0-2 or 7-9, cols 3-5)

**将/帅 (King/General)**
- Move: 1 square orthogonal (up/down/left/right)
- **Palace rule:** Must stay in 3×3 palace
- **Flying check rule:** Can capture opponent king if same column with no pieces between

**炮 (Cannon)**
- Move: Straight lines (horizontal/vertical)
- **No-capture:** Must move freely without jumping
- **Capture:** Must jump exactly one piece to land on target

**兵/卒 (Pawn/Soldier)**
- **Before river crossing:** Can only move forward
- **After river crossing:** Can move forward or sideways
- Move: 1 square per turn
- Red: Cannot move backward (dr ≤ 0)
- Black: Cannot move backward (dr ≥ 0)

**Post-Move Checks:**
1. **Not in check after move:** `not _is_in_check(red)`
2. **Kings not facing:** `not _kings_facing()`

### Move Generation: `generate_moves(red: bool) -> dict`

Returns: `{(r, c): [(tr, tc), ...], ...}`

**Process:**
1. Find all pieces of given color
2. For each piece, get candidate squares via `_candidates()`
3. Filter candidates: only keep legally playable moves
4. Filter ensures:
   - King not in check after move
   - Kings don't face each other (no shared column with clear line)

**Internal Helper:** `_candidates(fr, fc) -> list`
Returns all reachable squares (ignoring check/game-state legality).

### Display

#### `display() -> None`
Pretty-print current board state with coordinates.

```
  a b c d e f g h i
9 R N B A K A B N R
...
5 . . . . . . . . .
  = = = = = = = = =  ← River marker
4 . . . . . . . . .
...
0 r n b a k a b n r
```

#### `display_moves(red: bool) -> list`
Print all legal moves with numbering, return list of ICCS strings.

**Output Format:**
```
  红方可走棋步:
  序号  棋子  走法
  ────────────────
  1     车    a0b0
  2     车    a0a1
  ...
```

**Returns:** `["a0b0", "a0a1", ...]` for menu selection

#### `move(iccs_move: str) -> str`
Execute a single move.

**Process:**
1. Parse 4-character ICCS string
2. Get source/target coordinates
3. Validate move legality
4. Update board grid
5. Return captured piece (or '.' if none)

**Raises:** `ValueError` on invalid format or illegal move

---

## 6. AI Engine - Alpha-Beta Search

**File:** `/Users/winnieshi/MF/github/game/chinese_chess/alpha_beta.py` (335 lines)

### Evaluation Function: `evaluate(board) -> int`

Returns red-centric score (positive = red advantage, negative = black advantage).

**Scoring Components:**

1. **Piece Values (PIECE_VALUE dictionary):**
   ```python
   "p": 44,    "P": 44,    # Pawn/Soldier
   "n": 108,   "N": 108,   # Knight
   "b": 23,    "B": 23,    # Bishop/Elephant
   "a": 23,    "A": 23,    # Advisor/Counselor
   "r": 233,   "R": 233,   # Rook/Chariot
   "c": 101,   "C": 101,   # Cannon
   "k": 2500,  "K": 2500,  # King/General
   ```

2. **Position-Specific Tables (PST):** 10×9 grids for each piece type
   - **Reference:** Elephantfish chess engine (improved version)
   - **PST Types:** PST_P (pawn), PST_N (knight), PST_B (bishop), PST_A (advisor), PST_R (rook), PST_C (cannon), PST_K (king)
   - **Application:**
     - Red pieces: Use PST with row flipped (9-r)
     - Black pieces: Use PST directly (optimized for black perspective)

**Evaluation Formula:**
```python
for each piece:
    if red_piece:
        score += PIECE_VALUE[piece] + pst[9-row][col]
    else:
        score -= PIECE_VALUE[piece] + pst[row][col]
```

### Search Algorithm: `alphabeta(board, depth, alpha, beta, maximizing, nodes_counter, history)`

**Classic Alpha-Beta Pruning with Enhancements:**

**Parameters:**
- `depth`: Search depth (leaf evaluation at depth 0)
- `alpha`, `beta`: Search bounds
- `maximizing`: True = red's turn (max), False = black's turn (min)
- `nodes_counter`: Optional list `[count]` to track nodes expanded
- `history`: Optional set of board keys for repetition detection

**Base Cases:**
1. **King captured:** Return `-INF` or `INF` (game-ending positions)
2. **Depth 0:** Return `evaluate(board)` (leaf node)
3. **No legal moves:** Return `-INF` or `INF` (stalemate = loss)

**Move Ordering:** `_order_moves()`
- Sorts moves by captured piece value (captures first)
- Improves pruning efficiency

**Repetition Detection:** `_board_key()`
- Converts grid to immutable tuple key
- If board state already in `history`, penalize slightly (-5 or +5)
- Prevents infinite loops

**Pruning Logic:**
- Red's turn (max): `alpha = max(alpha, score)`; prune if `beta <= alpha`
- Black's turn (min): `beta = min(beta, score)`; prune if `beta <= alpha`

**Returns:** `(best_score, best_move_iccs)` or `(score, None)` at non-leaf

### AI Class: `class ChessAI`

#### Initialization
```python
def __init__(self, depth=5):
    self.depth = depth
    self.history = set()  # Tracks visited board states
```

#### Main API: `best_move(board: Board, red_turn: bool) -> (str, dict)`

**Returns:** `(move_iccs, info_dict)` or `(None, {...})` if no moves

**Info Dictionary:**
```python
{
    'depth': int,        # Search depth used
    'nodes': int,        # Total nodes explored
    'time': float,       # Elapsed time in seconds
    'score': int,        # Evaluation of chosen move
}
```

**Implementation:**
1. Initialize `nodes_counter = [0]` and timestamp
2. Call `alphabeta(board, depth, -INF, INF, red_turn, nodes_counter, history)`
3. Track elapsed time
4. Return move and stats

---

## 7. Game Data Format

### Games Module: `games.py` (1504 lines)

**Structure:**
```python
GAMES = [
    {
        "name": str,       # Full game title with event
        "red": str,        # Red player/team name
        "black": str,      # Black player/team name
        "result": str,     # "1-0" (red wins), "0-1" (black wins), "1/2-1/2" (draw)
        "url": str,        # Link to original on xqbase.com
        "moves": [str],    # List of ICCS moves
    },
    ...
]
```

**Current Data:** 10 professional games from xqbase.com (象棋巫师)

**Example Game:**
```python
{
    "name": "2000年全国象棋个人锦标赛 上海 林宏敏 先胜 四川 李艾东",
    "red": "上海 林宏敏",
    "black": "四川 李艾东",
    "result": "1-0",
    "url": "https://www.xqbase.com/xqbase/?gameid=135",
    "moves": [
        "h2e2", "h9g7",
        "h0g2", "i9h9",
        ...
    ],
}
```

### Endgames Module: `endgames.py` (27 lines)

**Structure:**
```python
ENDGAMES = [
    {
        "name": str,           # Puzzle name
        "category": str,       # 杀法 (checkmate), 将法 (attack), etc.
        "difficulty": int,     # 1-5 (1=easiest)
        "fen": str,            # Position description (modified FEN-like)
        "first_move": str,     # "red" or "black"
        "solution": [str],     # ICCS moves to solve puzzle
    },
    ...
]
```

**Current Data:** 2 endgame puzzles (as examples)

---

## 8. Configuration & Constants

### No External Configuration Files
- **Dependencies:** None (pyproject.toml is empty)
- **Hardcoded Constants:**
  - `ROWS = 10, COLS = 9`
  - `BASE_URL = "https://www.xqbase.com/xqbase/?gameid="`
  - `ENCODING = "gbk"`
  - `MAX_ID = 12000` (download limit)
  - `TIMEOUT = 15` seconds (for URL fetch)
  - `POLITE_DELAY = 0.5` seconds (between requests)

### Environment
- **Python Version:** 3.13+ (specified in pyproject.toml)
- **Virtual Environment:** `.venv/` (managed by `uv`)
- **Package Manager:** `uv` (ultrafast Python package manager)

### Runtime Configuration (Interactive)

**Game Mode Selection:**
```
中国象棋
  1. 对弈模式
  2. 棋谱模式
  3. 人机对弈
  4. AI 自对弈
  q. 退出
```

**AI vs AI Configuration Example:**
```
红方搜索深度 (1~8, 默认3): 4
黑方搜索深度 (1~8, 默认3): 3
最大步数 (默认200): 150
播放方式 (Enter=逐步, a=自动): a
```

---

## 9. UI/Game Mode Interactions

### Entry Point: `main()` in `main.py`

**Architecture:**
```python
def main():
    while True:
        print_menu()
        choice = input("选择: ")
        if choice == "1":
            play_mode()          # Two-player
        elif choice == "2":
            replay_mode()        # Replay games
        elif choice == "3":
            ai_mode()            # Human vs AI
        elif choice == "4":
            ai_vs_ai_mode()      # AI self-play
        elif choice in ("q", "quit"):
            break
```

**Flow Control:**
- Each mode is independent
- Returns to menu on completion
- Menu loops indefinitely until user quits

### Input/Output Patterns

#### Play Mode I/O
```
Input:
  - ICCS moves: "b0c2"
  - Help: "h" (red) or "H" (black)
  - Selection: "1" (after help)
  - Quit: "q"

Output:
  - Board display (10 lines with coordinates)
  - Move list with numbering (if h/H pressed)
  - Capture notification: "吃掉: [piece]"
  - Game over message: "红方胜! (..." 
```

#### Replay Mode I/O
```
Input:
  - Game selection: "1"-"10"
  - Step control: Enter (next), "q" (quit)

Output:
  - Game list table
  - Game metadata
  - Move-by-move board updates
  - Final result message
```

#### AI vs Human I/O
```
Input:
  - Side selection: "1" (default=red), "2" (black)
  - Depth selection: "1"-"8" (default=5)
  - Move input: same as Play Mode

Output:
  - Board display
  - AI move with stats: 
    "AI 走法: h0e0 (深度=5, 节点=2341, 耗时=1.23s, 评分=145)"
```

### Board Display Examples

**Initial Position:**
```
  a b c d e f g h i
9 R N B A K A B N R
8 . . . . . . . . .
7 . C . . . . . C .
6 P . P . P . P . P
5 . . . . . . . . .
  = = = = = = = = =
4 . . . . . . . . .
3 p . p . p . p . p
2 . c . . . . . c .
1 . . . . . . . . .
0 r n b a k a b n r
```

**After Some Moves:**
```
  a b c d e f g h i
9 R N . A K A B N R
8 . . B . . . . . .
7 . . . . . . . C .
6 P . P . P . P . P
5 . . . . . . . . .
  = = = = = = = = =
4 . . . . . . . . .
3 p . p . p . p . .
2 . c . . . . . c .
1 . . b . . . . . .
0 r n . a k a . n r
```

---

## 10. Key Patterns & Architecture

### Design Patterns

1. **Board State Pattern:** Immutable-style board with move/undo via copy-on-backtrack
2. **Minimax with Alpha-Beta:** Classic game tree search
3. **Move Validation Decorator:** `validate_move()` wraps move execution
4. **Factory Pattern:** `Board()` constructor for empty or copied boards
5. **Data-Driven:** Games stored as data structures, not code

### Data Flow

```
gen_games.py
  → Download from xqbase.com
  → Parse HTML
  → Generate games.py

main.py (CLI Menu)
  → replay_mode() → Load GAMES → Board.move()
  → play_mode() → Two players → Board.move()
  → ai_mode() → Board.move() + ChessAI.best_move()
  → ai_vs_ai_mode() → ChessAI vs ChessAI

board.py
  → Manage grid state
  → Validate moves (all 7 piece types)
  → Generate legal moves
  → Detect game end

alpha_beta.py
  → Evaluate position
  → Tree search with pruning
  → Return best move
```

### Error Handling

**Validation Errors (ValueError):**
- Invalid ICCS format
- No piece at source
- Move violates piece rules
- Move puts own king in check
- Kings facing each other

**Network Errors (gen_games.py):**
- URL timeout → Logged, continue
- Parsing failure → Skip game, try next
- 20+ consecutive failures → Abort download

**Input Errors (main.py):**
- Invalid menu choice → Ignore, re-prompt
- Invalid move number → Out of range warning
- EOF/KeyboardInterrupt → Graceful quit

---

## 11. Testing Infrastructure

### Test Files (4 files, 1,148 lines)

1. **test_moves.py** (651 lines)
   - Validates movement rules for all 7 piece types
   - Tests edge cases: river crossing, palace restrictions, blocking

2. **test_games.py** (111 lines)
   - Verifies all games in GAMES can be replayed
   - Checks for illegal moves during playback

3. **test_ai.py** (251 lines)
   - Tests alpha-beta search correctness
   - Validates evaluation function
   - Benchmarks search performance

4. **test_self_play.py** (135 lines)
   - Runs AI vs AI games to completion
   - Checks for logic errors during play

### Running Tests
```bash
uv run python -m pytest chinese_chess/
uv run python chinese_chess/test_games.py
uv run python chinese_chess/test_ai.py
```

---

## Summary

This is a **production-quality Chinese chess implementation** featuring:

✅ **Complete game logic** with all 7 piece types and special rules  
✅ **Robust AI engine** using alpha-beta pruning  
✅ **4 game modes:** 2-player, replay, human-vs-AI, AI-vs-AI  
✅ **Professional game data** fetched from xqbase.com  
✅ **Comprehensive testing** with 1,100+ lines of tests  
✅ **Clean architecture** with clear separation of concerns  
✅ **ICCS coordinate standard** for international compatibility  

