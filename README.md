# Hytale Server Manager

A Python automation script for managing Dedicated Hytale Servers.

![Hytale Server Manager Screenshot](screenshot.png)

## Features

* **GUI & Console Modes**: Use the modern graphical interface or headless console mode (`-nogui`) for flexible management.
* **Robustness**: Automated crash detection, scheduled restarts, and world backups (zips locally before starting).
* **Reliable Auto-Updates**: Checks `git master` via HTTP to automatically download and install updates using a safe installer script.
* **Performance**: Detects and enables Ahead-Of-Time (`HytaleServer.aot`) cache for faster startups.
* **Notifications**: Integrated Discord Webhooks for server status changes (Start, Stop, Crash).
* **Background Scanning**: Automatically checks for server updates every 30 minutes and restarts if found.
* **Linux Integration**: Native systemd service support and desktop auto-start capabilities.
* **Platform Checks**: auto-detects Java 25 and `Assets.zip` requirements.

## Requirements

* **Operating System**: Windows or Linux
* **Python 3.x**:
  * **Windows**: [Download from Python.org](https://www.python.org/downloads/windows/) (Ensure "Add Python to PATH" is checked)
  * **Linux**: Usually pre-installed. (`sudo apt install python3 python3-tk` might be needed for GUI).

* **Java 25**: [Download from Adoptium](https://adoptium.net/temurin/releases/?version=25)
* **Internet Connection**: Required for downloading updates and Discord webhooks.

## Installation

1. Clone this repository or download `hsm.py`.
2. Place the scripts in your desired server folder.

## Usage

### Graphical Mode (Default)

Run the script without arguments to open the GUI:

```bash
python hsm.py
```

* **Controls**: Toggle Backups, Discord Webhooks, and Auto-Restart directly from the UI.
* **Quick Access**: Open Server, World, and Backup folders.
* **Themes**: Toggle between Light and Dark mode.

### Console Mode (Headless)

Run with the `-nogui` argument for CLI-only operation:

```bash
python hsm.py -nogui
```

* Configuration is loaded from `hsm.conf`.

### Linux Extras

**Install as Service** (Runs in background, auto-restarts on crash/reboot):

```bash
sudo python3 hsm.py -install-service
sudo systemctl start hytale-manager
```

**Enable Desktop Auto-Start**:

```bash
python3 hsm.py -enable-autostart
```

### Help

View all command line arguments:

```bash
python hsm.py -help
```

## Configuration

Settings are saved to `hsm.conf`. Key features:

```json
{
  "enable_backups": true,
  "max_backups": 3,
  "enable_discord": true,
  "discord_webhook": "YOUR_WEBHOOK_URL",
  "enable_auto_restart": true,
  "enable_schedule": false,
  "restart_interval": 12,
  "manager_auto_update": true
}
```

## Versioning

Current Version: 3.3.4
