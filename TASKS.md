# TASKS

## Active

- (none)

## Completed by Version

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
