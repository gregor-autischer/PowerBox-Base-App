# PH_HA_Main_AddOn

PowerHaus Home Assistant Add-on.

## Local Development

### Quick Start

```bash
# 1. Start Home Assistant and the add-on
docker compose up -d

# 2. Wait for HA to start, then open http://localhost:8123
#    Complete the onboarding wizard

# 3. Get a Long-Lived Access Token:
#    - Go to your Profile (bottom left)
#    - Scroll to "Long-Lived Access Tokens"
#    - Create a token and copy it

# 4. Create .env file with your token
echo "HA_TOKEN=your_token_here" > .env

# 5. Restart the add-on to pick up the token
docker compose restart powerhaus

# 6. View the add-on UI at http://localhost:8099
#    Check HA for sensor.powerhaus entity
```

### URLs

| URL | Service |
|-----|---------|
| http://localhost:8123 | Home Assistant |
| http://localhost:8099 | PowerHaus Add-on UI |

### Development Workflow

To see changes to `app.py`:

```bash
docker compose restart powerhaus
```

To rebuild completely:

```bash
docker compose down
docker compose up --build -d
```

View logs:

```bash
docker compose logs -f powerhaus
```

### How it Works

The add-on in dev mode connects directly to Home Assistant's REST API using your long-lived token. In production (when installed via the Supervisor), it uses the Supervisor API automatically.
