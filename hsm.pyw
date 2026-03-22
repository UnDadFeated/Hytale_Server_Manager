"""
Hytale Server Manager - GUI and console automation for Hytale dedicated servers.

Manages server lifecycle, updates, backups, Discord integration, and systemd/autostart.
"""
import os
import sys
import datetime

_script_dir = os.path.dirname(os.path.abspath(__file__))
DEBUG_LOG = os.path.join(_script_dir, "debug.log")
_debug_handle = None

def _debug(event, msg):
    """Write timestamped debug event to debug.log (overwritten each launch)."""
    global _debug_handle
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{ts}] [{event}] {msg}\n"
        if _debug_handle is None:
            _debug_handle = open(DEBUG_LOG, "w", encoding="utf-8")
        _debug_handle.write(line)
        _debug_handle.flush()
    except Exception:
        pass

_debug("START", f"Process started | PID={os.getpid()} | argv={sys.argv!r} | cwd={os.getcwd()}")
_debug("START", f"executable={sys.executable} | pythonw={('pythonw' in sys.executable.lower())}")

import subprocess
import time
import shutil
import atexit
import urllib.request
import zipfile
import threading
import queue
import platform
import re
import signal
import json
import traceback
import webbrowser
import contextlib

_debug("IMPORT", "core stdlib imports done")
try:
    import psutil
    HAS_PSUTIL = True
    _debug("IMPORT", "psutil OK")
except ImportError as e:
    HAS_PSUTIL = False
    psutil = None
    _debug("IMPORT", f"psutil FAIL: {e}")

# --- Constants ---
# Windows flag for hiding child console windows.
if platform.system() == "Windows":
    CREATE_NO_WINDOW = 0x08000000
    # Also optionally use STARTUPINFO to hide things deeper if needed.
else:
    CREATE_NO_WINDOW = 0
__version__ = "3.10.22"
JAVA_VERSION_REQ = 25
SERVER_JAR = "HytaleServer.jar"
UPDATER_ZIP_URL = "https://downloader.hytale.com/hytale-downloader.zip"
UPDATER_ZIP_FILE = "hytale-downloader.zip"
IS_WINDOWS = platform.system() == "Windows"
IS_DARWIN = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"
IS_PYTHONW = IS_WINDOWS and "pythonw" in sys.executable.lower()
UPDATER_EXECUTABLE = "hytale-downloader.exe" if IS_WINDOWS else "hytale-downloader"
ASSETS_FILE = "Assets.zip"
AOT_FILE = "HytaleServer.aot"
BACKUP_DIR = "universe/backups"
WORLD_DIR = "universe/worlds"

# Always resolve paths relative to the script's own directory.
# This ensures the manager works correctly when launched by Windows at startup
# (which sets CWD to System32 by default).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHECK_WHITE_PNG = os.path.join(BASE_DIR, ".check_white.png")
CHECK_BLACK_PNG = os.path.join(BASE_DIR, ".check_black.png")
LOG_FILE = os.path.join(BASE_DIR, "hsm.log")
CONFIG_FILE = os.path.join(BASE_DIR, "hsm.conf")
LOCK_FILE = os.path.join(BASE_DIR, ".hsm.lock")

console = None  # No rich; pythonw has no console

try:
    import discord
    from discord.ext import commands
    HAS_DISCORD = True
    _debug("IMPORT", "discord OK")
except ImportError:
    HAS_DISCORD = False
    _debug("IMPORT", "discord skip (optional)")


# --- Locking & Dependencies ---
def _acquire_single_instance_lock():
    """Returns (True, None) if we got the lock, else (False, error_msg)."""
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if HAS_PSUTIL and psutil.pid_exists(old_pid):
                return False, f"Another instance is already running (PID {old_pid}). Close it first."
            try:
                os.remove(LOCK_FILE)
            except OSError:
                pass
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        def _release():
            try:
                if os.path.exists(LOCK_FILE):
                    os.remove(LOCK_FILE)
            except OSError:
                pass
        atexit.register(_release)
        return True, None
    except Exception as e:
        _debug("LOCK", f"acquire failed: {e}")
        return True, None

def _check_gui_requirements():
    """Returns list of missing packages required for GUI."""
    missing = []
    try:
        import PySide6  # noqa: F401
    except ImportError:
        missing.append("PySide6")
    if not HAS_PSUTIL:
        missing.append("psutil")
    return missing


def _show_missing_deps_and_offer_install(missing):
    """
    Show a visible warning that deps are missing and offer to install.
    Works with pythonw (no console). Returns True if user chose Install and it succeeded (or deps now OK).
    """
    pkg_list = ", ".join(missing)
    msg = (
        f"Hytale Server Manager cannot start the GUI.\n\n"
        f"Missing: {pkg_list}\n\n"
        f"Would you like to install them now?"
    )
    def do_install():
        exe = sys.executable
        if IS_WINDOWS and "pythonw" in exe.lower():
            exe = exe.replace("pythonw.exe", "python.exe").replace("pythonw", "python.exe")
        cmd = [exe, "-m", "pip", "install"] + missing
        _debug("DEPS", f"Running: {cmd}")
        try:
            r = subprocess.run(cmd)
            _debug("DEPS", f"pip exit code: {r.returncode}")
            return r.returncode == 0
        except Exception as e:
            _debug("DEPS", f"pip failed: {e}")
            return False

    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        if messagebox.askyesno("Hytale Server Manager - Missing Requirements", msg):
            root.destroy()
            ok = do_install()
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("Hytale Server Manager", "Restart the application." if ok else f"Install failed. Run: pip install {pkg_list}")
            root.destroy()
            return ok
        root.destroy()
        return False
    except Exception as e:
        _debug("DEPS", f"tkinter failed: {e}")

    if IS_WINDOWS:
        try:
            import ctypes
            MB_YESNO = 0x4
            IDYES = 6
            r = ctypes.windll.user32.MessageBoxW(0, msg, "Hytale Server Manager - Missing Requirements", MB_YESNO)
            if r != IDYES:
                _debug("DEPS", "User chose No")
                return False
            ok = do_install()
            ctypes.windll.user32.MessageBoxW(
                0,
                "Installation complete. Restart the application." if ok else "Installation failed. Try: pip install " + pkg_list,
                "Hytale Server Manager",
                0x40,
            )
            return ok
        except Exception as e:
            _debug("DEPS", f"MessageBox fallback failed: {e}")

    if IS_DARWIN:
        try:
            msg_esc = msg.replace('"', "'").replace("\n", " ")[:200]
            script = f'display dialog "{msg_esc}" with title "Hytale Server Manager" buttons {{"Install", "Cancel"}} default button "Install"'
            r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if "Install" not in (r.stdout or ""):
                return False
            ok = do_install()
            result_msg = ("Restart the application." if ok else f"Install failed. Run: pip install {pkg_list}").replace('"', "'")
            subprocess.run(["osascript", "-e", f'display dialog "{result_msg}" with title "Hytale Server Manager" buttons {{"OK"}}'], capture_output=True)
            return ok
        except Exception as e:
            _debug("DEPS", f"osascript failed: {e}")

    if IS_LINUX:
        try:
            for cmd in ["zenity", "kdialog"]:
                try:
                    r = subprocess.run([cmd, "--question", "--text=" + msg[:500], "--title=Hytale Server Manager"], capture_output=True)
                    if r.returncode == 0:
                        ok = do_install()
                        subprocess.run([cmd, "--msgbox", "Restart the application." if ok else f"Install failed. Run: pip install {pkg_list}"], capture_output=True)
                        return ok
                    return False
                except FileNotFoundError:
                    continue
        except Exception as e:
            _debug("DEPS", f"Linux dialog failed: {e}")

    help_path = os.path.join(BASE_DIR, "INSTALL_REQUIREMENTS.txt")
    try:
        with open(help_path, "w", encoding="utf-8") as f:
            f.write(f"Hytale Server Manager - Missing: {pkg_list}\n\n")
            f.write("Run this command in Command Prompt (Windows) or Terminal (Mac/Linux):\n\n")
            f.write(f"    pip install {pkg_list}\n\n")
            f.write("Or:  pip install -r requirements.txt\n")
        if IS_WINDOWS:
            os.startfile(help_path)
        elif IS_DARWIN:
            subprocess.run(["open", help_path])
        else:
            subprocess.run(["xdg-open", help_path], capture_output=True)
    except Exception as e:
        _debug("DEPS", f"Could not write help file: {e}")
    return False


# --- Configuration ---
def validate_config(config):
    """
    Validates and corrects configuration values to prevent runtime errors.
    
    Args:
        config (dict): The configuration dictionary to validate.
        
    Returns:
        dict: The validated configuration dictionary.
    """
    # Validate server_memory format (e.g., 4G, 4096M)
    mem = str(config.get("server_memory", "8G"))
    if not re.match(r"(?i)^\d+[GM]$", mem):
        print(f"WARNING: Invalid server_memory format '{mem}'. Reverting to 8G.")
        config["server_memory"] = "8G"
    else:
        config["server_memory"] = mem.upper()

    # Interval check
    try:
        float(config.get("restart_interval", 12))
    except ValueError:
        print("WARNING: Invalid restart_interval. Reverting to 12.0.")
        config["restart_interval"] = 12.0

    return config

