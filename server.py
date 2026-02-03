"""
Real-Time Chat & Notification Server
=====================================
An async WebSocket server that supports multiple simultaneous clients,
broadcasts messages in real-time, and persists all activity to a log file.

Usage:
    python server.py

The webapp (index.html) connects from a browser on the same machine.
Server binds to 0.0.0.0 so both the terminal client and the browser
client can reach it.
"""

import asyncio
import sys
import websockets
import json
import logging
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict


# ---------------------------------------------------------------------------
# Windows fix — must run BEFORE asyncio.run()
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ---------------------------------------------------------------------------
# Logging setup  –  logs go to console AND to logs/server.log
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
    """Represents a single connected WebSocket client."""
    websocket: object
    username:  str = "Anonymous"
    joined_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {"username": self.username, "joined_at": self.joined_at}


@dataclass
class Message:
    """Envelope for every message that moves through the server."""
    sender:    str
    content:   str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    msg_type:  str = "chat"                               # chat | system | error

    def to_json(self) -> str:
        return json.dumps(asdict(self))


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
class ChatServer:

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host    = host
        self.port    = port
        self.clients: set[Client] = set()

    # ----- public ----------------------------------------------------------

    async def start(self) -> None:
        logger.info("Server starting on ws://%s:%d", self.host, self.port)

        # origins=None  →  accept WebSocket from ANY origin (localhost browser, etc.)
        async with websockets.serve(
            self._handler,
            self.host,
            self.port,
            origins=None,                                 # allow all origins
        ):
            logger.info("Server is LIVE  ✓  — waiting for clients …")
            logger.info("  Terminal client : python client.py")
            logger.info("  Browser client  : open index.html in a browser")
            await asyncio.Future()

    # ----- handler ---------------------------------------------------------

    async def _handler(self, websocket) -> None:
        client = await self._register(websocket)
        try:
            async for raw in websocket:
                await self._process(client, raw)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self._unregister(client)

    # ----- lifecycle -------------------------------------------------------

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

    # ----- message handling ------------------------------------------------

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

    # ----- transport -------------------------------------------------------

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
