# Conversation Log

## 2025-03-21 (continued)

- **Code cleanup:** Module docstring; section comments; bare `except:` → `except OSError`/`Exception`
- **README:** New screenshot; platform badge (Windows | Linux | macOS); version 3.10.16; link to CHANGELOG
- **Version:** 3.10.15 → 3.10.16 (PATCH)

---

## 2025-03-21

- **Uptime counter fix:** Added `get_uptime_str()` to core; GUI polls via QTimer every 1s. Uptime no longer relies on monitor-loop callbacks.
- **Layout:** CPU, RAM, uptime centered under Start/Stop buttons using `Qt.AlignHCenter` and stats_container wrapper.
- **Version:** 3.10.14 → 3.10.15 (PATCH)

---