def load_config():
    """Loads the server configuration from the JSON file."""
    default_config = {
        "last_server_version": "3.3.4",
        "dark_mode": True,
        "enable_logging": True,
        "check_updates": True,
        "auto_start": False,
        "enable_backups": True,
        "enable_discord": False,
        "discord_webhook": "",
        "discord_token": "", # New for Bot
        "discord_channel_id": 0, # New for Bot
        "enable_auto_restart": True,
        "enable_schedule": False,
        "restart_interval": 12,
        "server_memory": "8G",
        "max_backups": 3,
        "manager_auto_update": True,
        "start_with_windows": False
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                loaded = json.load(f)
                default_config.update(loaded)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    return validate_config(default_config)

def save_config(config):
    """Saves the current configuration to the JSON file."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")

# --- Core Logic ---
class HytaleUpdaterCore:
    """
    Core logic controller for the Hytale Server Manager.
    
    Handles server process management, updates, backups, discord integration, 
    and background monitoring tasks.
    """
    
    def __init__(self, log_callback, input_callback=None, config=None, status_callback=None):
        self.log_callback = log_callback
        self.input_callback = input_callback
        self.status_callback = status_callback
        self.config = config if config else load_config()
        
        self.server_process = None
        self.stop_requested = False
        self.restart_timer = None
        self.update_timer = None
        self.monitor_thread = None
        self.start_time = None
        self.discord_bot = None

        self._lifecycle_lock = threading.Lock()
        self._starting = False

        if self.config.get("enable_discord", False) and HAS_DISCORD and self.config.get("discord_token"):
             self.start_discord_bot()

    def log(self, message, tag=None):
        """
        Logs a message to the registered callback and optional rich console.
        
        Args:
            message (str): The message to log.
            tag (str, optional): A tag for categorization (e.g., 'stderr', 'error').
        """
        self.log_callback(message, tag)

    def update_status(self, status):
        """Updates the status via the callback."""
        if self.status_callback:
            self.status_callback(status)

    def get_uptime_str(self):
        """Returns current uptime string if server is running, else '00:00:00'."""
        if self.server_process and self.server_process.poll() is None and self.start_time:
            uptime = datetime.datetime.now() - self.start_time
            return str(uptime).split('.')[0]
        return "00:00:00"

    def start_discord_bot(self):
        """Starts the Discord Bot in a separate thread."""
        token = self.config.get("discord_token")
        channel_id = self.config.get("discord_channel_id", 0)
        
        if not token: return

        # Define Bot Class inline to access manager instance
        class HytaleBot(commands.Bot):
            def __init__(self, manager_core):
                intents = discord.Intents.default()
                if hasattr(intents, "message_content"):
                    intents.message_content = True
                super().__init__(command_prefix="!", intents=intents)
                self.manager = manager_core
            
            async def on_ready(self):
                self.manager.log(f"Discord Bot logged in as {self.user}")
                if channel_id:
                    channel = self.get_channel(int(channel_id))
                    if channel: await channel.send("🟢 **Hytale Manager Connected!**")

        self.discord_bot = HytaleBot(self)

        @self.discord_bot.command(name="status")
        async def status(ctx):
            if self.server_process:
                await ctx.send(f"✅ Server is **Running** (PID: {self.server_process.pid})")
            else:
                await ctx.send("🔴 Server is **Stopped**")

        @self.discord_bot.command(name="start")
        async def start_server(ctx):
            if self.server_process:
                await ctx.send("Server is already running.")
            else:
                await ctx.send("🚀 Starting server...")
                self.start_server_sequence()

        @self.discord_bot.command(name="stop")
        async def stop_server(ctx):
            if self.server_process:
                await ctx.send("🛑 Stopping server...")
                self.stop_server()
            else:
                await ctx.send("Server is already stopped.")
        
        @self.discord_bot.command(name="restart")
        async def restart_server(ctx):
            await ctx.send("🔄 Restarting server...")
            self.stop_server()
            # specific restart logic for the bot
            threading.Timer(5.0, self.start_server_sequence).start()

        def run_bot():
            try:
                self.discord_bot.run(token)
            except Exception as e:
                print(f"Discord Bot Error: {e}")

        threading.Thread(target=run_bot, daemon=True).start()

    def check_java_version(self):
        """Verifies if Java 25 or higher is installed and available."""
        self.log("Checking Java version...")
        try:
            kwargs = {}
            if IS_WINDOWS:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                kwargs["startupinfo"] = startupinfo
                kwargs["creationflags"] = CREATE_NO_WINDOW
                
            result = subprocess.run(["java", "-version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kwargs)
            output = result.stdout
            
            match = re.search(r'version "(?:1\.)?(\d+)', output)
            if match:
                major_version = int(match.group(1))
                if major_version >= JAVA_VERSION_REQ:
                    self.log(f"Java {major_version} detected.")
                    return True
                else:
                    self.log(f"WARNING: Java {major_version} detected, but Java {JAVA_VERSION_REQ} or higher is required. Output:\n{output}")
                    return False
            else:
                # Fallback string matching
                if f'version "{JAVA_VERSION_REQ}' in output or f'version "1.{JAVA_VERSION_REQ}' in output:
                    self.log(f"Java {JAVA_VERSION_REQ} detected.")
                    return True
                
                self.log(f"WARNING: Java {JAVA_VERSION_REQ} or higher not detected. Output:\n{output}")
                return False
        except FileNotFoundError:
            self.log("ERROR: Java not found in PATH.")
            return False

    def check_assets(self):
        """Checks if the required assets file exists, asking the user if missing."""
        self.log(f"Checking for {ASSETS_FILE}...")
        cwd = os.getcwd()
        assets_path = os.path.join(cwd, ASSETS_FILE)
        
        if os.path.exists(assets_path):
            self.log(f"Found {ASSETS_FILE} at {assets_path}")
            return assets_path
        
        self.log(f"{ASSETS_FILE} not found in {cwd}")
        
        if self.input_callback:
            user_path = self.input_callback(f"Please enter the full path to {ASSETS_FILE}: ")

            if user_path and isinstance(user_path, str) and os.path.exists(user_path) and os.path.basename(user_path) == ASSETS_FILE:
                 try:
                     shutil.copy(user_path, cwd)
                     self.log(f"Copied {ASSETS_FILE} to server directory.")
                     return os.path.join(cwd, ASSETS_FILE)
                 except Exception as e:
                     self.log(f"Error copying file: {e}")
                     return None
        return None

    def ensure_updater(self):
        """Ensures the Hytale updater executable is available."""
        # Check for standard executable name or platform specific names
        candidates = [UPDATER_EXECUTABLE]
        if IS_WINDOWS:
            candidates.append("hytale-downloader-windows-amd64.exe")
        elif IS_DARWIN:
            # Apple Silicon first, then Intel
            candidates.extend(["hytale-downloader-darwin-arm64", "hytale-downloader-darwin-amd64"])
        else:
            # Linux (including Arch)
            candidates.append("hytale-downloader-linux-amd64")
            
        for cand in candidates:
            if os.path.exists(cand):
                 if not IS_WINDOWS and not os.access(cand, os.X_OK):
                     try: os.chmod(cand, 0o755)
                     except OSError:
                         pass
                 return [f"./{cand}"] if not IS_WINDOWS else [cand]

        if os.path.exists("hytale-downloader.jar"):
            return ["java", "-jar", "hytale-downloader.jar"]

        self.log(f"Updater executable not found. Checking for cached zip: {UPDATER_ZIP_FILE}...")
        
        should_download = True
        if os.path.exists(UPDATER_ZIP_FILE):
             try:
                 self.log(f"Found cached {UPDATER_ZIP_FILE}, checking remote size...")
                 req = urllib.request.Request(UPDATER_ZIP_URL, method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
                 with urllib.request.urlopen(req) as response:
                     remote_size = int(response.headers.get('Content-Length', 0))
                     local_size = os.path.getsize(UPDATER_ZIP_FILE)
                     
                     if remote_size > 0 and remote_size == local_size:
                         self.log("Local zip matches remote size. Skipping download.")
                         should_download = False
                     else:
                         self.log(f"Size mismatch (Local: {local_size}, Remote: {remote_size}). Redownloading...")
             except Exception as e:
                 self.log(f"Error checking remote size: {e}. forcing download.")

        if should_download:
            self.log(f"Updater not found in cache or invalid. Downloading from {UPDATER_ZIP_URL}...")
            try:
                req = urllib.request.Request(UPDATER_ZIP_URL, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    with open(UPDATER_ZIP_FILE, "wb") as f:
                        while chunk := response.read(65536):
                            f.write(chunk)
            except Exception as e:
                 self.log(f"Download failed: {e}")
                 return None

        try:
            with zipfile.ZipFile(UPDATER_ZIP_FILE, 'r') as zip_ref:
                zip_ref.extractall(".")
            
            # Re-check for candidates after extraction
            for cand in candidates:
                if os.path.exists(cand):
                    if not IS_WINDOWS and not os.access(cand, os.X_OK):
                        try: os.chmod(cand, 0o755)
                        except OSError:
                            pass
                    return [f"./{cand}"] if not IS_WINDOWS else [cand]
            
            # Fallback scan for any extracted binary
            for f in os.listdir('.'):
                if not f.startswith("hytale-downloader"):
                    continue
                if f.endswith(".jar"):
                    return ["java", "-jar", f]
                if IS_WINDOWS and f.endswith(".exe"):
                    return [f]
                if not IS_WINDOWS and "." not in f:
                    try:
                        os.chmod(f, 0o755)
                    except OSError:
                        pass
                    return [f"./{f}"]
            return None
        except Exception as e:
            self.log(f"Failed to download/extract updater: {e}")
            return None

    def resolve_command_path(self, cmd_list):
        """Resolves absolute paths for command execution."""
        new_cmd = cmd_list.copy()
        if not new_cmd: return new_cmd
        
        if new_cmd[0].startswith("./") or os.path.exists(new_cmd[0]):
             new_cmd[0] = os.path.abspath(new_cmd[0])
        
        if len(new_cmd) > 2 and "java" in new_cmd[0] and new_cmd[1] == "-jar":
             if os.path.exists(new_cmd[2]):
                 new_cmd[2] = os.path.abspath(new_cmd[2])
        return new_cmd

    def stop_existing_server_process(self):
        """Detects and stops any running instance of the Hytale server."""
        _debug("SERVER", "stop_existing_server_process() checking for orphaned java/HytaleServer.jar")
        self.log("Checking for running Hytale server...")
        if IS_WINDOWS:
            try:
                kwargs = {}
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                kwargs["startupinfo"] = startupinfo
                kwargs["creationflags"] = CREATE_NO_WINDOW
                
                cmd = (
                    'powershell -NoProfile -Command "'
                    'Get-WmiObject Win32_Process | '
                    'Where-Object { $_.Name -eq \'java.exe\' -and $_.CommandLine -like \'*HytaleServer.jar*\' } | '
                    'Select-Object -ExpandProperty ProcessId"'
                )
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True, **kwargs)
                for line in result.stdout.splitlines():
                    pid = line.strip()
                    if pid.isdigit():
                        self.log(f"Found running server (PID: {pid}). Stopping...")
                        subprocess.run(f"taskkill /PID {pid} /F", shell=True, creationflags=CREATE_NO_WINDOW)
            except Exception: pass
        else:
             try:
                cmd = ["pgrep", "-f", SERVER_JAR]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    for pid in result.stdout.strip().splitlines():
                        self.log(f"Found running server (PID: {pid}). Stopping...")
                        subprocess.run(["kill", pid])
             except Exception: pass

    def get_remote_server_version(self, updater_cmd):
        """Queries the updater for the latest remote server version."""
        try:
            cmd = updater_cmd + ["-print-version"]
            
            CREDENTIALS_FILE = ".hytale-downloader-credentials.json"
            exe_dir = os.path.dirname(os.path.abspath(updater_cmd[0]))
            cred_path = os.path.join(exe_dir, CREDENTIALS_FILE)
            cmd.extend(["-credentials-path", cred_path])

            try:
                # Ensure the executable directory is writable on Linux
                if not IS_WINDOWS and os.path.exists(exe_dir):
                    try:
                        os.chmod(exe_dir, 0o775)
                    except Exception:
                        pass
                # We use a 10s timeout. If the downloader halts to prompt for an OAuth login,
                # it will timeout. We can then gracefully catch the timeout and display the prompt.
                kwargs = {}
                if IS_WINDOWS:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    kwargs["startupinfo"] = startupinfo
                    kwargs["creationflags"] = CREATE_NO_WINDOW
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, **kwargs)
                if result.returncode == 0:
                    return result.stdout.strip()
                return None
            except subprocess.TimeoutExpired as e:
                if e.stdout:
                    for line in e.stdout.splitlines():
                        if "http" in line or "Authorization" in line or "authenticate" in line:
                            self.log(f"[Updater Auth Required] {line.strip()}")
                self.log("Background check timed out waiting for downloader authentication. Please restart the manager to authenticate.")
                return None
            
        except Exception as e:
            self.log(f"Version check failed: {e}")
            return None

    def check_self_update(self):
        """
        Checks the remote master branch for a newer version of this script.
        
        It compares the local __version__ with the __version__ string found in 
        the remote hytale_server_manager.py file. If a newer version is found,
        it downloads the new script and launches a separate installer process.
        """
        if not self.config.get("manager_auto_update", True):
             return False

        # Add cache buster
        ts = int(time.time())
        # We now check hytale_server_manager.py directly for the version
        MANAGER_URL = f"https://raw.githubusercontent.com/UnDadFeated/Hytale_Server_Manager/master/hsm.pyw?t={ts}"
        
        try:
            req = urllib.request.Request(MANAGER_URL, headers={'User-Agent': 'HytaleManagerUpdater'})
            with urllib.request.urlopen(req) as response:
                remote_content = response.read().decode('utf-8')
            
            remote_version = None
            # Regex to find __version__ = "x.y.z"
            match = re.search(r'__version__\s*=\s*"([^"]+)"', remote_content)
            if match:
                remote_version = match.group(1)
            
            if not remote_version:
                self.log("Could not parse remote version.")
                return False

            local_version = __version__
            
            # Semantic version comparison
            def parse_ver(v): return [int(x) for x in v.split('.')]
            
            if parse_ver(remote_version) > parse_ver(local_version):
                self.log(f"New manager version found ({remote_version}). Downloading...")
                
                # Use current file extension
                script_ext = os.path.splitext(sys.argv[0])[1]
                if script_ext not in [".py", ".pyw"]:
                     script_ext = ".py" # fallback
                     
                new_file = f"hsm{script_ext}.new"
                
                # Save the already downloaded content
                with open(new_file, "w", encoding='utf-8') as f:
                    f.write(remote_content)
                
                self.log("File downloaded. Preparing installer...")
                return True
            else:
                self.log("Manager is up to date.")
                return False

        except Exception as e:
            self.log(f"Failed to check/update manager: {e}")
            return False

    def run_update_installer(self):
        """
        Creates and executes a temporary python script to handle the self-update process.
        
        The installer waits for this process to exit, replaces the script files,
        and then restarts the manager.
        """
        args_repr = repr(sys.argv)
        installer_code = f'''
import os
import time
import sys
import subprocess

pid = {os.getpid()}
print(f"Waiting for parent process {{pid}} to close...")

def is_pid_running(p):
    try:
        if os.name == 'nt':
            # tasklist returns filter info if process not found or PID if found
            output = subprocess.check_output(f'tasklist /FI "PID eq {{p}}"', shell=True, creationflags={CREATE_NO_WINDOW}).decode()
            return str(p) in output
        else:
            os.kill(p, 0)
            return True
    except Exception:
        return False

try:
    # Wait for up to 30 seconds for parent to exit
    start_wait = time.time()
    while is_pid_running(pid):
        if time.time() - start_wait > 30:
            print("Timed out waiting for parent to close. Forcing update...")
            break
        time.sleep(1)
            
    print("Updating files...")
    time.sleep(2) # Extra buffer
    
    # Check for legacy version.py and remove it if it exists
    if os.path.exists("version.py"):
        try:
            os.remove("version.py")
            print("Removed legacy version.py")
        except Exception as e:
            print(f"Failed to remove version.py: {{e}}")

    script_ext = os.path.splitext({repr(sys.argv[0])})[1]
    if script_ext not in [".py", ".pyw"]:
        script_ext = ".py"
        
    old_file = f"hsm{{script_ext}}"
    new_file = f"hsm{{script_ext}}.new"

    if os.path.exists(new_file):
        if os.path.exists(old_file): os.remove(old_file)
        os.rename(new_file, old_file)
        print(f"Updated {{old_file}}")
        
    print("Files updated. Restarting manager...")
    
    # We want the manager to restart in pythonw if it's currently running in pythonw
    # However python is needed for the GUI to do the printing.
    # if it's currently running from a bat or standard executable we just use sys.executable
    if "pythonw" in sys.executable.lower():
         subprocess.Popen([sys.executable] + {args_repr}, creationflags={CREATE_NO_WINDOW})
    else:
         subprocess.Popen([sys.executable] + {args_repr})
    
except Exception as e:
    print(f"Update failed: {{e}}")
    if "pythonw" not in sys.executable.lower():
        input("Press Enter to exit...")
'''


        with open("updater_installer.py", "w") as f:
            f.write(installer_code)
            
        self.log("Launching installer and exiting...")
        
        # Launch using the same executable that is currently running (usually pythonw.exe on Windows)
        if IS_WINDOWS:
            subprocess.Popen([sys.executable, "updater_installer.py"], creationflags=CREATE_NO_WINDOW)
        else:
            subprocess.Popen([sys.executable, "updater_installer.py"])

        os._exit(0)

    def _install_from_zip_or_folder(self, staging_dir, specific_zip=None):
        """Helper to extract and install server files from a zip or folder in staging."""
        extracted_root = os.path.join(staging_dir, "extracted")
        if os.path.exists(extracted_root): shutil.rmtree(extracted_root)
        
        files_ready_to_copy = False
        source_bases = []

        if specific_zip:
            # SMART VERIFICATION: Peek inside zip before extracting
            try:
                self.log(f"Verifying integrity with {os.path.basename(specific_zip)}...")
                with zipfile.ZipFile(specific_zip, 'r') as zip_ref:
                    # Check 1: Assets.zip
                    assets_needs_update = False
                    try:
                        assets_info = zip_ref.getinfo("Assets.zip")
                        local_assets = os.path.join(os.getcwd(), "Assets.zip")
                        if not os.path.exists(local_assets) or os.path.getsize(local_assets) != assets_info.file_size:
                            assets_needs_update = True
                    except KeyError:
                        pass # Assets.zip not in this zip (unlikely for server zip)

                    # Check 2: Server Jar (Scanning for it since it might be in a subdir)
                    server_needs_update = False
                    jar_info = None
                    for zinfo in zip_ref.infolist():
                        if zinfo.filename.endswith("HytaleServer.jar"):
                            jar_info = zinfo
                            break
                    
                    if jar_info:
                        local_jar = os.path.join(os.getcwd(), "HytaleServer.jar")
                        if not os.path.exists(local_jar) or os.path.getsize(local_jar) != jar_info.file_size:
                            server_needs_update = True
                    else:
                        server_needs_update = True # Jar not found in zip? Suspicious, force extract.

                    if not assets_needs_update and not server_needs_update:
                        self.log("Files up to date (Verified against cached zip). Skipping extraction.")
                        return True
                    
                    self.log("Integrity mismatch detected. Extracting update...")
                    zip_ref.extractall(extracted_root)
                
                files_ready_to_copy = True
                source_bases.append(extracted_root)
                if os.path.exists(os.path.join(extracted_root, "Server")):
                        source_bases.append(os.path.join(extracted_root, "Server"))
            except Exception as e:
                self.log(f"Failed to verify/extract zip: {e}")
                return False
        else:
            # Check for ANY zip if specific one not provided
            potential_zips = [f for f in os.listdir(staging_dir) if f.endswith(".zip") and "Assets" not in f]
            if potential_zips:
                # Pick the most recent/likely one
                target_zip = os.path.join(staging_dir, potential_zips[0])
                self.log(f"Found server package: {target_zip}")
                return self._install_from_zip_or_folder(staging_dir, target_zip)
            
            # Fallback to loose files
            files_ready_to_copy = True
            source_bases.append(staging_dir)
            if os.path.exists(os.path.join(staging_dir, "Server")):
                source_bases.append(os.path.join(staging_dir, "Server"))

        any_replaced = False
        if files_ready_to_copy:
            # 1. Look for Assets.zip
            for base in source_bases:
                assets_src = os.path.join(base, ASSETS_FILE)
                if os.path.exists(assets_src):
                    try:
                        dest = os.path.join(os.getcwd(), ASSETS_FILE)
                        if os.path.exists(dest): os.remove(dest)
                        shutil.copy2(assets_src, dest)
                        self.log(f"Replaced {ASSETS_FILE} from {assets_src}")
                        any_replaced = True
                    except Exception as e: self.log(f"Error moving Assets.zip: {e}")
                    break
            
            # 2. Look for Server components
            server_components = [SERVER_JAR, "Licenses"]
            for comp in server_components:
                for base in source_bases:
                    src = os.path.join(base, comp)
                    if os.path.exists(src):
                        try:
                            dest = os.path.join(os.getcwd(), comp)
                            if os.path.isdir(src):
                                if os.path.exists(dest): shutil.rmtree(dest)
                                shutil.copytree(src, dest)
                            else:
                                if os.path.exists(dest): os.remove(dest)
                                shutil.copy2(src, dest)
                            self.log(f"Replaced {comp} from {src}")
                            any_replaced = True
                        except Exception as e: self.log(f"Error moving {comp}: {e}")
                        break

        if not any_replaced:
            self.log("WARNING: No files were replaced during install attempt.")
            return False
        
        return True

    def update_server(self):
        """Handles the server update process using the Hytale downloader."""
        updater_cmd = self.ensure_updater()
        
        if not updater_cmd:
            self.log("Cannot run update, updater not available.")
            return

        self.log("Checking for updates...")

        resolved_cmd = self.resolve_command_path(updater_cmd)

        remote_version = self.get_remote_server_version(resolved_cmd)
        local_version = self.config.get("last_server_version", "0.0.0")

        if remote_version:
            self.log(f"Remote version: {remote_version}")
            if remote_version == local_version:
                self.log(f"Config ver matches remote ({remote_version}). Checking file integrity...")
            else:
                self.log(f"New version available (Old: {local_version}, New: {remote_version}).")
        else:
            self.log("Could not determine remote version. Forcing update check...")

        try:
            staging_dir = os.path.abspath("updater_staging")
            if not os.path.exists(staging_dir):
                os.makedirs(staging_dir)
            
            # PRE-CHECK: existing zip?
            install_success = False
            if remote_version:
                # The CLI usually names zips by version, e.g. "2026.01.28-xxx.zip"
                potential_matches = [f for f in os.listdir(staging_dir) if f.startswith(remote_version) and f.endswith(".zip")]
                if potential_matches:
                     cached_zip = os.path.join(staging_dir, potential_matches[0])
                     self.log(f"Found existing cached zip: {cached_zip}. Attempting install...")
                     if self._install_from_zip_or_folder(staging_dir, cached_zip):
                         self.log("Install from cache successful! Skipping downloader.")
                         install_success = True

            if not install_success:
                 # Target the credentials file explicitly where the executable is located
                CREDENTIALS_FILE = ".hytale-downloader-credentials.json"
                exe_dir = os.path.dirname(os.path.abspath(resolved_cmd[0]))
                cred_path = os.path.join(exe_dir, CREDENTIALS_FILE)
                
                run_cmd = resolved_cmd.copy()
                run_cmd.extend(["-credentials-path", cred_path])

                # Ensure the executable directory is writable on Linux
                if not IS_WINDOWS and os.path.exists(exe_dir):
                    try:
                        os.chmod(exe_dir, 0o775)
                    except Exception:
                        pass

                self.log(f"Running updater in: {staging_dir}...")
                
                # Run the downloader CLI
                # We use stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True
                # to read line by line efficiently and print it.
                kwargs = {}
                if IS_WINDOWS:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    kwargs["startupinfo"] = startupinfo
                    kwargs["creationflags"] = CREATE_NO_WINDOW
                    
                process = subprocess.Popen(
                    run_cmd, cwd=staging_dir, 
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                    bufsize=1, universal_newlines=True, **kwargs
                )
                
                # Iterate over the output line by line as it is produced
                for line in process.stdout:
                    if line: 
                        self.log(f"[Updater] {line.strip()}")
                
                process.wait()

                if process.returncode == 0:
                    self.log("Updater finished. Installing files...")
                    if self._install_from_zip_or_folder(staging_dir):
                        install_success = True
                    else:
                         self.log("WARNING: Downloader finished but install helper failed.")
                else:
                     self.log(f"Updater exited with code {process.returncode}")

            if install_success:
                self.log("Update application successful.")
                
                if remote_version and remote_version != local_version:
                     self.config["last_server_version"] = remote_version
                     save_config(self.config)
                     self.log(f"Updated local version record to {remote_version}")

                # SUCCESS: Clean up extracted files only - KEEP THE ZIP for future verification
                try:
                    self.log("Cleaning up extracted staging files...")
                    extracted_root = os.path.join(staging_dir, "extracted")
                    if os.path.exists(extracted_root):
                        shutil.rmtree(extracted_root)
                except Exception as e:
                    self.log(f"Failed to cleanup staging: {e}")
            
            # Cleanup artifacts only but KEEP zips
            if os.path.exists(staging_dir):
                artifacts = ["QUICKSTART.md", "hytale-downloader-windows-amd64.exe", "hytale-downloader-linux-amd64", "hytale-downloader"]
                for f in artifacts:
                    p = os.path.join(staging_dir, f)
                    if os.path.exists(p):
                        try: os.remove(p)
                        except OSError:
                            pass
                
                # Cleanup OLD zips (Prune cache)
                # We want to keep ONLY the zip that matches remote_version (or the one we just installed)
                if remote_version:
                     for f in os.listdir(staging_dir):
                         if f.endswith(".zip") and not f.startswith(remote_version) and "Assets" not in f:
                             try:
                                 self.log(f"Pruning old cached zip: {f}")
                                 os.remove(os.path.join(staging_dir, f))
                             except Exception as e:
                                 self.log(f"Failed to prune {f}: {e}")

        except Exception as e:
            self.log(f"Update failed: {e}")
            self.log(traceback.format_exc())

    def send_command(self, command):
        """Sends a console command to the running server process."""
        _debug("CMD", f"send_command: {command[:50]}{'...' if len(command) > 50 else ''}")
        if self.server_process and self.server_process.poll() is None:
            try:
                self.log(f"> {command}")
                msg = (command + "\n").encode('utf-8')
                self.server_process.stdin.write(msg)
                self.server_process.stdin.flush()
            except Exception as e:
                self.log(f"Failed to send command: {e}")
        else:
             self.log("Server is not running.")

    def backup_world(self):
        """Creates a backup of the world directory."""
        if not self.config.get("enable_backups", True):
            _debug("BACKUP", "skipped (disabled)")
            return
        if not os.path.exists(WORLD_DIR):
            _debug("BACKUP", f"skipped: {WORLD_DIR} not found")
            self.log(f"Backup skipped: World directory not found at {WORLD_DIR}")
            return

        self.log(f"Creating world backup from {WORLD_DIR}...")
        if not os.path.exists(BACKUP_DIR): os.makedirs(BACKUP_DIR)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_name = os.path.join(BACKUP_DIR, f"world_backup_{timestamp}")
        
        try:
            shutil.make_archive(backup_name, 'zip', WORLD_DIR)
            _debug("BACKUP", f"created {backup_name}.zip")
            self.log(f"Backup created: {backup_name}.zip")
            
            max_b = int(self.config.get("max_backups", 3))
            backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("world_backup_") and f.endswith(".zip")])
            if len(backups) > max_b:
                for old in backups[:-max_b]:
                    try: os.remove(os.path.join(BACKUP_DIR, old))
                    except OSError:
                        pass
        except Exception as e:
            self.log(f"Backup failed: {e}")

    def send_discord_webhook(self, message):
        """Sends a status message to the configured Discord webhook."""
        if not self.config.get("enable_discord", False): return
        url = self.config.get("discord_webhook", "").strip()
        if not url: return

        try:
            data = json.dumps({"content": message}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json', 'User-Agent': 'HytaleUpdater'})
            with urllib.request.urlopen(req, timeout=10) as r: pass
        except Exception as e:
            self.log(f"Discord Webhook Failed: {e}")

    def start_server_sequence(self):
        """Initiates the server startup sequence in a separate thread."""
        t = threading.Thread(target=self._start_server_thread)
        t.daemon = True
        t.start()

    def _start_server_thread(self):
        """Internal method to handle the server startup steps."""
        with self._lifecycle_lock:
            if self.server_process and self.server_process.poll() is None:
                _debug("SERVER", "start_server_sequence skipped: already running")
                self.log("Start requested but server is already running. Skipping.")
                return
            if getattr(self, '_starting', False):
                _debug("SERVER", "start_server_sequence skipped: startup in progress")
                self.log("Startup already in progress. Skipping.")
                return
            self._starting = True
            self.stop_requested = False

        _debug("SERVER", "start_server_sequence begin")
        try:
            # 1. Manager Update Check
            if self.check_self_update():
                self.run_update_installer()
                return

            # 2. Java Check
            if not self.check_java_version(): return

            # 3. Server Check (and Downloader)
            if self.config.get("check_updates", True):
                self.stop_existing_server_process() # Stop before update to be safe
                self.update_server()

            # 4. Assets Check
            assets_path = self.check_assets()
            if not assets_path: return

            # Ensure server is stopped before start (redundant but safe if updates disabled)
            self.stop_existing_server_process()

            # 5. Backup World
            self.backup_world()

            self.log("Starting Server...")
            self.send_discord_webhook("🟢 Hytale Server Starting...")

            memory = self.config.get("server_memory", "4G")
            
            env = os.environ.copy()
            env["_JAVA_OPTIONS"] = f"-Xmx{memory}"
            
            cmd = ["java", f"-Xmx{memory}"]
            
            custom_aot = self.config.get("server_aot", "")
            if custom_aot and os.path.exists(custom_aot):
                 self.log(f"Using Custom AOT Cache: {custom_aot}")
                 cmd.append(f"-XX:AOTCache={custom_aot}")
                 
            cmd.extend(["-jar", SERVER_JAR, "--assets", assets_path])

            try:
                startupinfo = None
                creationflags = 0
                if IS_WINDOWS:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    creationflags = CREATE_NO_WINDOW
                
                self.server_process = subprocess.Popen(
                    cmd, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE,
                    startupinfo=startupinfo, creationflags=creationflags
                )
                self.start_time = datetime.datetime.now()
                _debug("SERVER", f"Started | pid={self.server_process.pid} | cmd={' '.join(cmd[:4])}...")
                self.update_status({"state": "Running", "pid": self.server_process.pid})

                threading.Thread(target=self._read_stream, args=(self.server_process.stdout, "stdout"), daemon=True).start()
                threading.Thread(target=self._read_stream, args=(self.server_process.stderr, "stderr"), daemon=True).start()
                
                self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                self.monitor_thread.start()
                
                self.start_update_checker()

                if self.config.get("enable_schedule", False):
                    self._schedule_restart()

            except Exception as e:
                _debug("SERVER", f"Failed to start: {e}")
                self.log(f"Failed to start server: {e}")
                self.update_status({"state": "Stopped"})
        finally:
            self._starting = False

    def _read_stream(self, stream, tag):
        """Reads output from the server process stdout/stderr."""
        try:
            for line_bytes in iter(stream.readline, b''):
                if line_bytes:
                    line = line_bytes.decode('utf-8', errors='replace').strip()
                    if line: self.log(line, tag)
        except Exception as e:
            self.log(f"Stream read error ({tag}): {e}", tag="stderr")
        finally:
            stream.close()

    def _monitor_loop(self):
        """Monitors the server process status."""
        if not self.server_process: return
        
        while self.server_process and self.server_process.poll() is None:
            if self.start_time:
                uptime = datetime.datetime.now() - self.start_time
                uptime_str = str(uptime).split('.')[0]
                self.update_status({
                    "state": "Running",
                    "pid": self.server_process.pid,
                    "uptime": uptime_str
                })
            
            time.sleep(1)

        rc = self.server_process.returncode
        pid = getattr(self.server_process, "pid", "?")
        self.log(f"Server exited with code {rc}")
        _debug("SERVER", f"Process exited | pid={pid} | returncode={rc} | stop_requested={self.stop_requested}")
        self.server_process = None
        self.update_status({"state": "Stopped"})
        self.send_discord_webhook(f"🔴 Server Stopped (Code {rc})")

        if rc != 0 and not self.stop_requested and self.config.get("enable_auto_restart", True):
             _debug("SERVER", "Crash detected (rc!=0) | auto_restart enabled | scheduling restart in 10s")
             self.log("Crash detected! Restarting in 10 seconds...")
             self.send_discord_webhook("⚠️ Crash detected. Restarting in 10s...")
             time.sleep(10)
             self.start_server_sequence()
        elif rc != 0:
             _debug("SERVER", f"Crash detected (rc={rc}) | auto_restart disabled or stop_requested")

    def start_update_checker(self):
        """Starts the background update checker."""
        if not self.config.get("check_updates", True):
            self.log("Background update check disabled by config.")
            return

        # 30 minutes = 1800 seconds
        interval = 1800
        self.log(f"Starting background update checker (every {interval}s).")
        
        def update_task():
            if self.stop_requested or not self.server_process: return
            self._run_background_update_check()
            # Reschedule if still running
            if not self.stop_requested and self.server_process:
                self.update_timer = threading.Timer(interval, update_task)
                self.update_timer.daemon = True
                self.update_timer.start()

        # Start first timer
        self.update_timer = threading.Timer(interval, update_task)
        self.update_timer.daemon = True
        self.update_timer.start()

    def _run_background_update_check(self):
        """Checks for updates in the background and restarts if found."""
        try:
            if self.check_self_update():
                self.log("[Background Check] New manager version found! Restarting application to apply...")
                self.send_discord_webhook("🔄 New Manager Update found! Restarting application...")
                self.stop_server()
                
                def delayed_installer():
                    while self.server_process and self.server_process.poll() is None:
                        time.sleep(1)
                    self.run_update_installer()
                
                threading.Thread(target=delayed_installer, daemon=True).start()
                return

            updater_cmd = self.ensure_updater()
            if not updater_cmd: return

            resolved_cmd = self.resolve_command_path(updater_cmd)
            remote_version = self.get_remote_server_version(resolved_cmd)
            local_version = self.config.get("last_server_version", "0.0.0")

            if remote_version:
                if remote_version != local_version:
                     self.log(f"[Background Check] New version found ({remote_version}). Restarting to update...")
                     self.send_discord_webhook(f"🚀 New update found ({remote_version})! Restarting server...")
                     self.restart_server()
                else:
                     self.log(f"[Background Check] Server is up to date ({local_version}).")
            else:
                self.log("[Background Check] Could not determine remote version.")

        except Exception as e:
            self.log(f"Background update check failed: {e}")

    def restart_server(self):
        """Restarts the server cleanly."""
        _debug("SERVER", "restart_server() called")
        self.log("Restarting server...")
        self.stop_server()
        
        def delayed_start():
            time.sleep(5) 
            self.start_server_sequence()
            
        threading.Thread(target=delayed_start, daemon=True).start()

    def stop_server(self):
        """Stops the running server process."""
        _debug("SERVER", "stop_server() called")
        self.stop_requested = True
        if self.restart_timer:
            self.restart_timer.cancel()
        if self.update_timer:
            self.update_timer.cancel()

        if self.server_process:
            self.log("Stopping server...")
            try:
                self.server_process.stdin.write(b"stop\n")
                self.server_process.stdin.flush()
            except Exception:
                pass
            try:
                self.server_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                _debug("SERVER", "stop timeout (30s) - killing process")
                self.log("Server did not stop in time. Killing process...")
                self.server_process.kill()
                self.server_process.wait()
    
    def _schedule_restart(self):
        """Schedules an automatic restart after a configured interval."""
        hours = float(self.config.get("restart_interval", 12))
        _debug("SERVER", f"scheduled restart in {hours}h")
        seconds = hours * 3600
        self.log(f"Scheduled restart in {hours} hours.")
        
        def restart_task():
            self.log("Executing scheduled restart...")
            self.send_discord_webhook("⏰ Executing scheduled restart...")
            self.stop_server()
            time.sleep(10)
            self.start_server_sequence()

        self.restart_timer = threading.Timer(seconds, restart_task)
        self.restart_timer.start()


# --- CLI Utilities ---
def install_service():
    """Installs the manager as a systemd service (Linux only)."""
    if not IS_LINUX:
        print("Service installation requires Linux with systemd (e.g. Ubuntu, Arch, Fedora).")
        if IS_DARWIN:
            print("On macOS, use launchd or add to Login Items manually.")
        return

    if os.geteuid() != 0:
        print("Error: This command must be run as root (sudo).")
        return

    service_path = "/etc/systemd/system/hytale-manager.service"
    script_path = os.path.abspath(__file__)
    working_dir = os.path.dirname(script_path)
    user = os.environ.get('SUDO_USER', 'root')

    content = f"""[Unit]
Description=Hytale Server Manager
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_dir}
ExecStart={sys.executable} {script_path} -nogui
Restart=always

