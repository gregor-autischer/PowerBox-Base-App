# PowerHaus Home Assistant Add-on Repository

[![Home Assistant Add-on](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/hassio/)

Smart home management with cloud backups, SSH access, and a web terminal for Home Assistant.

## Installation

1. Open your Home Assistant instance.
2. Navigate to **Settings** > **Add-ons** > **Add-on Store**.
3. Click the menu icon (three dots, top right) and select **Repositories**.
4. Add this repository URL:
   ```
   https://github.com/gregor-autischer/PH_HA_Main_AddOn
   ```
5. Find **PowerHaus** in the add-on store and click **Install**.

## Add-ons in this repository

### [PowerHaus](./powerhaus)

Cloud backups, secure SSH access, and a web terminal for your Home Assistant instance. Connects to PowerHaus Studio for centralized key management and backup storage.

**Features:**
- Cloud backup via Home Assistant's native backup system
- SSH access with public key authentication
- Browser-based web terminal
- Real-time entity dashboard

## Development

See the [dev/](./dev) directory for local development setup using Docker Compose.

```bash
cd dev
cp .env.example ../.env
# Edit .env with your HA long-lived access token
docker compose up -d
```

- Home Assistant: http://localhost:8123
- PowerHaus Add-on: http://localhost:8099
