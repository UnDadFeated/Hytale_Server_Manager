# TASKS

## Active

- (none)

## Completed by Version

### 3.10.18 (2025-03-21)

- [x] Status label: color only Running/Stopped, not "Status:"

### 3.10.17 (2025-03-21)

- [x] Status label: poll core state; fix "Stopped" when server running
- [x] Status colors: Stopped red, Running green
- [x] Start/Stop buttons: disabled state grey when inactive

### 3.10.16 (2025-03-21)

- [x] Code cleanup: docstring, section comments, bare except fixes
- [x] README: new screenshot, platform badge, CHANGELOG link

### 3.10.15 (2025-03-21)

- [x] Uptime counter: GUI polling via get_uptime_str() every 1s
- [x] Center CPU, RAM, uptime under buttons (AlignHCenter)

### 3.10.14 (2025-03-22)

- [x] Footer: lower padding, center buttons vertically

### 3.10.13 (2025-03-22)

- [x] Dark mode: input boxes 1 shade lighter (#222222)

### 3.10.12 (2025-03-22)

- [x] Footer 1px taller; buttons moved down 1px (fix top clipping)

### 3.10.11 (2025-03-22)

- [x] Status label: fix "Stopped" descenders cut off

### 3.10.10 (2025-03-22)

- [x] Footer: buttons and checkbox text centered (margin-top -2px)

### 3.10.9 (2025-03-22)

- [x] Footer: skinny, smaller buttons (24px), 10px font, no cut-off

### 3.10.8 (2025-03-22)

- [x] Footer button text not cut off; config col spacing even

### 3.10.7 (2025-03-22)

- [x] Remove label/status boxes; footer taller

### 3.10.6 (2025-03-22)

- [x] Footer skinnier; remove mod box; Status skinnier; fix uptime

### 3.10.5 (2025-03-22)

- [x] Remove header subtitle; checkbox labels transparent bg (dark mode)

### 3.10.4 (2025-03-22)

- [x] Light: checkbox checked = dark grey + white check (visible)
- [x] Dark: buttons/footer grey #181818; consistent fg labels

### 3.10.3 (2025-03-22)

- [x] Check for updates: run installer and restart
- [x] Light theme: explicit QMainWindow/QWidget bg #d4d0c8

### 3.10.2 (2025-03-21)

- [x] Dark theme: Cursor IDE palette from 7.png

### 3.10.1 (2025-03-21)

- [x] Light theme: GUI bg #d4d0c8 (match retro grey button)
- [x] Checkbox: runtime PNG generation for visible checkmarks

### 3.10.0 (2025-03-21)

- [x] Checkbox checkmark visibility (check_white.svg, check_black.svg)
- [x] Light theme: 90s retro Windows style; console black in both themes
- [x] Footer: Check for updates button; Buy me a coffee donate button

### 3.9.9 (2025-03-21)

- [x] Dark theme: Cursor-IDE (#1e1e1e), 1px silver borders
- [x] Light theme: Windows default bg, light grey console
- [x] Compact "(Uncheck if modded)" label; remove redundant stylesheet

### 3.9.8 (2025-03-21)

- [x] Dark theme: modern grey platform (#36393f), console black
- [x] Light theme: legible contrast (console, labels, inputs)
- [x] Theme-aware checkboxes, frames, muted labels

### 3.9.7 (2025-03-21)

- [x] Single-instance detection (lock file, PID check)
- [x] Default checkboxes with slight hover effect

### 3.9.6 (2025-03-21)

- [x] Extended debug.log: server start/stop/crash, backup, send_command, schedule restart

### 3.9.5 (2025-03-21)

- [x] Interactive buttons: hover color, active glow (PySide6 QSS)
- [x] Checkbox hover color change
- [x] Console text 1pt smaller (8pt)

### 3.9.4 (2025-03-21)

- [x] Pre-req check (PySide6, psutil) before GUI launch
- [x] Visible warning + Install option for pythonw (tkinter/MessageBox/osascript/zenity/help file)
- [x] psutil optional; CPU/RAM show N/A when missing

### 3.9.3 (2025-03-21)

- [x] Remove rich (no console with pythonw); add IS_PYTHONW
- [x] Skip input() in exception handlers when pythonw to prevent hang

### 3.9.2 (2025-03-21)

- [x] Add debug.log on startup; timestamped event logging; overwrite each launch

### 3.9.1 (2025-03-21)

- [x] Restore compact Tkinter-like layout (1080×800, dense controls, large central console, command input at bottom)

### 3.9.0 (2025-03-21)

- [x] Migrate GUI from Tkinter to PySide6
- [x] Cross-platform support: Windows, Linux, Arch Linux, macOS
- [x] Add platform constants (IS_WINDOWS, IS_LINUX, IS_DARWIN)
- [x] macOS updater candidate support (darwin-arm64, darwin-amd64)
- [x] Linux/Arch install-service and enable-autostart utilities
- [x] macOS-friendly messaging for unsupported CLI autostart
- [x] Update README with OS-specific installation and run instructions
- [x] Add requirements.txt with psutil and PySide6

## Backlog

- Optional: Add macOS LaunchAgent support for CLI autostart
