#!/usr/bin/env python3
"""PowerHaus Add-on - Main Application."""

import asyncio
import os
import logging
from aiohttp import web, ClientSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Development mode detection
DEV_MODE = os.environ.get("DEV_MODE", "false").lower() == "true"

# Home Assistant configuration
if DEV_MODE:
    # Development mode: use direct HA API with long-lived access token
    HA_TOKEN = os.environ.get("HA_TOKEN", "")
    HA_URL = os.environ.get("HA_URL", "http://localhost:8123")
    HA_API_URL = f"{HA_URL}/api"
    logger.info(f"Running in DEVELOPMENT mode - connecting to {HA_URL}")
else:
    # Production mode: use Supervisor API
    HA_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
    HA_API_URL = "http://supervisor/core/api"
    logger.info("Running in PRODUCTION mode - using Supervisor API")

# Entity state
current_state = 0


async def update_ha_entity(session: ClientSession):
    """Update the powerhaus entity in Home Assistant."""
    global current_state

    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    entity_id = "sensor.powerhaus"
    state_url = f"{HA_API_URL}/states/{entity_id}"

    payload = {
        "state": str(current_state),
        "attributes": {
            "friendly_name": "PowerHaus",
            "unit_of_measurement": "",
            "icon": "mdi:flash"
        }
    }

    try:
        async with session.post(state_url, json=payload, headers=headers) as response:
            if response.status in (200, 201):
                logger.info(f"Updated powerhaus entity to state: {current_state}")
            else:
                text = await response.text()
                logger.error(f"Failed to update entity: {response.status} - {text}")
    except Exception as e:
        logger.error(f"Error updating entity: {e}")


async def toggle_entity_task():
    """Background task to toggle entity every 5 seconds."""
    global current_state

    async with ClientSession() as session:
        while True:
            await update_ha_entity(session)
            await asyncio.sleep(5)
            # Toggle between 0 and 1
            current_state = 1 if current_state == 0 else 0


async def handle_index(request):
    """Handle the main page request."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PowerHaus Add-on</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #ffffff;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        .logo {
            font-size: 4rem;
            margin-bottom: 20px;
        }
        h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .subtitle {
            font-size: 1.1rem;
            color: #a0a0a0;
            margin-bottom: 30px;
        }
        .status {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
            padding: 20px;
            background: rgba(0, 212, 255, 0.1);
            border-radius: 10px;
            margin-top: 20px;
        }
        .status-indicator {
            width: 15px;
            height: 15px;
            background: #00ff88;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .entity-info {
            margin-top: 30px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            font-size: 0.9rem;
            color: #888;
        }
        .entity-name {
            color: #00d4ff;
            font-family: monospace;
            font-size: 1rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">⚡</div>
        <h1>PowerHaus</h1>
        <p class="subtitle">Home Assistant Add-on</p>

        <div class="status">
            <div class="status-indicator"></div>
            <span>Add-on is running</span>
        </div>

        <div class="entity-info">
            <p>Publishing entity: <span class="entity-name">sensor.powerhaus</span></p>
            <p style="margin-top: 10px;">State toggles between 0 and 1 every 5 seconds</p>
        </div>
    </div>
</body>
</html>"""
    return web.Response(text=html_content, content_type='text/html')


async def handle_health(request):
    """Health check endpoint."""
    return web.json_response({"status": "ok", "entity_state": current_state})


async def start_background_tasks(app):
    """Start background tasks."""
    app['entity_toggle_task'] = asyncio.create_task(toggle_entity_task())


async def cleanup_background_tasks(app):
    """Cleanup background tasks."""
    app['entity_toggle_task'].cancel()
    try:
        await app['entity_toggle_task']
    except asyncio.CancelledError:
        pass


def main():
    """Main entry point."""
    app = web.Application()

    # Routes
    app.router.add_get('/', handle_index)
    app.router.add_get('/health', handle_health)

    # Handle ingress path
    app.router.add_get('/ingress', handle_index)

    # Background tasks
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    # Get port from environment or use default
    port = int(os.environ.get("INGRESS_PORT", 8099))

    logger.info(f"Starting PowerHaus Add-on on port {port}")
    web.run_app(app, host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
