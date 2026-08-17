# Changelog

## 3.14.0 (2026-08-17)

- **feat:** Mod-aware updates: "Do not update if modded" now works — the manager detects mod files (`.jar`/`.zip`) inside `mods/` and skips server updates when the option is enabled (default on). Previously the checkbox silently did nothing.
- **fix:** GUI: Removed the fake mutual exclusivity between "Check for Server Updates" and "Do not update if modded"; both can be enabled simultaneously.
- **fix:** GUI: Discord input fields (webhook/token/channel) are now hidden when Discord is disabled.
- **fix:** GUI: The console now uses a platform-appropriate monospace font (Consolas on Windows, Menlo on macOS, DejaVu Sans Mono on Linux) instead of hardcoded Consolas.
- **perf:** GUI: The Server RAM and AOT Cache fields now save on commit (Enter/blur) instead of on every keystroke.
- **chore:** Removed the unused `install_service_ui` GUI method (systemd install remains available via `-install-service`).
- **docs:** Documented `modded_do_not_update` and `update_to_prerelease` in the README config reference and CLI help; corrected the pre-release bullet (`-patchline` is passed to the Hytale updater, not a manager flag) and the stale "macOS autostart not supported" note (`-enable-autostart` installs a LaunchAgent).

## 3.13.0 (2026-08-17)

- **feat:** Console mode: interactive command input — each stdin line is forwarded to the server console (parity with the GUI command bar). Degrades to idle under no-tty/systemd (stdin EOF).
- **feat:** AOT cache: auto-detect bundled `HytaleServer.aot` and pass `-XX:AOTCache` automatically; a missing custom `server_aot` path now falls back to the bundled cache with a warning.
- **feat:** Graceful shutdown: console mode handles `SIGTERM` (systemd `stop`) like `SIGINT` — sends `stop`, waits, escalates SIGTERM → SIGKILL on Unix before exiting.
- **fix:** Server launch: removed redundant `_JAVA_OPTIONS` env var (duplicated `-Xmx`, polluted stderr, and leaked into child JVMs); heap is passed on the command line only.
- **fix:** Server stop: Unix stop now escalates `stop` command → 15s → SIGTERM → 15s → SIGKILL instead of jumping straight to SIGKILL after 30s.
- **perf:** Console mode logging reuses a single persistent `hsm.log` handle instead of open/write/close per log line.
- **docs:** README version badge/caption/config reference corrected; documented console command input, `server_aot`, and graceful shutdown.


- **fix:** Locking: Prevent PID reuse conflicts by writing the script's absolute path to the lock file and validating process cmdline/directory via `psutil`. Gracefully handles legacy lock files.

## 3.12.1 (2026-06-10)

- **fix:** Windows: Ensure script runs with `.pyw` extension under `pythonw.exe`. Automatically renames and restarts from `.py` on launch.
- **fix:** Self-Updater: Add smart handling of `.py` on Windows to download the update targeting `.pyw`, clean up the legacy `.py` file, and restart under `pythonw.exe`.

## 3.12.0 (2026-06-04)

- **feat:** Auto-start: Implement native macOS LaunchAgent autostart support via a user plist file. Adds `-disable-autostart` option.
- **feat:** Requirements: Add recommended/optional `discord.py` comment to requirements.txt.
- **feat:** GUI: Add Find in Console log search and highlight utility (previous/next jumping, yellow selection).
- **feat:** GUI: Add a new Backup Manager dialog to list, delete, and safely restore world backups.

## 3.11.4 (2026-05-22)

- **fix:** GUI: Seed CPU metrics and use non-blocking `psutil.cpu_percent(interval=None)` to eliminate periodic 100ms stutter.
- **fix:** Discord Bot: Rename shadowed local coroutine commands (`status_cmd`, `start_cmd`, `stop_cmd`, `restart_cmd`) so the core server controls can be correctly called from Discord.
- **fix:** Updater: Force credentials file path to resolve to `BASE_DIR` instead of executable directory to prevent crashes on read-only system filesystems (e.g. `/usr/bin/java`).
- **fix:** Locking: Implement robust platform-specific fallback process check (using `tasklist` on Windows, `os.kill(pid, 0)` on Unix) to support single-instance detection when `psutil` is not yet installed.

