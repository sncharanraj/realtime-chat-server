"""
Real-Time Chat & Notification Server
=====================================
Deployment version with HTTP health check endpoint for Render.
"""

import asyncio
import sys
import websockets
import json
import logging
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict
from aiohttp import web  # ← NEW: for health check endpoint


# ---------------------------------------------------------------------------
# Windows fix
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "server.log")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass(eq=False)
class Client:
    websocket: object
    username:  str = "Anonymous"
    joined_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {"username": self.username, "joined_at": self.joined_at}


@dataclass
class Message:
    sender:    str
    content:   str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    msg_type:  str = "chat"

    def to_json(self) -> str:
        return json.dumps(asdict(self))


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
class ChatServer:

    def __init__(self, host: str = "0.0.0.0", port: int = None):
        self.host    = host
        self.port    = port or int(os.environ.get("PORT", 8765))
        self.clients: set[Client] = set()

    async def start(self) -> None:
        logger.info("Server starting on ws://%s:%d", self.host, self.port)

        # Start HTTP health check server on same port
        app = web.Application()
        app.router.add_get('/health', self._health_check)
        app.router.add_head('/health', self._health_check)  # ← Render uses HEAD
        app.router.add_get('/', self._serve_html)
        
        runner = web.AppRunner(app)
        await runner.setup()
        http_site = web.TCPSite(runner, self.host, self.port)
        await http_site.start()

        # Start WebSocket server on port + 1
        ws_port = self.port + 1
        async with websockets.serve(
            self._handler,
            self.host,
            ws_port,
            origins=None,
        ):
            logger.info("HTTP server is LIVE on port %d", self.port)
            logger.info("WebSocket server is LIVE on port %d", ws_port)
            await asyncio.Future()

    async def _health_check(self, request):
        """Health check endpoint for Render"""
        return web.Response(text="OK", status=200)
    
    async def _serve_html(self, request):
        """Serve a simple landing page"""
        html = f"""
<!DOCTYPE html>
<html>
<head><title>Chat Server</title></head>
<body style="font-family:sans-serif;max-width:600px;margin:50px auto;padding:20px">
    <h1>🚀 Real-Time Chat Server</h1>
    <p>WebSocket server is running on <code>wss://{request.host}/ws</code></p>
    <p><strong>Status:</strong> <span style="color:green">● Live</span></p>
    <p><strong>Connected clients:</strong> {len(self.clients)}</p>
    <hr>
    <p>Open <a href="your-frontend-url-here">the chat webapp</a> to connect.</p>
</body>
</html>
"""
        return web.Response(text=html, content_type='text/html')

    async def _handler(self, websocket) -> None:
        client = await self._register(websocket)
        try:
            async for raw in websocket:
                await self._process(client, raw)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self._unregister(client)

    async def _register(self, websocket) -> Client:
        try:
            handshake = json.loads(await asyncio.wait_for(websocket.recv(), timeout=5))
            username  = handshake.get("username", "Anonymous").strip() or "Anonymous"
        except (json.JSONDecodeError, asyncio.TimeoutError, KeyError):
            username = "Anonymous"

        client = Client(websocket=websocket, username=username)
        self.clients.add(client)
        logger.info("Client connected: %s  (total: %d)", username, len(self.clients))

        welcome = Message(sender="SERVER", content=f"Welcome, {username}!", msg_type="system")
        await self._send(client, welcome)

        notify = Message(sender="SERVER", content=f"{username} joined the chat.", msg_type="system")
        await self._broadcast(notify, exclude=client)
        return client

    async def _unregister(self, client: Client) -> None:
        self.clients.discard(client)
        logger.info("Client disconnected: %s  (remaining: %d)", client.username, len(self.clients))

        notify = Message(sender="SERVER", content=f"{client.username} left the chat.", msg_type="system")
        await self._broadcast(notify)

    async def _process(self, client: Client, raw: str) -> None:
        try:
            data    = json.loads(raw)
            content = str(data.get("content", "")).strip()

            if not content:
                return

            if content.startswith("/"):
                await self._handle_command(client, content)
                return

            msg = Message(sender=client.username, content=content)
            logger.info("[CHAT] %s: %s", client.username, content)
            await self._broadcast(msg)

        except json.JSONDecodeError:
            err = Message(sender="SERVER", content="Invalid message format.", msg_type="error")
            await self._send(client, err)
            logger.warning("Malformed message from %s", client.username)

    async def _handle_command(self, client: Client, cmd: str) -> None:
        parts   = cmd.split()
        command = parts[0].lower()

        responses = {
            "/help":  "Available commands: /help, /users, /ping",
            "/ping":  "PONG 🏓",
            "/users": "Online: " + ", ".join(c.username for c in self.clients),
        }

        reply_text = responses.get(command, f"Unknown command: {command}  — try /help")
        reply      = Message(sender="SERVER", content=reply_text, msg_type="system")

        logger.info("[CMD] %s used %s", client.username, command)
        await self._send(client, reply)

    async def _broadcast(self, message: Message, exclude: Client | None = None) -> None:
        tasks = [
            self._send(client, message)
            for client in self.clients
            if client is not exclude
        ]
        if tasks:
            await asyncio.gather(*tasks)

    @staticmethod
    async def _send(client: Client, message: Message) -> None:
        try:
            await client.websocket.send(message.to_json())
        except websockets.exceptions.ConnectionClosed:
            logger.debug("Send failed for %s – connection already closed.", client.username)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    server = ChatServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server shut down by user.")
