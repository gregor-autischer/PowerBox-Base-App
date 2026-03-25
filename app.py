#!/usr/bin/env python3
"""PowerHaus Add-on - Main Application."""

import asyncio
import os
import json
import logging
from pathlib import Path
from aiohttp import web, ClientSession, WSMsgType

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
    """Handle the main page request - serve the Vue app."""
    static_dir = Path(__file__).parent / "static"
    index_file = static_dir / "index.html"

    if index_file.exists():
        return web.FileResponse(index_file)

    # Fallback if static files not built yet
    return web.Response(
        text="<h1>Frontend not built</h1><p>Run 'npm install && npm run build' to build the frontend.</p>",
        content_type='text/html'
    )


async def handle_health(request):
    """Health check endpoint."""
    return web.json_response({"status": "ok", "entity_state": current_state})


async def handle_entities(request):
    """Fetch all entities from Home Assistant."""
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    async with ClientSession() as session:
        try:
            async with session.get(f"{HA_API_URL}/states", headers=headers) as response:
                if response.status == 200:
                    entities = await response.json()
                    return web.json_response(entities)
                else:
                    text = await response.text()
                    return web.json_response(
                        {"error": f"Failed to fetch entities: {response.status}", "detail": text},
                        status=response.status
                    )
        except Exception as e:
            logger.error(f"Error fetching entities: {e}")
            return web.json_response({"error": str(e)}, status=500)


async def handle_websocket(request):
    """WebSocket proxy to Home Assistant for live updates."""
    ws_client = web.WebSocketResponse()
    await ws_client.prepare(request)

    # Connect to Home Assistant WebSocket
    ha_ws_url = HA_API_URL.replace("/api", "/api/websocket").replace("http", "ws")

    async with ClientSession() as session:
        try:
            async with session.ws_connect(ha_ws_url) as ha_ws:
                # HA sends auth_required first
                msg = await ha_ws.receive_json()
                logger.info(f"HA WebSocket: {msg}")

                # Authenticate
                await ha_ws.send_json({
                    "type": "auth",
                    "access_token": HA_TOKEN
                })

                # Wait for auth_ok
                msg = await ha_ws.receive_json()
                if msg.get("type") != "auth_ok":
                    await ws_client.send_json({"error": "Authentication failed", "detail": msg})
                    await ws_client.close()
                    return ws_client

                await ws_client.send_json({"type": "auth_ok"})

                # Subscribe to state changes
                await ha_ws.send_json({
                    "id": 1,
                    "type": "subscribe_events",
                    "event_type": "state_changed"
                })

                # Relay messages between client and HA
                async def relay_from_ha():
                    async for msg in ha_ws:
                        if msg.type == WSMsgType.TEXT:
                            await ws_client.send_str(msg.data)
                        elif msg.type == WSMsgType.ERROR:
                            break

                async def relay_from_client():
                    async for msg in ws_client:
                        if msg.type == WSMsgType.TEXT:
                            await ha_ws.send_str(msg.data)
                        elif msg.type == WSMsgType.ERROR:
                            break

                await asyncio.gather(relay_from_ha(), relay_from_client())

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await ws_client.send_json({"error": str(e)})

    return ws_client


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
    app.router.add_get('/api/entities', handle_entities)
    app.router.add_get('/api/ws', handle_websocket)

    # Handle ingress path
    app.router.add_get('/ingress', handle_index)

    # Serve static files (JS, CSS, assets from Vite build)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.router.add_static('/assets', static_dir / "assets")

    # Background tasks
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)

    # Get port from environment or use default
    port = int(os.environ.get("INGRESS_PORT", 8099))

    logger.info(f"Starting PowerHaus Add-on on port {port}")
    web.run_app(app, host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
