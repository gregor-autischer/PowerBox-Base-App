#!/usr/bin/env python3
"""PowerHaus Add-on - Main Application."""

import asyncio
import os
import json
import logging
import time
from pathlib import Path
import aiohttp
from aiohttp import web, ClientSession, WSMsgType, MultipartReader, ClientTimeout

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

# Studio API configuration
STUDIO_API_BASE = os.environ.get("STUDIO_API_BASE", "").rstrip("/")
BOX_API_TOKEN = os.environ.get("BOX_API_TOKEN", "")

# Backup stream chunk size (256 KB)
BACKUP_CHUNK_SIZE = 262144

# SSH username (from HA addon options, default hassio)
SSH_USERNAME = "hassio"

# Config sync state
synced_config = {
    "ssh_authorized_keys": [],
}

# Terminal token cache (token → expiry timestamp)
terminal_token_cache = {}
TERMINAL_TOKEN_CACHE_TTL = 60  # seconds to cache valid tokens locally

# Internal ttyd credential (read from /data/ttyd_credential at startup)
TTYD_CREDENTIAL = ""

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


async def _check_terminal_auth(request) -> web.Response | None:
    """Check terminal access token. Returns error response or None if valid."""
    token = request.query.get("token", "")
    if not token:
        return web.json_response({"error": "Terminal token required"}, status=401)
    if not await validate_terminal_token(token):
        return web.json_response({"error": "Invalid or expired terminal token"}, status=401)
    return None


async def handle_terminal_proxy(request):
    """Proxy HTTP requests to ttyd running on port 7681."""
    auth_error = await _check_terminal_auth(request)
    if auth_error:
        return auth_error

    path = request.match_info.get('path', '')
    ttyd_url = f"http://127.0.0.1:7681/api/terminal/{path}"
    query_string = request.query_string
    if query_string:
        ttyd_url += f"?{query_string}"

    # Build auth for internal ttyd credential
    ttyd_auth = aiohttp.BasicAuth("powerhaus", TTYD_CREDENTIAL) if TTYD_CREDENTIAL else None

    async with ClientSession(auth=ttyd_auth) as session:
        try:
            async with session.request(
                method=request.method,
                url=ttyd_url,
                headers={k: v for k, v in request.headers.items()
                         if k.lower() not in ('host', 'content-length', 'authorization')},
                data=await request.read(),
            ) as resp:
                body = await resp.read()
                return web.Response(
                    body=body,
                    status=resp.status,
                    headers={k: v for k, v in resp.headers.items()
                             if k.lower() not in ('transfer-encoding', 'content-encoding')},
                )
        except Exception as e:
            logger.error(f"Terminal proxy error: {e}")
            return web.json_response(
                {"error": "Terminal not available", "detail": str(e)},
                status=502,
            )


async def handle_terminal_ws(request):
    """Proxy WebSocket connections to ttyd."""
    auth_error = await _check_terminal_auth(request)
    if auth_error:
        return auth_error

    ws_client = web.WebSocketResponse(protocols=['tty'])
    await ws_client.prepare(request)

    path = request.match_info.get('path', '')
    ttyd_ws_url = f"ws://127.0.0.1:7681/api/terminal/{path}"
    query_string = request.query_string
    if query_string:
        ttyd_ws_url += f"?{query_string}"

    ttyd_auth = aiohttp.BasicAuth("powerhaus", TTYD_CREDENTIAL) if TTYD_CREDENTIAL else None

    async with ClientSession(auth=ttyd_auth) as session:
        try:
            async with session.ws_connect(
                ttyd_ws_url,
                protocols=['tty'],
            ) as ttyd_ws:
                async def relay_from_ttyd():
                    async for msg in ttyd_ws:
                        if msg.type == WSMsgType.TEXT:
                            await ws_client.send_str(msg.data)
                        elif msg.type == WSMsgType.BINARY:
                            await ws_client.send_bytes(msg.data)
                        elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                            break

                async def relay_from_client():
                    async for msg in ws_client:
                        if msg.type == WSMsgType.TEXT:
                            await ttyd_ws.send_str(msg.data)
                        elif msg.type == WSMsgType.BINARY:
                            await ttyd_ws.send_bytes(msg.data)
                        elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                            break

                await asyncio.gather(relay_from_ttyd(), relay_from_client())
        except Exception as e:
            logger.error(f"Terminal WebSocket proxy error: {e}")

    return ws_client


def _studio_headers() -> dict[str, str]:
    """Build authorization headers for Studio API calls."""
    return {
        "Authorization": f"Bearer {BOX_API_TOKEN}",
    }


