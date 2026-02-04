"""
Real-Time Chat Server - Render Deployment Version
==================================================
This version runs an HTTP server with health check for Render.
For local WebSocket testing, use the original server.py.
"""

import asyncio
import sys
import logging
import os
from aiohttp import web


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
# HTTP Server (for Render health checks)
# ---------------------------------------------------------------------------
async def health_check(request):
    """Health check endpoint - aiohttp handles HEAD automatically"""
    return web.Response(text="OK\n", status=200)


async def serve_html(request):
    """Landing page"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Chat Server</title>
    <meta charset="utf-8">
    <style>
        body { font-family: system-ui, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; line-height: 1.6; }
        h1 { color: #333; }
        .status { color: #22c55e; font-weight: bold; }
        code { background: #f3f4f6; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; }
        .info { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 16px 0; }
    </style>
</head>
<body>
    <h1>🚀 Real-Time Chat Server</h1>
    <p><strong>Status:</strong> <span class="status">● Live</span></p>
    
    <div class="info">
        <strong>Deployment Note:</strong> This is a health check endpoint for Render's deployment system.
        The full WebSocket chat server with real-time messaging runs locally.
        <p>To use locally: <code>python server_local.py</code></p>
    </div>
    
    <h3>Project Repository</h3>
    <p>View the full source code and instructions at:</p>
    <p><a href="https://github.com/yourusername/realtime-chat-server">github.com/yourusername/realtime-chat-server</a></p>
    
    <h3>Features</h3>
    <ul>
        <li>Python asyncio backend</li>
        <li>WebSocket real-time communication</li>
        <li>Multi-client support</li>
        <li>Browser + terminal clients</li>
        <li>Command system (/help, /users, /ping)</li>
    </ul>
    
    <p><small>Built as a portfolio project demonstrating backend skills</small></p>
</body>
</html>
"""
    return web.Response(text=html, content_type='text/html')


async def start_server():
    """Start HTTP server on Render's PORT"""
    port = int(os.environ.get("PORT", 8000))
    
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', serve_html)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info("=" * 60)
    logger.info("HTTP Server LIVE on port %d", port)
    logger.info("Health check: http://0.0.0.0:%d/health", port)
    logger.info("Landing page: http://0.0.0.0:%d/", port)
    logger.info("=" * 60)
    
    # Keep running
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server shut down by user.")
