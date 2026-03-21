# Changelog

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
