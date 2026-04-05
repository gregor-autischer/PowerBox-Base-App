# PowerHaus Add-on

PowerHaus extends Home Assistant with secure remote access and cloud backup capabilities through the PowerHaus Studio platform.

## Features

- **Cloud Backups** — Automatically back up and restore your Home Assistant instance through Home Assistant's native backup system, stored securely in PowerHaus Studio.
- **SSH Access** — Secure shell access to your Home Assistant host with public key authentication, managed through PowerHaus Studio.
- **Web Terminal** — Browser-based terminal accessible from the Home Assistant sidebar, with token-based authentication.
- **Real-time Dashboard** — View and monitor your Home Assistant entities from the PowerHaus panel.

## How It Works

Once installed, PowerHaus registers itself as a backup agent in Home Assistant. Your backups are securely streamed to PowerHaus Studio for cloud storage. SSH keys are managed centrally through Studio and synced to the add-on automatically.

The add-on also installs a companion integration (`powerhaus`) into Home Assistant that enables the backup agent functionality.

## Configuration

### SSH Options

| Option | Default | Description |
|--------|---------|-------------|
| `ssh.username` | `hassio` | The SSH username for shell access |
| `ssh.authorized_keys` | `[]` | Additional local SSH public keys (Studio keys are synced automatically) |
| `ssh.sftp` | `false` | Enable SFTP file transfer subsystem |
| `ssh.allow_tcp_forwarding` | `false` | Enable SSH TCP port forwarding |

### Connecting via SSH

```bash
ssh hassio@<your-ha-ip>
```

SSH access requires a public key registered either locally (via the `authorized_keys` option) or through PowerHaus Studio.

## Network Ports

| Port | Protocol | Description |
|------|----------|-------------|
| 22 | TCP | SSH server |
| 8099 | TCP | Web UI (accessed via Home Assistant ingress) |

## Support

For issues and feature requests, visit the [PowerHaus GitHub repository](https://github.com/gregor-autischer/PH_HA_Main_AddOn/issues).