## 3.11.3 (2026-04-20)

- **fix:** Prompts: Improve missing GUI dependency prompts with OS-specific install commands.
- **fix:** Compatibility: Add platform-specific Java 25 requirement check and dialog alerts.
- **feat:** Downloader: Switch pre-release downloader arg to `-patchline pre-release` per Hytale manual specs.

## 3.11.1 (2026-04-20)

- **feat:** Auto-start: Update cross-platform autostart behavior and checkbox integration for Windows registry, Linux desktop, and macOS login items.

## 3.11.0 (2026-04-20)

- **feat:** Layout: Clean up GUI config area with column-based layout (General, Updates, Backup, Discord).
- **feat:** Linux: Add Install Service systemd setup button in footer.
- **feat:** Downloader: Add `update_to_prerelease` option to track pre-release channel.

## 3.10.22 (2025-03-21)

- **fix:** CPU/RAM: #statsContainer explicit footer_bg (overrides QWidget black)

## 3.10.21 (2025-03-21)

- **fix:** Control config box: footer grey (#181818) bg; buttons = discord input grey (#222222)

## 3.10.20 (2025-03-21)

- **feat:** Config: "Do not update if modded" checkbox (mutually exclusive with "Check for new server updates")
- **fix:** Remove "(Uncheck if modded)" label

## 3.10.19 (2025-03-21)

- **fix:** CPU/RAM: use psutil.cpu_percent(interval=0.1); update in _refresh_uptime (fixes 0% display)

## 3.10.18 (2025-03-21)

- **fix:** Status label: color only "Running"/"Stopped", keep "Status:" in default theme color

## 3.10.17 (2025-03-21)

- **fix:** Status label: poll core state in _refresh_uptime (fixes "Stopped" when server running)
- **fix:** Status colors: Stopped = red (#e53935), Running = green (#43a047)
- **fix:** Start/Stop buttons: disabled state styled grey (#666) when inactive

## 3.10.16 (2025-03-21)

- **chore:** Module docstring; section comments (Constants, Config, Core, CLI, GUI, Main)
- **chore:** Replace bare `except:` with `except OSError` or `except Exception`
- **chore:** README: new screenshot, platform badge (Windows | Linux | macOS), version link to CHANGELOG

## 3.10.15 (2025-03-21)

- **fix:** Uptime counter: add GUI-side QTimer polling `core.get_uptime_str()` every second
- **fix:** Action column: center CPU, RAM, and uptime labels under Start/Stop buttons (AlignHCenter)

## 3.10.14 (2025-03-22)

- **fix:** Footer: reduced padding; vertically center buttons/checkboxes (AlignVCenter)

## 3.10.13 (2025-03-22)

- **fix:** Dark mode: input boxes 1 shade lighter (#222222) for better contrast with GUI bg

## 3.10.12 (2025-03-22)

- **fix:** Footer 1px taller (35px); buttons/checkboxes margin-top 1px (fix top-line clipping)

## 3.10.11 (2025-03-22)

- **fix:** Status label: remove max-height, add padding (fix descender cut-off on "Stopped")

## 3.10.10 (2025-03-22)

- **fix:** Footer: buttons and checkbox labels nudged up 2px for vertical centering

## 3.10.9 (2025-03-22)

- **fix:** Footer: skinny (34px), buttons 24px height, font 10px, padding 2px 6px (no text cut-off)

## 3.10.8 (2025-03-22)

- **fix:** Footer buttons: min-height 24px, padding 6px 10px (text no longer cut off)
- **fix:** Config col1/col2: uniform spacing 6px between fields

## 3.10.7 (2025-03-22)

- **fix:** Remove boxes around QLabel (input labels, status); footer taller (40px) + margins

## 3.10.6 (2025-03-22)

- **fix:** Footer skinnier (max-height 32px, reduced margins)
- **fix:** Remove box around "(Uncheck if modded)"; Status label skinnier (max-height 18px)
- **fix:** Uptime not updating: update_stats logic was outside apply() when HAS_PSUTIL

## 3.10.5 (2025-03-22)

- **fix:** Remove "| Comprehensive Server Management Tool" from header
- **fix:** Dark mode: checkbox labels transparent background (no black bg)

## 3.10.4 (2025-03-22)

- **fix:** Light mode: checkbox selection visible (dark grey bg + white check)
- **fix:** Dark mode: buttons/footer #181818 (not black); consistent config labels (no green labels)

## 3.10.3 (2025-03-22)

- **fix:** Check for updates: actually run installer and restart (was only logging)
- **fix:** Light theme: force QMainWindow/QWidget background to button grey (#d4d0c8)

## 3.10.2 (2025-03-21)

- **fix:** Dark theme: Cursor IDE palette (#0b0b0b bg, #1e1e1e sections, #333333 borders, #3fb950 accent)

## 3.10.1 (2025-03-21)

- **fix:** Light theme GUI background now uses Windows retro grey (#d4d0c8)
- **fix:** Checkbox checkmarks: generate PNG at runtime (Qt loads reliably); remove SVG

## 3.10.0 (2025-03-21)

- **feat:** Visible checkmarks in checkboxes (white for dark, black for light) via custom SVG icons
- **feat:** Light theme: 90s retro Windows style (#c0c0c0, 3D inset/outset borders, black text)
- **feat:** Footer: "Check for updates" button; donate changed to "☕ Buy me a coffee"
- **fix:** Console stays black in both themes (yellow text legibility)

## 3.9.9 (2025-03-21)

- **feat:** Dark theme: Cursor-IDE / VS Code Dark+ (#1e1e1e) with 1px silver borders
- **fix:** Light theme: default Windows colors (#f0f0f0), console light grey (#e5e5e5)
- **fix:** Compact "(Uncheck if modded)" label layout; remove redundant QGroupBox stylesheet

## 3.9.8 (2025-03-21)

- **feat:** Dark theme: modern grey platform (Discord-like #36393f); console remains black
- **fix:** Light theme legibility: dark text on light console, themed inputs, muted labels
- **fix:** Theme-aware checkboxes, group boxes, frames; Discord integration section styling

## 3.9.7 (2025-03-21)

- **feat:** Single-instance detection; prevents multiple hsm.pyw from fighting over server
- **fix:** Default checkboxes (visible checkmark); slight hover effect on checkboxes

## 3.9.6 (2025-03-21)

- **feat:** Extended debug.log: server lifecycle (start/stop/crash/restart), backup, commands, schedule

## 3.9.5 (2025-03-21)

- **feat:** Interactive buttons/checkboxes: hover color change, active button glow (PySide6 QSS)
- **fix:** Console text 1pt smaller (8pt) for better fit

## 3.9.4 (2025-03-21)

- **feat:** Pre-req check before GUI; visible warning + auto-install when PySide6/psutil missing
- **feat:** Works with pythonw (no console): tkinter → Windows MessageBox → macOS osascript → Linux zenity/kdialog → fallback help file
- **refactor:** psutil optional; show N/A for CPU/RAM when missing

## 3.9.3 (2025-03-21)

- **refactor:** Remove rich; add IS_PYTHONW; skip input() in exception handlers when pythonw to prevent hang

## 3.9.2 (2025-03-21)

- **feat:** Add debug.log on startup; timestamped event logging for diagnosing launch failures (e.g. pythonw spinner on Windows)

## 3.9.1 (2025-03-21)

- **fix:** Restore Tkinter-like compact layout: 1080x800 window, dense controls, large central console, command input at bottom

## 3.9.0 (2025-03-21)

- **feat:** Cross-platform support: Windows, Linux, Arch Linux, macOS with platform-specific handling
- **feat:** Migrate GUI from Tkinter to PySide6 for improved cross-platform appearance and stability
- **refactor:** Replace tkinter/ttk widgets with Qt equivalents; apply Fusion style with dark/light palette
- **fix:** Correct donate handler to use core.log() instead of non-existent log_queue_wrapper attribute
- **fix:** Ensure thread-safe UI updates from background monitor via QTimer.singleShot
- **build:** Add requirements.txt with psutil and PySide6 dependencies
