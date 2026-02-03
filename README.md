# Real-Time Chat & Notification Server

> A Python backend project demonstrating **asyncio**, **WebSockets**, **OOP**, **error handling**, and **file logging** — built to prove backend skills, not pad a resume.

---

## What It Does

A multi-client, real-time chat server that:

- Accepts unlimited simultaneous WebSocket connections
- Broadcasts messages instantly to every connected client
- Sends system notifications when users join or leave
- Supports slash-commands (`/help`, `/users`, `/ping`)
- Logs every event to `logs/server.log`
- Handles errors per-client so one bad connection never crashes the server

---

## Tech Stack

| Technology | Why |
|---|---|
| **Python 3.11+** | Core language |
| **asyncio** | Non-blocking concurrency without threads |
| **websockets** | Production-grade async WebSocket library |
| **dataclasses** | Clean, typed data models |
| **logging** | Dual-output (console + file) event trail |

No frameworks. No databases. No cloud. Pure backend fundamentals.

---

## Project Structure

```
realtime-chat-server/
│
├── server.py          ← WebSocket server (ChatServer class)
├── client.py          ← Interactive terminal client (ChatClient class)
├── requirements.txt   ← Python dependencies
├── README.md          ← This file
└── logs/
    ├── .gitkeep       ← Keeps directory in Git
    └── server.log     ← Auto-generated at runtime
```

---

## Quick Start

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
2025-01-15 10:30:00 [INFO] Server starting on ws://127.0.0.1:8765
2025-01-15 10:30:00 [INFO] Server is LIVE  ✓  — waiting for clients …
```

### 3. Open two (or more) terminals and start clients

```bash
python client.py
```

Each client is prompted for a username, then can type messages freely.

### 4. Try the commands

| Command | What it does |
|---|---|
| `/help` | Lists available commands |
| `/users` | Shows everyone online |
| `/ping` | Server replies PONG |
| `/quit` | Disconnects cleanly |

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

---

