"""
Real-Time Chat Client
======================
Connects to the ChatServer via WebSocket and provides an interactive
terminal-based chat experience.

Usage:
    python client.py

Default server: ws://127.0.0.1:8765
"""

import asyncio
import sys
import websockets
import json
from datetime import datetime


# ---------------------------------------------------------------------------
# Windows fix — must run BEFORE asyncio.run()
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SERVER_URI       = "ws://127.0.0.1:8765"
RECONNECT_DELAY  = 3          # seconds between reconnection attempts
MAX_RETRIES      = 5          # 0 = infinite


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------
def _fmt_time() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _print_msg(sender: str, content: str, msg_type: str = "chat") -> None:
    """Pretty-print an incoming message with colour hints (ANSI)."""
    if msg_type == "system":
        print(f"\033[33m[{_fmt_time()}] ⚡ {content}\033[0m")
    elif msg_type == "error":
        print(f"\033[31m[{_fmt_time()}] ✖ {content}\033[0m")
    else:
        print(f"\033[36m[{_fmt_time()}] {sender}:\033[0m {content}")


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class ChatClient:
    """
    Async chat client that:
    * Sends a username handshake on connect
    * Listens for messages in a background task
    * Lets the user type commands / messages in the foreground
    * Reconnects automatically on unexpected disconnection
    """

    def __init__(self, username: str, uri: str = SERVER_URI):
        self.username   = username
        self.uri        = uri
        self.websocket  = None
        self._running   = True

    # ----- public ----------------------------------------------------------

    async def run(self) -> None:
        """Main entry – handles the reconnect loop."""
        attempts = 0
        while self._running:
            try:
                async with websockets.connect(self.uri) as ws:
                    self.websocket = ws
                    attempts = 0                          # reset on success
                    print(f"\033[32m✓ Connected to {self.uri}\033[0m")

                    # --- handshake: tell the server who we are ---
                    await ws.send(json.dumps({"username": self.username}))

                    # Run listener + input loop concurrently
                    await asyncio.gather(
                        self._listen(),
                        self._input_loop(),
                    )

            except websockets.exceptions.InvalidURI:
                print(f"\033[31m✖ Invalid server URI: {self.uri}\033[0m")
                self._running = False
                break

            except (ConnectionRefusedError, OSError):
                attempts += 1
                if MAX_RETRIES and attempts > MAX_RETRIES:
                    print("\033[31m✖ Max reconnection attempts reached. Exiting.\033[0m")
                    break
                print(f"\033[33m⟳ Connection lost. Retrying in {RECONNECT_DELAY}s … (attempt {attempts})\033[0m")
                await asyncio.sleep(RECONNECT_DELAY)

            except KeyboardInterrupt:
                self._running = False
                break

        print("\033[33mGoodbye!\033[0m")

    # ----- listener --------------------------------------------------------

    async def _listen(self) -> None:
        """Continuously read messages from the server."""
        try:
            async for raw in self.websocket:
                data = json.loads(raw)
                _print_msg(
                    sender   = data.get("sender", "?"),
                    content  = data.get("content", ""),
                    msg_type = data.get("msg_type", "chat"),
                )
        except websockets.exceptions.ConnectionClosed:
            print("\033[33m⚡ Server closed the connection.\033[0m")
            self._running = False

    # ----- input loop ------------------------------------------------------

    async def _input_loop(self) -> None:
        """Non-blocking terminal input that coexists with the listener."""
        loop = asyncio.get_running_loop()                # fixed: was get_event_loop()
        while self._running:
            try:
                # Run blocking input() in a thread so we don't block the event loop
                raw = await loop.run_in_executor(None, input, "you > ")
            except EOFError:
                break                                     # piped input ended

            text = raw.strip()
            if not text:
                continue

            if text.lower() in ("/quit", "/exit", "exit", "quit"):
                self._running = False
                break

            try:
                await self.websocket.send(json.dumps({"content": text}))
            except websockets.exceptions.ConnectionClosed:
                print("\033[33m⚡ Disconnected while sending.\033[0m")
                self._running = False
                break


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def _get_username() -> str:
    """Prompt the user for a display name (non-empty)."""
    while True:
        name = input("Enter your username: ").strip()
        if name:
            return name
        print("Username cannot be empty.")


if __name__ == "__main__":
    username = _get_username()
    client   = ChatClient(username=username)

    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\033[33mGoodbye!\033[0m")
