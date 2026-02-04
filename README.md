# Real-Time Chat & Notification Server

> A Python backend project demonstrating **asyncio**, **WebSockets**, **OOP**, **error handling**, and **file logging** — built to prove backend skills, not pad a resume.

**[🔴 Live Demo](https://your-app.onrender.com)** ← Deploy and replace this URL

---

## What It Does

A multi-client, real-time chat server that:

- Accepts unlimited simultaneous WebSocket connections
- Broadcasts messages instantly to every connected client
- Sends system notifications when users join or leave
- Supports slash-commands (`/help`, `/users`, `/ping`)
- Logs every event to `logs/server.log`
- Handles errors per-client so one bad connection never crashes the server
- Includes both terminal client AND browser webapp

---

## Tech Stack

| Technology | Why |
|---|---|
| **Python 3.11+** | Core language |
| **asyncio** | Non-blocking concurrency without threads |
| **websockets** | Production-grade async WebSocket library |
| **dataclasses** | Clean, typed data models |
| **logging** | Dual-output (console + file) event trail |
| **HTML/CSS/JS** | Browser client with zero dependencies |

No frameworks. No databases. No cloud. Pure backend fundamentals.

---

## Project Structure

```
realtime-chat-server/
│
├── server.py          ← WebSocket server (ChatServer class)
├── client.py          ← Interactive terminal client (ChatClient class)
├── index.html         ← Browser-based webapp (no framework)
├── requirements.txt   ← Python dependencies
├── Procfile           ← Deployment config
├── README.md          ← This file
└── logs/
    ├── .gitkeep       ← Keeps directory in Git
    └── server.log     ← Auto-generated at runtime
```

---

## Quick Start (Local Development)

### 1. Clone & install

```bash
git clone <your-repo-url>
cd realtime-chat-server
pip install -r requirements.txt
```

### 2. Start the server

```bash
python server.py
```

You'll see:
```
Server starting on ws://0.0.0.0:8765
Server is LIVE  ✓  — waiting for clients …
```

### 3. Connect clients

**Option A — Terminal client:**
```bash
python client.py
```

**Option B — Browser client:**
- Open `index.html` in Chrome/Firefox
- Or visit the deployed URL (see below)

### 4. Try the commands

| Command | What it does |
|---|---|
| `/help` | Lists available commands |
| `/users` | Shows everyone online |
| `/ping` | Server replies PONG |
| `/quit` | Disconnects cleanly |

---

## Deployment (Get a Live URL)

### Deploy to Render (Free)

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "ready for deployment"
   git push origin main
   ```

2. **Deploy on Render:**
   - Go to https://render.com
   - Sign up with GitHub
   - Click "New +" → "Web Service"
   - Connect your repo
   - Settings:
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python server.py`
   - Click "Create Web Service"

3. **Wait 2-3 minutes** — Render builds and deploys

4. **Get your URL:** `https://your-app-name.onrender.com`

5. **Update this README** with your live link

**Note:** Render's free tier spins down after 15 min of inactivity. First load takes ~30 seconds.

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for Railway, Fly.io, and custom domain setup.

---

## How the Code Works

### server.py — `ChatServer`

```
ChatServer
├── start()            → spins up the websockets.serve loop
├── _handler()         → one coroutine per client connection
├── _register()        → handshake + welcome + broadcast join
├── _unregister()      → remove client + broadcast leave
├── _process()         → parse JSON, route to broadcast or command
├── _handle_command()  → /help, /users, /ping
├── _broadcast()       → asyncio.gather across all sockets
└── _send()            → per-client error-isolated send
```

Key design decisions:
- Each client connection runs in its own **coroutine** (no threads).
- `_send()` catches `ConnectionClosed` in isolation — if one client drops mid-broadcast, others still receive the message.
- Messages are wrapped in a `Message` dataclass so serialisation and typing are consistent everywhere.

### client.py — `ChatClient`

```
ChatClient
├── run()              → reconnect loop (handles transient failures)
├── _listen()          → async for loop over incoming frames
└── _input_loop()      → run_in_executor wraps blocking input()
```

Key design decisions:
- `input()` is offloaded to a **thread pool** via `run_in_executor` so it doesn't block the async event loop.
- Reconnection is automatic with a configurable retry limit.
- ANSI colour codes give instant visual feedback (green = connected, yellow = system, red = error, cyan = chat).

### index.html — Browser Webapp

- **Zero dependencies** — pure HTML, CSS, JavaScript
- **Dark glassmorphism UI** — CSS variables for easy theming
- **Auto-reconnect** — same logic as terminal client
- **Works locally AND deployed** — auto-detects ws:// vs wss://

---

## What This Project Proves

| Skill Area | Evidence |
|---|---|
| **Python OOP** | `ChatServer`, `ChatClient`, `Client`, `Message` classes |
| **asyncio** | `async/await` throughout; `gather`, `wait_for`, `run_in_executor` |
| **WebSockets** | Full connect → handshake → message loop → disconnect lifecycle |
| **Error handling** | Per-client isolation, timeout on handshake, malformed-JSON recovery |
| **File I/O + Logging** | Dual-handler logger writing to both console and `server.log` |
| **Data modelling** | `dataclasses` with clean serialisation |
| **Git hygiene** | Structured commits, meaningful messages, clear folder layout |
| **Deployment** | Production-ready config, environment variables, HTTPS/WSS |

---

## Interview Prep — Questions This Project Answers

1. **"How do WebSockets differ from HTTP?"**  
   HTTP is request-response and stateless. WebSockets open a persistent, bi-directional TCP connection — once established, either side can push data at any time with no new handshake.

2. **"How does async work in Python?"**  
   `asyncio` runs coroutines on a single thread using an event loop. When a coroutine hits an `await`, it yields control back to the loop, which can run other coroutines. No OS threads needed for I/O-bound work.

3. **"How do you handle multiple clients?"**  
   Each accepted WebSocket connection spawns its own `_handler` coroutine. A shared `set` tracks all live clients. Broadcasts use `asyncio.gather` to send to all in parallel.

4. **"What happens if one client crashes mid-broadcast?"**  
   `_send()` wraps each individual send in a try/except. A failed send logs a debug message and skips that client — the rest of the broadcast completes normally.

5. **"How did you structure the project?"**  
   Separation of concerns: server logic in one file, client logic in another, data models as dataclasses. The `logs/` directory is version-controlled (via `.gitkeep`) but log files themselves are generated at runtime.

See [TECHNICAL_BREAKDOWN.md](TECHNICAL_BREAKDOWN.md) for 1000+ lines of detailed explanations.

---

## Suggested Git Commit History

```
feat: initial project setup — server.py, client.py, requirements.txt
feat: add Client and Message dataclasses
feat: implement WebSocket connection handler and handshake
feat: add message broadcasting to all connected clients
feat: add system notifications for join / leave events
feat: implement slash-commands (/help, /users, /ping)
feat: add dual-output logging (console + file)
feat: add reconnection logic to client
feat: add browser webapp (index.html)
feat: add deployment config for Render
docs: write comprehensive README and deployment guide
```

---

## Extending This Project

Ideas for adding features:
- **Authentication**: JWT tokens instead of plain usernames
- **Message history**: SQLite/PostgreSQL to persist messages
- **Private messages**: `/dm Alice hello` sends only to Alice
- **Typing indicators**: "Alice is typing…" when someone types
- **File uploads**: Base64-encode and send images/files
- **Rooms/channels**: Separate chat rooms with `/join #general`

---

## License

MIT — use it, learn from it, put it on your resume.

---

## Author

Built as a portfolio project to demonstrate Python backend skills for job applications.

- **GitHub**: [github.com/yourusername/realtime-chat-server](https://github.com/yourusername)
- **Live Demo**: [your-app.onrender.com](https://your-app.onrender.com) ← Update after deployment
- **LinkedIn**: [linkedin.com/in/yourprofile](https://linkedin.com/in/yourprofile)