async def handle_backup_upload(request):
    """Receive backup from HA integration and proxy-upload to Studio.

    Expects multipart/form-data with:
      - 'metadata': JSON with AgentBackup fields
      - 'backup_file': the .tar backup stream
    """
    if not STUDIO_API_BASE or not BOX_API_TOKEN:
        return web.json_response(
            {"error": "Studio API not configured (STUDIO_API_BASE / BOX_API_TOKEN)"},
            status=503,
        )

    reader = await request.multipart()
    metadata = None
    backup_file_part = None

    # Parse multipart parts
    while True:
        part = await reader.next()
        if part is None:
            break
        if part.name == "metadata":
            raw = await part.read(decode=True)
            metadata = json.loads(raw)
        elif part.name == "backup_file":
            backup_file_part = part

        if metadata and backup_file_part:
            break

    if not metadata or not backup_file_part:
        return web.json_response(
            {"error": "Missing metadata or backup_file part"},
            status=400,
        )

    backup_id = metadata.get("backup_id", "")

    async def _stream_from_part():
        """Yield chunks from the multipart file part."""
        while True:
            chunk = await backup_file_part.read_chunk(BACKUP_CHUNK_SIZE)
            if not chunk:
                break
            yield chunk

    # Build multipart upload to Studio
    async with ClientSession() as session:
        try:
            with web.MultipartWriter("form-data") as writer:
                meta_part = writer.append(json.dumps(metadata))
                meta_part.set_content_disposition("form-data", name="metadata")
                meta_part.headers["Content-Type"] = "application/json"

                file_part = writer.append(_stream_from_part())
                file_part.set_content_disposition(
                    "form-data",
                    name="backup_file",
                    filename=f"{backup_id}.tar",
                )
                file_part.headers["Content-Type"] = "application/octet-stream"

                async with session.post(
                    f"{STUDIO_API_BASE}/studio/api/addon/backup/upload/",
                    data=writer,
                    headers=_studio_headers(),
                    timeout=ClientTimeout(total=7200),
                ) as resp:
                    body = await resp.json()
                    return web.json_response(body, status=resp.status)

        except Exception as e:
            logger.error(f"Backup upload to Studio failed: {e}")
            return web.json_response(
                {"error": "Upload to Studio failed", "detail": str(e)},
                status=502,
            )


async def handle_backup_download(request):
    """Stream a backup file from Studio back to the HA integration."""
    backup_id = request.match_info["backup_id"]

    if not STUDIO_API_BASE or not BOX_API_TOKEN:
        return web.json_response(
            {"error": "Studio API not configured"},
            status=503,
        )

    async with ClientSession() as session:
        try:
            async with session.get(
                f"{STUDIO_API_BASE}/studio/api/addon/backup/download/{backup_id}/",
                headers=_studio_headers(),
            ) as resp:
                if resp.status == 404:
                    return web.json_response({"error": "Backup not found"}, status=404)
                if resp.status != 200:
                    body = await resp.text()
                    return web.json_response(
                        {"error": f"Studio returned {resp.status}", "detail": body},
                        status=resp.status,
                    )

                # Stream response back to caller
                response = web.StreamResponse(
                    status=200,
                    headers={
                        "Content-Type": "application/octet-stream",
                        "Content-Disposition": f'attachment; filename="{backup_id}.tar"',
                    },
                )
                await response.prepare(request)

                async for chunk in resp.content.iter_chunked(BACKUP_CHUNK_SIZE):
                    await response.write(chunk)

                await response.write_eof()
                return response

        except Exception as e:
            logger.error(f"Backup download from Studio failed: {e}")
            return web.json_response(
                {"error": "Download from Studio failed", "detail": str(e)},
                status=502,
            )