[Install]
WantedBy=multi-user.target
"""
    try:
        with open(service_path, "w") as f:
            f.write(content)
        
        print(f"Service file created at {service_path}")
        subprocess.run(["systemctl", "daemon-reload"])
        subprocess.run(["systemctl", "enable", "hytale-manager"])
        print("Service enabled! Start it with: sudo systemctl start hytale-manager")
    except Exception as e:
        print(f"Failed to install service: {e}")

def enable_autostart():
    """Enables auto-start for the current user (Linux Desktop)."""
    if IS_WINDOWS:
        print("Auto-start setup via CLI is Windows-only in GUI. Use the GUI 'Start with Windows' option.")
        return
    if IS_DARWIN:
        print("macOS CLI autostart is not supported. Add the app to System Preferences > Users & Groups > Login Items.")
        return

    autostart_dir = os.path.expanduser("~/.config/autostart")
    if not os.path.exists(autostart_dir):
        os.makedirs(autostart_dir)

    desktop_file = os.path.join(autostart_dir, "hytale-manager.desktop")
    script_path = os.path.abspath(__file__)
    working_dir = os.path.dirname(script_path)

    content = f"""[Desktop Entry]
Type=Application
Name=Hytale Server Manager
Exec={sys.executable} {script_path}
Path={working_dir}
Terminal=false
"""
    try:
        with open(desktop_file, "w") as f:
            f.write(content)
        print(f"Auto-start entry created at {desktop_file}")
    except Exception as e:
        print(f"Failed to enable auto-start: {e}")

# --- Modes ---
def run_console_mode():
    """Runs the updater in console-only mode."""
    def console_logger(message, tag=None):
        """
        Callback for logging messages in console mode.
        
        Args:
            message (str): The log message.
            tag (str, optional): The log tag (e.g., 'stderr').
        """
        # File logging and fallback print (when run with python, not pythonw).
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        
        # Only print if rich console is NOT active to avoid double printing
        if not console:
             print(f"{timestamp} {message}")
        
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{timestamp} {message}\n")
        except OSError:
            pass
    
    config = load_config()
    core = HytaleUpdaterCore(console_logger, input_callback=input, config=config)
    
    print("--- Console Mode ---")
    print("Use Ctrl+C to stop. The script will try to gracefully stop the server.")
    
    core.start_server_sequence()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        core.stop_server()

# --- GUI ---
def run_gui_mode():
    """Starts the graphical user interface."""
    _debug("GUI", "run_gui_mode() entered")
    _debug("GUI", "importing PySide6.QtWidgets...")
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QGroupBox, QLabel, QPushButton, QCheckBox, QLineEdit,
        QTextEdit, QPlainTextEdit, QFrame, QMessageBox, QFileDialog,
    )
    _debug("GUI", "PySide6.QtWidgets OK")
    _debug("GUI", "importing PySide6.QtCore...")
    from PySide6.QtCore import Qt, QTimer, QUrl
    _debug("GUI", "PySide6.QtCore OK")
    _debug("GUI", "importing PySide6.QtGui...")
    from PySide6.QtGui import QPalette, QColor, QFont, QTextCursor, QTextCharFormat, QImage, QPainter, QPen, QBrush
    _debug("GUI", "PySide6.QtGui OK")

    def ensure_check_icons():
        """Create checkmark PNGs if missing (Qt loads PNG more reliably than SVG)."""
        for path, fg in [(CHECK_WHITE_PNG, QColor(255, 255, 255)), (CHECK_BLACK_PNG, QColor(0, 0, 0))]:
            if os.path.exists(path):
                continue
            img = QImage(14, 14, QImage.Format_ARGB32)
            img.fill(0)
            p = QPainter(img)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(fg, 2.5))
            p.setBrush(Qt.NoBrush)
            p.drawLine(2, 7, 5, 10)
            p.drawLine(5, 10, 12, 2)
            p.end()
            img.save(path)

    class HytaleGUI(QMainWindow):
        """Graphical User Interface for the Hytale Server Manager using PySide6."""

        def __init__(self):
            _debug("GUI", "HytaleGUI.__init__ started")
            super().__init__()
            self.setWindowTitle(f"Hytale Server Manager v{__version__}")
            self.setFixedSize(1080, 800)
            _debug("GUI", "loading config...")
            self.config = load_config()
            self.is_dark = self.config.get("dark_mode", True)
            _debug("GUI", "config OK")

            self.log_queue = queue.Queue()
            _debug("GUI", "creating HytaleUpdaterCore...")
            self.core = HytaleUpdaterCore(self.log_queue_wrapper, self.ask_file, self.config, self.update_stats)
            _debug("GUI", "core OK")

            _debug("GUI", "setup_ui...")
            self.setup_ui()
            self.apply_theme()

            self.log_timer = QTimer(self)
            self.log_timer.timeout.connect(self.drain_log_queue)
            self.log_timer.start(80)
            self.uptime_timer = QTimer(self)
            self.uptime_timer.timeout.connect(self._refresh_uptime)
            self.uptime_timer.start(1000)

            if self.config.get("auto_start", False):
                QTimer.singleShot(1000, self.start_server)
            _debug("GUI", "HytaleGUI.__init__ done")

        def setup_ui(self):
            cw = QWidget()
            self.setCentralWidget(cw)
            main = QVBoxLayout(cw)
            main.setContentsMargins(6, 4, 6, 6)
            main.setSpacing(2)

            header = QHBoxLayout()
            title = QLabel(f"Hytale Server Manager v{__version__}")
            title.setStyleSheet("font-weight: bold; font-size: 13px;")
            header.addWidget(title)
            header.addStretch()
            main.addLayout(header)

            controls = QGroupBox("Controls & Configuration")
            controls.setObjectName("controlsGroup")
            controls_layout = QHBoxLayout(controls)
            controls_layout.setContentsMargins(6, 10, 6, 6)
            controls_layout.setSpacing(16)

            col1 = QVBoxLayout()
            col1.setSpacing(6)
            self.cb_logging = QCheckBox("Enable File Logging")
            self.cb_logging.setChecked(self.config.get("enable_logging", True))
            self.cb_logging.stateChanged.connect(self.save)
            col1.addWidget(self.cb_logging)
            self.cb_autostart = QCheckBox("Auto-Start Server")
            self.cb_autostart.setChecked(self.config.get("auto_start", False))
            self.cb_autostart.stateChanged.connect(self.save)
            col1.addWidget(self.cb_autostart)
            self.cb_restart = QCheckBox("Auto-Restart on Crash")
            self.cb_restart.setChecked(self.config.get("enable_auto_restart", True))
            self.cb_restart.stateChanged.connect(self.save)
            col1.addWidget(self.cb_restart)
            ram_row = QHBoxLayout()
            ram_row.addWidget(QLabel("Server RAM:"))
            self.entry_memory = QLineEdit()
            self.entry_memory.setMaximumWidth(60)
            self.entry_memory.setText(self.config.get("server_memory", "8G"))
            self.entry_memory.textChanged.connect(self.on_config_change)
            ram_row.addWidget(self.entry_memory)
            self.lbl_reboot = QLabel("⚠ Reboot Required")
            self.lbl_reboot.setStyleSheet("color: #ff9800;")
            self.lbl_reboot.hide()
            ram_row.addWidget(self.lbl_reboot)
            ram_row.addStretch()
            col1.addLayout(ram_row)
            aot_row = QHBoxLayout()
            aot_row.addWidget(QLabel("AOT:"))
            self.entry_aot = QLineEdit()
            self.entry_aot.setMaximumWidth(120)
            self.entry_aot.setText(self.config.get("server_aot", ""))
            self.entry_aot.textChanged.connect(self.on_config_change)
            aot_row.addWidget(self.entry_aot)
            btn_aot = QPushButton("Browse")
            btn_aot.setMaximumWidth(70)
            btn_aot.clicked.connect(self.browse_aot)
            aot_row.addWidget(btn_aot)
            col1.addLayout(aot_row)
            controls_layout.addLayout(col1)

            col2 = QVBoxLayout()
            col2.setSpacing(6)
            self.cb_check_upd = QCheckBox("Check for new server updates")
            self.cb_check_upd.setChecked(self.config.get("check_updates", True))
            self.cb_check_upd.stateChanged.connect(lambda: self._on_check_updates_toggled())
            col2.addWidget(self.cb_check_upd)
            self.cb_no_update_modded = QCheckBox("Do not update if modded")
            self.cb_no_update_modded.setChecked(not self.config.get("check_updates", True))
            self.cb_no_update_modded.stateChanged.connect(lambda: self._on_no_update_modded_toggled())
            col2.addWidget(self.cb_no_update_modded)
            bkp_row = QHBoxLayout()
            self.cb_backup = QCheckBox("Backup World on Start")
            self.cb_backup.setChecked(self.config.get("enable_backups", True))
            self.cb_backup.stateChanged.connect(self.save)
            bkp_row.addWidget(self.cb_backup)
            bkp_row.addWidget(QLabel("Max:"))
            self.entry_max_backups = QLineEdit()
            self.entry_max_backups.setMaximumWidth(30)
            self.entry_max_backups.setText(str(self.config.get("max_backups", 3)))
            self.entry_max_backups.editingFinished.connect(self.save)
            bkp_row.addWidget(self.entry_max_backups)
            bkp_row.addStretch()
            col2.addLayout(bkp_row)
            sch_row = QHBoxLayout()
            self.cb_schedule = QCheckBox("Schedule Restart (Hrs)")
            self.cb_schedule.setChecked(self.config.get("enable_schedule", False))
            self.cb_schedule.stateChanged.connect(self.save)
            sch_row.addWidget(self.cb_schedule)
            self.entry_schedule = QLineEdit()
            self.entry_schedule.setMaximumWidth(45)
            self.entry_schedule.setText(str(self.config.get("restart_interval", 12)))
            self.entry_schedule.editingFinished.connect(self.save)
            sch_row.addWidget(self.entry_schedule)
            sch_row.addStretch()
            col2.addLayout(sch_row)
            controls_layout.addLayout(col2)

            dsc_box = QFrame()
            dsc_box.setFrameShape(QFrame.StyledPanel)
            dsc_layout = QVBoxLayout(dsc_box)
            dsc_layout.setContentsMargins(4, 4, 4, 4)
            dsc_layout.setSpacing(1)
            self.cb_discord = QCheckBox("Discord Integration")
            self.cb_discord.setChecked(self.config.get("enable_discord", False))
            self.cb_discord.stateChanged.connect(self.save)
            dsc_layout.addWidget(self.cb_discord)
            dsc_row1 = QHBoxLayout()
            dsc_row1.addWidget(QLabel("Webhook:"))
            self.entry_webhook = QLineEdit()
            self.entry_webhook.setPlaceholderText("URL")
            self.entry_webhook.setText(self.config.get("discord_webhook", ""))
            self.entry_webhook.editingFinished.connect(self.save)
            self.entry_webhook.setMinimumWidth(140)
            dsc_row1.addWidget(self.entry_webhook)
            dsc_layout.addLayout(dsc_row1)
            dsc_row2 = QHBoxLayout()
            dsc_row2.addWidget(QLabel("Token:"))
            self.entry_token = QLineEdit()
            self.entry_token.setEchoMode(QLineEdit.Password)
            self.entry_token.setText(self.config.get("discord_token", ""))
            self.entry_token.setMinimumWidth(140)
            self.entry_token.editingFinished.connect(self.save)
            dsc_row2.addWidget(self.entry_token)
            dsc_layout.addLayout(dsc_row2)
            dsc_row3 = QHBoxLayout()
            dsc_row3.addWidget(QLabel("Channel:"))
            self.entry_channel = QLineEdit()
            self.entry_channel.setPlaceholderText("ID")
            self.entry_channel.setText(str(self.config.get("discord_channel_id", 0)))
            self.entry_channel.setMinimumWidth(80)
            self.entry_channel.editingFinished.connect(self.save)
            dsc_row3.addWidget(self.entry_channel)
            dsc_layout.addLayout(dsc_row3)
            controls_layout.addWidget(dsc_box)

            def open_dir(path):
                try:
                    from PySide6.QtGui import QDesktopServices
                    p = os.path.abspath(path)
                    if not os.path.exists(p):
                        os.makedirs(p)
                    QDesktopServices.openUrl(QUrl.fromLocalFile(p))
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not open directory: {e}")

            nav_col = QVBoxLayout()
            nav_col.setSpacing(1)
            for lbl, path in [("Server", "."), ("Worlds", WORLD_DIR), ("Backups", BACKUP_DIR)]:
                b = QPushButton(lbl)
                b.setFixedWidth(70)
                b.setFixedHeight(22)
                b.clicked.connect(lambda checked, p=path: open_dir(p))
                nav_col.addWidget(b)
            nav_col.addSpacing(4)
            self.lbl_status = QLabel("Status: <span style='color:#e53935'>Stopped</span>")
            self.lbl_status.setObjectName("statusLbl")
            self.lbl_status.setTextFormat(Qt.RichText)
            self.lbl_status.setStyleSheet("font-weight: bold;")
            nav_col.addWidget(self.lbl_status)
            controls_layout.addLayout(nav_col)

            action_col = QVBoxLayout()
            action_col.setSpacing(2)
            self.btn_start = QPushButton("START SERVER")
            self.btn_start.setFixedHeight(26)
            self.btn_start.setFixedWidth(140)
            self.btn_start.setObjectName("btnStart")
            self.btn_start.clicked.connect(self.start_server)
            action_col.addWidget(self.btn_start)
            self.btn_stop = QPushButton("STOP SERVER")
            self.btn_stop.setFixedHeight(26)
            self.btn_stop.setFixedWidth(140)
            self.btn_stop.setObjectName("btnStop")
            self.btn_stop.setEnabled(False)
            self.btn_stop.clicked.connect(self.stop_server)
            action_col.addWidget(self.btn_stop)
            ver_lbl = QLabel(f"Version: {self.config.get('last_server_version', 'Unknown')}")
            ver_lbl.setObjectName("mutedLbl")
            action_col.addWidget(ver_lbl, 0, Qt.AlignHCenter)
            stats_row = QHBoxLayout()
            self.lbl_cpu = QLabel("CPU: 0%")
            self.lbl_ram = QLabel("RAM: 0%")
            self.lbl_cpu.setObjectName("mutedLbl")
            self.lbl_ram.setObjectName("mutedLbl")
            stats_row.addWidget(self.lbl_cpu)
            stats_row.addWidget(self.lbl_ram)
            stats_container = QWidget()
            stats_container.setObjectName("statsContainer")
            stats_container.setLayout(stats_row)
            action_col.addWidget(stats_container, 0, Qt.AlignHCenter)
            self.lbl_uptime = QLabel("Uptime: 00:00:00")
            self.lbl_uptime.setStyleSheet("font-size: 10px;")
            action_col.addWidget(self.lbl_uptime, 0, Qt.AlignHCenter)
            controls_layout.addLayout(action_col)

            main.addWidget(controls)

            self.console = QPlainTextEdit()
            self.console.setReadOnly(True)
            self.console.setFont(QFont("Consolas", 8))
            self.console.setMaximumBlockCount(1000)
            self.console.setMinimumHeight(300)
            main.addWidget(self.console, 1)

            cmd_frame = QFrame()
            cmd_frame.setObjectName("cmdBar")
            cmd_layout = QHBoxLayout(cmd_frame)
            cmd_layout.setContentsMargins(0, 2, 0, 2)
            cmd_layout.addWidget(QLabel("Command:"))
            self.entry_cmd = QLineEdit()
            self.entry_cmd.setPlaceholderText("Enter server command...")
            self.entry_cmd.returnPressed.connect(self.send_command_ui)
            cmd_layout.addWidget(self.entry_cmd)
            main.addWidget(cmd_frame)

            footer_frame = QFrame()
            footer_frame.setObjectName("footerBar")
            footer_frame.setMaximumHeight(35)
            footer = QHBoxLayout(footer_frame)
            footer.setSpacing(6)
            footer.setContentsMargins(3, 0, 3, 2)
            footer.setAlignment(Qt.AlignVCenter)
            theme_btn = QPushButton("Toggle Theme")
            theme_btn.setFixedHeight(24)
            theme_btn.clicked.connect(self.toggle_theme)
            footer.addWidget(theme_btn)
            btn_check = QPushButton("Check for updates")
            btn_check.setFixedHeight(24)
            btn_check.clicked.connect(self.check_updates_ui)
            self.cb_mgr_update = QCheckBox("Auto-Update Manager")
            self.cb_mgr_update.setChecked(self.config.get("manager_auto_update", True))
            self.cb_mgr_update.stateChanged.connect(self.save)
            footer.addWidget(self.cb_mgr_update)
            self.cb_start_win = QCheckBox("Start with Windows")
            self.cb_start_win.setChecked(self.config.get("start_with_windows", False))
            self.cb_start_win.stateChanged.connect(self.save_and_set_autostart)
            if not IS_WINDOWS:
                self.cb_start_win.setEnabled(False)
            footer.addWidget(self.cb_start_win)
            footer.addStretch()
            footer.addWidget(btn_check)
            btn_coffee = QPushButton("☕ Support the Development")
            btn_coffee.setFixedHeight(24)
            btn_coffee.clicked.connect(self.open_donation_link)
            footer.addWidget(btn_coffee)
            main.addWidget(footer_frame)

        def browse_aot(self):
            path, _ = QFileDialog.getOpenFileName(self, "Select AOT File", "", "AOT Files (*.aot);;All Files (*)")
            if path:
                self.entry_aot.setText(path)
                self.save()

        def check_updates_ui(self):
            self.core.log("Checking for manager and server updates...")
            if self.core.check_self_update():
                self.core.log("Manager update found. Restarting...")
                self.core.stop_server()

                def do_install():
                    while self.core.server_process and self.core.server_process.poll() is None:
                        time.sleep(0.5)
                    self.core.run_update_installer()

                threading.Thread(target=do_install, daemon=True).start()
            else:
                self.core.log("Up to date.")

        def open_donation_link(self):
            donate_url = "https://buymeacoffee.com/jscheema"
            try:
                with open(os.devnull, "w") as null_err:
                    with contextlib.redirect_stderr(null_err):
                        success = webbrowser.open(donate_url)
                if not success:
                    self.core.log(f"[Donate] Could not open browser. Please visit: {donate_url}")
            except Exception as e:
                self.core.log(f"[Donate] Failed to open browser ({e}). Please visit: {donate_url}")

        def send_command_ui(self):
            cmd = self.entry_cmd.text().strip()
            if cmd:
                self.core.send_command(cmd)
                self.entry_cmd.clear()
                self.entry_cmd.setFocus()

        def on_config_change(self):
            self.save()
            if self.core.server_process and self.core.server_process.poll() is None:
                self.lbl_reboot.show()
            else:
                self.lbl_reboot.hide()

        def start_server(self):
            self.lbl_reboot.hide()
            self.save()
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.core.start_server_sequence()

        def stop_server(self):
            self.core.stop_server()
            self.btn_stop.setEnabled(False)

        def _on_check_updates_toggled(self):
            """Mutually exclusive: exactly one of Check for updates / Do not update if modded."""
            self.cb_no_update_modded.blockSignals(True)
            self.cb_no_update_modded.setChecked(not self.cb_check_upd.isChecked())
            self.cb_no_update_modded.blockSignals(False)
            self.save()

        def _on_no_update_modded_toggled(self):
            """Mutually exclusive: exactly one of Check for updates / Do not update if modded."""
            self.cb_check_upd.blockSignals(True)
            self.cb_check_upd.setChecked(not self.cb_no_update_modded.isChecked())
            self.cb_check_upd.blockSignals(False)
            self.save()

        def save(self):
            ch = self.entry_channel.text().strip()
            mb = self.entry_max_backups.text().strip()
            self.config.update({
                "enable_logging": self.cb_logging.isChecked(),
                "check_updates": self.cb_check_upd.isChecked(),
                "auto_start": self.cb_autostart.isChecked(),
                "enable_backups": self.cb_backup.isChecked(),
                "enable_discord": self.cb_discord.isChecked(),
                "enable_auto_restart": self.cb_restart.isChecked(),
                "enable_schedule": self.cb_schedule.isChecked(),
                "discord_webhook": self.entry_webhook.text(),
                "discord_token": self.entry_token.text(),
                "discord_channel_id": int(ch) if ch.isdigit() else 0,
                "restart_interval": self.entry_schedule.text(),
                "server_memory": self.entry_memory.text(),
                "server_aot": self.entry_aot.text(),
                "max_backups": int(mb) if mb.isdigit() else 3,
                "manager_auto_update": self.cb_mgr_update.isChecked(),
                "start_with_windows": self.cb_start_win.isChecked(),
            })
            self.core.config = self.config
            save_config(self.config)

        def save_and_set_autostart(self):
            self.save()
            if IS_WINDOWS:
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                    if self.cb_start_win.isChecked():
                        script_path = os.path.abspath(sys.argv[0])
                        python_exe = sys.executable
                        if "pythonw.exe" not in python_exe.lower():
                            pw = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
                            python_exe = pw if os.path.exists(pw) else pw
                        cmd = f'"{python_exe}" "{script_path}" --startup-delay'
                        winreg.SetValueEx(key, "HytaleServerManager", 0, winreg.REG_SZ, cmd)
                    else:
                        try:
                            winreg.DeleteValue(key, "HytaleServerManager")
                        except OSError:
                            pass
                    winreg.CloseKey(key)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to set registry key: {e}")

        def _refresh_uptime(self):
            """Refresh uptime, status, and CPU/RAM labels (called every second)."""
            running = (
                self.core.server_process is not None
                and self.core.server_process.poll() is None
            )
            # Update status label (color only on Running/Stopped, not "Status:")
            if running:
                self.lbl_status.setText("Status: <span style='color:#43a047'>Running</span>")
                self.btn_start.setEnabled(False)
                self.btn_stop.setEnabled(True)
            else:
                self.lbl_status.setText("Status: <span style='color:#e53935'>Stopped</span>")
                self.btn_start.setEnabled(True)
                self.btn_stop.setEnabled(False)
            # Update uptime
            s = self.core.get_uptime_str()
            uptime_text = f"Uptime: {s}"
            if self.lbl_uptime.text() != uptime_text:
                self.lbl_uptime.setText(uptime_text)
            # Update CPU/RAM (interval=0.1 required - cpu_percent returns 0 with interval=None)
            if HAS_PSUTIL:
                try:
                    cpu_load = psutil.cpu_percent(interval=0.1)
                    ram_load = psutil.virtual_memory().percent
                    self.lbl_cpu.setText(f"CPU: {cpu_load}%")
                    self.lbl_ram.setText(f"RAM: {ram_load}%")
                except Exception:
                    pass
            else:
                self.lbl_cpu.setText("CPU: N/A")
                self.lbl_ram.setText("RAM: N/A")

        def update_stats(self, status):
            """Callback from core; updates buttons/status. CPU/RAM handled by _refresh_uptime."""
            def apply():
                state = status.get("state", "Unknown")
                if not HAS_PSUTIL:
                    self.lbl_cpu.setText("CPU: N/A")
                    self.lbl_ram.setText("RAM: N/A")
                if state == "Stopped":
                    self.btn_start.setEnabled(True)
                    self.btn_stop.setEnabled(False)
                    self.lbl_status.setText("Status: <span style='color:#e53935'>Stopped</span>")
                    self.lbl_uptime.setText("Uptime: 00:00:00")
                elif state == "Running":
                    self.btn_start.setEnabled(False)
                    self.btn_stop.setEnabled(True)
                    self.lbl_status.setText("Status: <span style='color:#43a047'>Running</span>")
                    self.lbl_uptime.setText(f"Uptime: {status.get('uptime', '00:00:00')}")
            QTimer.singleShot(0, apply)

        def log_queue_wrapper(self, msg, tag=None):
            timestamp = datetime.datetime.now().strftime("[%H:%M:%S]")
            self.log_queue.put((f"{timestamp} {msg}\n", tag))
            if self.cb_logging.isChecked():
                clean_msg = re.sub(r"\x1b\[[0-9;]*m", "", f"{timestamp} {msg}\n")
                try:
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(clean_msg)
                except OSError:
                    pass

        def drain_log_queue(self):
            while not self.log_queue.empty():
                try:
                    msg, tag = self.log_queue.get_nowait()
                except queue.Empty:
                    break
                self.insert_colored(msg, tag)
                scrollbar = self.console.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())

        def insert_colored(self, text, tag):
            cursor = self.console.textCursor()
            cursor.movePosition(QTextCursor.End)
            parts = re.split(r"(\x1b\[[0-9;]*m)", text)
            current_color = "#ff5555" if tag == "stderr" else None
            for part in parts:
                if part.startswith("\x1b["):
                    raw = part.strip()
                    code = raw[2:-1].split(";")[-1] if raw.endswith("m") and len(raw) > 2 else ""
                    if code == "0":
                        current_color = None
                    elif code in ("31", "91"):
                        current_color = "#ff5555"
                    elif code in ("32", "92"):
                        current_color = "#55ff55" if self.is_dark else "#00aa00"
                    elif code in ("33", "93"):
                        current_color = "#ffff55" if self.is_dark else "#aaaa00"
                    elif code in ("36", "96"):
                        current_color = "#55ffff" if self.is_dark else "#00aaaa"
                else:
                    if part:
                        fmt = QTextCharFormat()
                        if current_color:
                            fmt.setForeground(QColor(current_color))
                        cursor.setCharFormat(fmt)
                        cursor.insertText(part)

        def ask_file(self, prompt):
            path, _ = QFileDialog.getOpenFileName(self, prompt, "", "Zip Files (*.zip);;All Files (*)")
            return path or ""

        def apply_theme(self):
            silver = "#6b6b6b"
            from urllib.parse import quote
            def icon_url(p):
                path = os.path.abspath(p).replace("\\", "/")
                return "file:///" + quote(path, safe="/:")
            check_w = icon_url(CHECK_WHITE_PNG)
            check_b = icon_url(CHECK_BLACK_PNG)
            if self.is_dark:
                # Cursor-IDE palette; control box = footer grey; buttons = discord input grey
                bg, fg = "#0b0b0b", "#e0e0e0"
                input_bg, input_fg = "#222222", "#e0e0e0"
                console_bg, console_fg = "#0c0c0c", "#d4d4d4"
                muted, cb_hover = "#9d9d9d", "#3fb950"
                footer_bg = "#181818"
                btn_bg, btn_hover_bg, btn_border = input_bg, "#2a2a2a", "#333333"
                cb_checked = f"background: {cb_hover}; border-color: {cb_hover}; image: url({check_w!r});"
                input_border = f"border: 1px solid {btn_border};"
                group_border = f"border: 1px solid {btn_border}; border-radius: 4px; background: {footer_bg};"
                frame_border = f"border: 1px solid {btn_border}; border-radius: 4px; background: {input_bg};"
                btn_border_style = f"border: 1px solid {btn_border}; border-radius: 4px;"
            else:
                # Light: 90s retro Windows; checkbox checked = dark grey + white check (visible)
                bg, fg = "#d4d0c8", "#000000"
                input_bg, input_fg = "#ffffff", "#000000"
                console_bg, console_fg = "#0c0c0c", "#d4d4d4"
                muted, cb_hover = "#404040", "#000080"
                btn_bg, btn_hover_bg, btn_border = "#d4d0c8", "#d4d0c8", "#808080"
                cb_checked = f"background: #404040; border: 1px solid #808080; border-radius: 0; image: url({check_w!r});"
                input_border = "border: 2px inset; border-color: #808080 #c0c0c0 #c0c0c0 #808080;"
                group_border = "border: 2px outset; border-color: #ffffff #808080 #808080 #ffffff; border-radius: 0;"
                frame_border = "border: 2px inset; border-color: #808080 #c0c0c0 #c0c0c0 #808080; border-radius: 0;"
                btn_border_style = "border: 2px outset; border-color: #ffffff #808080 #808080 #ffffff; border-radius: 0;"
                footer_bg = bg
            p = self.palette()
            p.setColor(QPalette.Window, QColor(bg))
            p.setColor(QPalette.WindowText, QColor(fg))
            p.setColor(QPalette.Base, QColor(input_bg))
            p.setColor(QPalette.Text, QColor(fg))
            p.setColor(QPalette.Button, QColor(bg))
            p.setColor(QPalette.ButtonText, QColor(fg))
            self.setPalette(p)
            qss = f"""
                QMainWindow, QWidget {{ background: {bg}; }}
                #footerBar, #cmdBar, #controlsGroup {{ background: {footer_bg}; }}
                #footerBar QPushButton {{ font-size: 10px; padding: 2px 6px; min-height: 20px; }}
                QCheckBox {{ color: {fg}; padding: 2px; background-color: transparent; }}
                QCheckBox:hover {{ color: {fg}; }}
                QCheckBox::indicator {{ background: {input_bg}; border: 1px solid {btn_border}; border-radius: 2px; width: 13px; height: 13px; }}
                QCheckBox::indicator:hover {{ border: 1px solid {cb_hover}; background: {btn_hover_bg}; }}
                QCheckBox::indicator:checked {{ {cb_checked} }}
                QLineEdit {{ background: {input_bg}; color: {input_fg}; padding: 2px; {input_border} }}
                QGroupBox {{ color: {fg}; font-weight: bold; padding-top: 6px; margin-top: 4px; {group_border} }}
                QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; color: {fg}; }}
                QFrame {{ color: {fg}; {frame_border} padding: 4px; }}
                QLabel {{ color: {fg}; border: none; background: transparent; }}
                #statsContainer {{ background: {footer_bg}; border: none; }}
                #mutedLbl {{ font-size: 10px; color: {muted}; margin: 0; padding: 0; background: transparent; }}
                #statusLbl {{ border: none; background: transparent; padding: 2px 0; min-height: 1.2em; }}
                QPushButton {{ {btn_border_style} padding: 4px 8px; color: {fg}; background: {btn_bg}; }}
                QPushButton:hover {{ border: 2px solid {cb_hover}; background: {btn_hover_bg}; }}
                QPushButton:pressed {{ border: 2px solid {cb_hover}; background: {cb_hover}; color: white; }}
                QPushButton:disabled {{ opacity: 0.5; }}
                #btnStart {{ font-weight: bold; color: #3fb950; }}
                #btnStart:hover {{ border: 2px solid #3fb950; background: #1a3d1a; }}
                #btnStart:pressed {{ border: 2px solid #3fb950; background: #3fb950; color: #0b0b0b; }}
                #btnStart:disabled {{ color: #666; }}
                #btnStop {{ font-weight: bold; color: #D13438; }}
                #btnStop:hover {{ border: 2px solid #ff6b6b; background: #4d1a1a; }}
                #btnStop:pressed {{ border: 2px solid #ff6b6b; background: #D13438; color: white; }}
                #btnStop:disabled {{ color: #666; }}
            """
            self.setStyleSheet(qss)
            self.console.setStyleSheet(f"QPlainTextEdit {{ background: {console_bg}; color: {console_fg}; font-family: Consolas; font-size: 11px; }}")
            self._refresh_uptime()  # Re-apply status color after theme change

        def toggle_theme(self):
            self.is_dark = not self.is_dark
            self.config["dark_mode"] = self.is_dark
            self.apply_theme()
            self.save()

        def closeEvent(self, event):
            if self.core.server_process and self.core.server_process.poll() is None:
                reply = QMessageBox.question(
                    self, "Quit",
                    "Server is running. Do you want to stop it and quit?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.core.stop_server()
                    event.accept()
                    QApplication.quit()
                else:
                    event.ignore()
            else:
                event.accept()
                QApplication.quit()

    _debug("GUI", "creating QApplication...")
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    _debug("GUI", f"QApplication OK | style=Fusion")
    app.setStyle("Fusion")
    ensure_check_icons()
    _debug("GUI", "creating HytaleGUI window...")
    window = HytaleGUI()
    _debug("GUI", "calling window.show()...")
    window.show()
    _debug("GUI", "entering app.exec() event loop")
    sys.exit(app.exec())

def print_help():
    """Prints the help message."""
    abs_config_path = os.path.abspath(CONFIG_FILE)
    print(f"Hytale Server Manager v{__version__}")
    print("=" * 60)
    print("Usage: python hsm.pyw [options]")
    print("\nCommand Line Options:")
    print("  -nogui             : Run in console-only mode (headless). Useful for servers.")
    print("  -install-service   : (Linux) Installs systemd service for background operation.")
    print("  -enable-autostart  : (Linux) Adds to desktop auto-start.")
    print("  -help, --help      : Show this help message.")
    print("\nDescription:")
    print("  Manages the Hytale Dedicated Server life-cycle.")
    print("  Features: Auto-Updates, Crash Detection, Auto-Restarts, World Backups, Discord Webhooks.")
    
    print("\nConfiguration File:")
    print(f"  Location: {abs_config_path}")
    print("\n  The configuration is a JSON file with the following options:")
    print("  - last_server_version : Tracks the installed server version.")
    print("  - dark_mode           : (GUI) Enable dark theme. [true/false]")
    print("  - enable_logging      : Write logs to hsm.log. [true/false]")
    print("  - check_updates       : Check for updates on startup. [true/false]")
    print("  - auto_start          : Automatically start the server when this script runs. [true/false]")
    print("  - enable_backups      : Zip the world folder before starting. [true/false]")
    print("  - max_backups         : Number of backups to keep. [Integer]")
    print("  - enable_discord      : Enable Discord Webhook notifications. [true/false]")
    print("  - discord_webhook     : The Discord Webhook URL. [String]")
    print("  - enable_auto_restart : Restart server automatically on crash/stop. [true/false]")
    print("  - enable_schedule     : Enable scheduled periodic restarts. [true/false]")
    print("  - restart_interval    : Hours between scheduled restarts. [Float]")
    print("  - server_memory       : Java Heap Size (e.g., '4G', '8G'). [String]")
    print("=" * 60)
    sys.exit(0)

# --- Main ---
def main():
    """Main entry point."""
    _debug("MAIN", "entering main()")
    # Always set the working directory to the script's own folder.
    # This is critical when launched via the Windows registry (Start with Windows),
    # which defaults the CWD to C:\Windows\System32.
    os.chdir(BASE_DIR)
    _debug("MAIN", f"chdir to BASE_DIR={BASE_DIR}")

    if "--startup-delay" in sys.argv:
        _debug("MAIN", "startup-delay: sleeping 30s")
        time.sleep(30)
        sys.argv.remove("--startup-delay")
        _debug("MAIN", "startup-delay done")

    # Cleanup temporary update files
    if os.path.exists("updater_installer.py"):
        try: os.remove("updater_installer.py")
        except OSError:
            pass
        
    for f in ["version.py.new", "hsm.py.new", "hsm.pyw.new"]:
         if os.path.exists(f):
             try: os.remove(f)
             except OSError:
                 pass

    if "-help" in sys.argv or "--help" in sys.argv:
        _debug("MAIN", "print_help and exit")
        print_help()

    if "-install-service" in sys.argv:
        _debug("MAIN", "install-service")
        install_service()
        sys.exit(0)

    if "-enable-autostart" in sys.argv:
        _debug("MAIN", "enable-autostart")
        enable_autostart()
        sys.exit(0)

    ok, err = _acquire_single_instance_lock()
    if not ok:
        _debug("MAIN", f"single-instance block: {err}")
        if IS_PYTHONW and IS_WINDOWS:
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, err, "Hytale Server Manager", 0x10)
            except Exception:
                pass
        else:
            print(err)
        sys.exit(1)

    if "-nogui" in sys.argv:
        _debug("MAIN", "starting console mode")
        run_console_mode()
    else:
        _debug("MAIN", "starting GUI mode")
        missing = _check_gui_requirements()
        while missing:
            _debug("MAIN", f"Missing GUI deps: {missing}")
            if not _show_missing_deps_and_offer_install(missing):
                _debug("MAIN", "User cancelled or install failed")
                sys.exit(1)
            missing = _check_gui_requirements()
        try:
            run_gui_mode()
            _debug("MAIN", "run_gui_mode returned (app exited normally)")
        except ImportError as e:
            _debug("GUI", f"ImportError: {e}")
            if "PySide6" in str(e) or "PySide" in str(e):
                _debug("GUI", "Fix: pip install PySide6  (or: pip install -r requirements.txt)")
            if not IS_PYTHONW:
                traceback.print_exc()
                print("GUI libraries not found (PySide6 required).")
                print("Install with: pip install PySide6")
                print("Falling back to console mode...")
                run_console_mode()
            else:
                sys.exit(1)
        except Exception as e:
            _debug("GUI", f"Exception: {e}\n{traceback.format_exc()}")
            if not IS_PYTHONW:
                traceback.print_exc()
                input("GUI Start Failed! Press Enter to exit...")
            else:
                sys.exit(1)

if __name__ == "__main__":
    try:
        _debug("MAIN", "__main__ block entered, calling main()")
        main()
        _debug("MAIN", "main() returned normally")
    except Exception as e:
        _debug("CRASH", f"Unhandled: {e}\n{traceback.format_exc()}")
        if not IS_PYTHONW:
            try:
                traceback.print_exc()
                input("Critical Crash! Press Enter to exit...")
            except Exception:
                pass
        sys.exit(1)
