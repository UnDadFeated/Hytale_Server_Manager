# Conversation Log

## 2025-03-21 (status fix)

- **Status label fix:** _refresh_uptime now polls core.server_process directly; status no longer stuck on Stopped
- **Status colors:** Stopped = red (#e53935), Running = green (#43a047)
- **Version:** 3.10.16 → 3.10.17 (PATCH)

---

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