async def handle_backup_list(request):
    """List backups stored on Studio."""
    if not STUDIO_API_BASE or not BOX_API_TOKEN:
        return web.json_response({"backups": []})

    async with ClientSession() as session:
        try:
            async with session.post(
                f"{STUDIO_API_BASE}/studio/api/addon/backup/list/",
                headers=_studio_headers(),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return web.json_response(data)
                return web.json_response({"backups": []})
        except Exception as e:
            logger.error(f"Backup list from Studio failed: {e}")
            return web.json_response({"backups": []})


async def handle_backup_get(request):
    """Get a specific backup's metadata from Studio."""
    backup_id = request.match_info["backup_id"]

    if not STUDIO_API_BASE or not BOX_API_TOKEN:
        return web.json_response({"error": "Not found"}, status=404)

    async with ClientSession() as session:
        try:
            async with session.get(
                f"{STUDIO_API_BASE}/studio/api/addon/backup/{backup_id}/",
                headers=_studio_headers(),
            ) as resp:
                data = await resp.json()
                return web.json_response(data, status=resp.status)
        except Exception as e:
            logger.error(f"Backup get from Studio failed: {e}")
            return web.json_response({"error": str(e)}, status=502)


async def handle_backup_delete(request):
    """Delete a backup from Studio."""
    backup_id = request.match_info["backup_id"]

    if not STUDIO_API_BASE or not BOX_API_TOKEN:
        return web.json_response({"error": "Studio not configured"}, status=503)

    async with ClientSession() as session:
        try:
            async with session.delete(
                f"{STUDIO_API_BASE}/studio/api/addon/backup/{backup_id}/",
                headers=_studio_headers(),
            ) as resp:
                data = await resp.json()
                return web.json_response(data, status=resp.status)
        except Exception as e:
            logger.error(f"Backup delete from Studio failed: {e}")
            return web.json_response({"error": str(e)}, status=502)


async def config_sync_task():
    """Background task: periodically sync config from Studio, update authorized_keys."""
    await asyncio.sleep(30)  # wait for services to stabilize

    while True:
        if STUDIO_API_BASE and BOX_API_TOKEN:
            try:
                async with ClientSession() as session:
                    async with session.post(
                        f"{STUDIO_API_BASE}/studio/api/addon/config/sync/",
                        headers=_studio_headers(),
                        json={},
                        timeout=ClientTimeout(total=15),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            config = data.get("config", data)

                            # Update SSH authorized keys
                            new_keys = config.get("ssh_authorized_keys", [])
                            if new_keys != synced_config["ssh_authorized_keys"]:
                                synced_config["ssh_authorized_keys"] = new_keys
                                await _write_authorized_keys(new_keys)
                                logger.info(f"Updated authorized_keys with {len(new_keys)} key(s)")
            except Exception as e:
                logger.debug(f"Config sync error (will retry): {e}")

        await asyncio.sleep(60)


async def _write_authorized_keys(keys: list[str]):
    """Write SSH authorized keys to the user's authorized_keys file."""
    username = SSH_USERNAME
    ssh_dir = f"/home/{username}/.ssh"
    auth_keys_path = f"{ssh_dir}/authorized_keys"

    try:
        os.makedirs(ssh_dir, exist_ok=True)
        with open(auth_keys_path, "w") as f:
            for key in keys:
                key = key.strip()
                if key:
                    f.write(f"{key}\n")
        os.chmod(auth_keys_path, 0o600)
    except Exception as e:
        logger.error(f"Failed to write authorized_keys: {e}")


async def validate_terminal_token(token: str) -> bool:
    """Validate a terminal token against Studio (with local caching)."""
    if not token:
        return False

    now = time.time()

    # Check local cache first
    cached = terminal_token_cache.get(token)
    if cached and cached > now:
        return True

    # Ask Studio to validate
    if not STUDIO_API_BASE or not BOX_API_TOKEN:
        return False

    try:
        async with ClientSession() as session:
            async with session.post(
                f"{STUDIO_API_BASE}/studio/api/addon/terminal/validate/",
                headers=_studio_headers(),
                json={"token": token},
                timeout=ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("valid"):
                        # Cache the valid token locally
                        terminal_token_cache[token] = now + TERMINAL_TOKEN_CACHE_TTL
                        return True
    except Exception as e:
        logger.debug(f"Terminal token validation error: {e}")

    return False


async def start_background_tasks(app):
    """Start background tasks."""
    app['entity_toggle_task'] = asyncio.create_task(toggle_entity_task())
    app['config_sync_task'] = asyncio.create_task(config_sync_task())

    # Load ttyd internal credential
    global TTYD_CREDENTIAL
    try:
        with open("/data/ttyd_credential", "r") as f:
            TTYD_CREDENTIAL = f.read().strip()
    except FileNotFoundError:
        logger.warning("No ttyd credential found at /data/ttyd_credential")


async def cleanup_background_tasks(app):
    """Cleanup background tasks."""
    for task_name in ('entity_toggle_task', 'config_sync_task'):
        task = app.get(task_name)
        if task:
            task.cancel()
            try:
                await task
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

    # Backup proxy routes (integration → add-on → Studio)
    app.router.add_post('/api/backup/upload', handle_backup_upload)
    app.router.add_get('/api/backup/download/{backup_id}', handle_backup_download)
    app.router.add_get('/api/backup/list', handle_backup_list)
    app.router.add_get('/api/backup/{backup_id}', handle_backup_get)
    app.router.add_delete('/api/backup/{backup_id}', handle_backup_delete)

    # Terminal proxy routes (ttyd on port 7681)
    app.router.add_route('*', '/api/terminal/ws', handle_terminal_ws)
    app.router.add_route('*', '/api/terminal/{path:.*}', handle_terminal_proxy)

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
