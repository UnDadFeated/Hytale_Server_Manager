# Changelog

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
