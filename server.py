"""
Real-Time Chat & Notification Server
=====================================
An async WebSocket server that supports multiple simultaneous clients,
broadcasts messages in real-time, and persists all activity to a log file.

Usage:
    python server.py

Default host: 127.0.0.1
Default port: 8765
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
# On Windows, asyncio defaults to ProactorEventLoop which breaks websockets.
# SelectorEventLoop fixes it. This block does nothing on Linux / macOS.
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
        logging.StreamHandler(),                          # terminal
        logging.FileHandler(LOG_FILE, encoding="utf-8"),  # file
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass(eq=False)
class Client:
    """Represents a single connected WebSocket client."""
    websocket: object                                     # raw connection
    username:  str = "Anonymous"
    joined_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Serialisable snapshot (excludes the raw socket)."""
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
    """
    Manages the full lifecycle of the WebSocket chat server.

    Responsibilities
    ----------------
    * Accept & track connected clients
    * Route incoming messages to every connected client (broadcast)
    * Send system notifications on join / leave
    * Handle errors gracefully so one bad client can't crash the server
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host    = host
        self.port    = port
        self.clients: set[Client] = set()                 # live connections

    # ----- public API ------------------------------------------------------

    async def start(self) -> None:
        """Spin up the WebSocket server and block until stopped (Ctrl-C)."""
        logger.info("Server starting on ws://%s:%d", self.host, self.port)

        async with websockets.serve(self._handler, self.host, self.port):
            logger.info("Server is LIVE  ✓  — waiting for clients …")
            await asyncio.Future()                        # run forever

    # ----- internal helpers ------------------------------------------------

    async def _handler(self, websocket) -> None:
        """Per-connection coroutine — lives for as long as the socket is open."""
        client = await self._register(websocket)
        try:
            async for raw in websocket:
                await self._process(client, raw)
        except websockets.exceptions.ConnectionClosed:
            pass                                          # normal disconnect
        finally:
            await self._unregister(client)

    # ----- lifecycle -------------------------------------------------------

    async def _register(self, websocket) -> Client:
        """Accept a new connection, assign a username, notify everyone."""
        # First message from client must be a JSON handshake: {"username":"…"}
        try:
            handshake = json.loads(await asyncio.wait_for(websocket.recv(), timeout=5))
            username  = handshake.get("username", "Anonymous").strip() or "Anonymous"
        except (json.JSONDecodeError, asyncio.TimeoutError, KeyError):
            username = "Anonymous"

        client = Client(websocket=websocket, username=username)
        self.clients.add(client)

        logger.info("Client connected: %s  (total: %d)", username, len(self.clients))

        # Tell the new client about themselves
        welcome = Message(sender="SERVER", content=f"Welcome, {username}!", msg_type="system")
        await self._send(client, welcome)

        # Tell everyone else
        notify = Message(sender="SERVER", content=f"{username} joined the chat.", msg_type="system")
        await self._broadcast(notify, exclude=client)
        return client

    async def _unregister(self, client: Client) -> None:
        """Clean up a disconnected client and notify the room."""
        self.clients.discard(client)
        logger.info("Client disconnected: %s  (remaining: %d)", client.username, len(self.clients))

        notify = Message(sender="SERVER", content=f"{client.username} left the chat.", msg_type="system")
        await self._broadcast(notify)

    # ----- message handling ------------------------------------------------

    async def _process(self, client: Client, raw: str) -> None:
        """Validate and route a single incoming message."""
        try:
            data    = json.loads(raw)
            content = str(data.get("content", "")).strip()

            if not content:
                return                                    # ignore empty payloads

            # --- special commands (extensible) ---
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
        """
        Simple slash-commands.
        /help          – list commands
        /users         – list connected usernames
        /ping          – server responds with PONG
        """
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
        """Send a message to every connected client (optionally skip one)."""
        tasks = [
            self._send(client, message)
            for client in self.clients
            if client is not exclude
        ]
        if tasks:
            await asyncio.gather(*tasks)

    @staticmethod
    async def _send(client: Client, message: Message) -> None:
        """Fire-and-forget send with per-client error isolation."""
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
