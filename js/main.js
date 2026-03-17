// js/main.js  — Canvas Go board + Pyodide AI glue
// No external board library needed!

// ─── CONFIG ──────────────────────────────────────────
const SIZE       = 9;          // board size (9, 13, or 19)
const CELL       = 34;          // pixels per cell
const PAD        = 28;          // padding around the grid
const CANVAS_PX  = CELL * (SIZE - 1) + PAD * 2;

const EMPTY = 0, BLACK = 1, WHITE = 2;

// ─── STATE ───────────────────────────────────────────
let board     = Array.from({ length: SIZE }, () => Array(SIZE).fill(EMPTY));
let previousBoard = null;
let humanTurn = true;           // human = BLACK, AI = WHITE
let pyodide, getAIMove, playHumanAndAI;
const statusEl = document.getElementById('status');

// ─── CANVAS SETUP ────────────────────────────────────
const canvas = document.getElementById('board');
const ctx    = canvas.getContext('2d');
canvas.width = canvas.height = CANVAS_PX;

// ─── DRAW ────────────────────────────────────────────
function draw() {
  // wooden background
  ctx.fillStyle = '#dcb35c';
  ctx.fillRect(0, 0, CANVAS_PX, CANVAS_PX);

  // grid lines
  ctx.strokeStyle = '#333';
  ctx.lineWidth = 1;
  for (let i = 0; i < SIZE; i++) {
    const pos = PAD + i * CELL;
    // vertical
    ctx.beginPath(); ctx.moveTo(pos, PAD); ctx.lineTo(pos, PAD + (SIZE - 1) * CELL); ctx.stroke();
    // horizontal
    ctx.beginPath(); ctx.moveTo(PAD, pos); ctx.lineTo(PAD + (SIZE - 1) * CELL, pos); ctx.stroke();
  }

  // star points (hoshi)
  const hoshi = SIZE === 19 ? [3,9,15] : SIZE === 13 ? [3,6,9] : [2,4,6];
  ctx.fillStyle = '#333';
  for (const r of hoshi) for (const c of hoshi) {
    ctx.beginPath();
    ctx.arc(PAD + c * CELL, PAD + r * CELL, 3.5, 0, Math.PI * 2);
    ctx.fill();
  }

  // stones
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      if (board[y][x] === EMPTY) continue;
      const cx = PAD + x * CELL;
      const cy = PAD + y * CELL;
      const radius = CELL * 0.44;

      // shadow
      ctx.beginPath();
      ctx.arc(cx + 2, cy + 2, radius, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0,0,0,0.3)';
      ctx.fill();

      // stone
      const grad = ctx.createRadialGradient(cx - 3, cy - 3, 2, cx, cy, radius);
      if (board[y][x] === BLACK) {
        grad.addColorStop(0, '#555');
        grad.addColorStop(1, '#000');
      } else {
        grad.addColorStop(0, '#fff');
        grad.addColorStop(1, '#bbb');
      }
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.strokeStyle = board[y][x] === BLACK ? '#000' : '#999';
      ctx.lineWidth = 0.5;
      ctx.stroke();
    }
  }
}

// ─── CLICK HANDLER ───────────────────────────────────
canvas.addEventListener('click', async (e) => {
  if (!humanTurn || !getAIMove) return;

  const rect = canvas.getBoundingClientRect();
  const scale = CANVAS_PX / rect.width;
  const mx = (e.clientX - rect.left) * scale;
  const my = (e.clientY - rect.top)  * scale;

  const x = Math.round((mx - PAD) / CELL);
  const y = Math.round((my - PAD) / CELL);

  if (x < 0 || x >= SIZE || y < 0 || y >= SIZE) return;
  if (!playHumanAndAI) return;

  humanTurn = false;
  statusEl.textContent = 'AI is thinking...';

  try {
    const result = playHumanAndAI(
      board.map(r => Array.from(r)),
      [x, y],
      previousBoard ? previousBoard.map(r => Array.from(r)) : null
    );

    let payload;
    if (result && typeof result.toJs === 'function') {
      payload = result.toJs({ dict_converter: Object.fromEntries });
      result.destroy();
    } else {
      payload = result;
    }

    if (payload && payload.board) {
      board = payload.board.map(r => Array.from(r));
      previousBoard = payload.previous_board ? payload.previous_board.map(r => Array.from(r)) : null;
      draw();
      statusEl.textContent = payload.status || 'Your turn (Black)';
    } else {
      statusEl.textContent = 'AI returned an invalid response.';
    }
  } catch (err) {
    console.error('AI error:', err);
    statusEl.textContent = 'AI error: ' + err.message;
  }

  humanTurn = true;
});

// ─── INIT PYODIDE ────────────────────────────────────
async function init() {
  draw();

  try {
    pyodide = await loadPyodide();
    statusEl.textContent = 'Loading AI...';

    const engineCode = await fetch('python/ai/engine.py').then(r => r.text());
    const utilsCode = await fetch('python/ai/board_utils.py').then(r => r.text());

    pyodide.FS.writeFile('board_utils.py', utilsCode);
    pyodide.FS.writeFile('engine.py', engineCode);

    await pyodide.runPythonAsync(`
    import importlib
    import board_utils
    import engine
    importlib.reload(board_utils)
    importlib.reload(engine)
    `);

    const engineModule = pyodide.pyimport('engine');
    getAIMove = engineModule.get_best_move;
    playHumanAndAI = engineModule.play_human_and_ai;

    statusEl.textContent = 'Your turn (Black) — click to place a stone!';
  } catch (err) {
    statusEl.textContent = 'Error loading AI: ' + err.message;
    console.error(err);
  }
}

init();