#!/usr/bin/env python3
"""
Supervise the Metadelphi backend for background service usage.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

# tomllib is stdlib only on Python 3.11+; fall back to tomli for 3.10.
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


APP_DIR = Path(__file__).resolve().parent


def get_state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "Metadelphi"
        return Path.home() / "AppData" / "Local" / "Metadelphi"

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Metadelphi"

    base = os.environ.get("XDG_STATE_HOME")
    if base:
        return Path(base) / "metadelphi"
    return Path.home() / ".local" / "state" / "metadelphi"


STATE_DIR = get_state_dir()
LOG_DIR = STATE_DIR / "logs"
PID_FILE = STATE_DIR / "service.pid"
CHILDREN_FILE = STATE_DIR / "children.json"
PORT_FILE = STATE_DIR / "service.port"
SUPERVISOR_LOG = LOG_DIR / "service.log"
BACKEND_LOG = LOG_DIR / "backend.log"


def ensure_runtime_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    ensure_runtime_dirs()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    try:
        with SUPERVISOR_LOG.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass

    if sys.stdout and not getattr(sys.stdout, "closed", True):
        try:
            print(line, flush=True)
        except OSError:
            pass


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def read_pid() -> Optional[int]:
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError, OSError):
        return None


def process_exists(pid: int) -> bool:
    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def write_pid_file() -> None:
    ensure_runtime_dirs()
    PID_FILE.write_text(f"{os.getpid()}\n", encoding="utf-8")


def write_children_file(backend_pid: int) -> None:
    ensure_runtime_dirs()
    payload = {
        "backend_pid": backend_pid,
    }
    CHILDREN_FILE.write_text(json.dumps(payload), encoding="utf-8")


def cleanup_pid_files() -> None:
    for path in (PID_FILE, CHILDREN_FILE):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def read_port_file() -> Optional[int]:
    try:
        return int(PORT_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError, OSError):
        return None


def write_port_file(port: int) -> None:
    ensure_runtime_dirs()
    PORT_FILE.write_text(f"{port}\n", encoding="utf-8")


def read_config_port() -> Optional[int]:
    config_path = APP_DIR / "config.toml"
    try:
        with config_path.open("rb") as handle:
            config = tomllib.load(handle)
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
        return None

    general = config.get("general")
    if not isinstance(general, dict):
        return None

    port = general.get("api_port")
    if port is None:
        return None
    try:
        return int(port)
    except (TypeError, ValueError):
        return None


def resolve_backend_port(cli_port: Optional[int] = None, ignore_saved: bool = False) -> int:
    """Resolve the backend port using CLI arg, env var, saved file, config, then default."""
    if cli_port is not None:
        return cli_port

    env_port = os.environ.get("API_PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            pass

    if not ignore_saved:
        saved_port = read_port_file()
        if saved_port is not None:
            return saved_port

    config_port = read_config_port()
    if config_port is not None:
        return config_port

    return 8000


def validate_port(value: str) -> int:
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"port must be an integer, got '{value}'")
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"port must be between 1 and 65535, got {port}")
    return port


def open_browser(url: str, background: bool = True) -> None:
    """Open a URL in the default browser."""
    try:
        if background:
            # Try to open without blocking. webbrowser.open usually forks on Unix.
            webbrowser.open(url, new=2)
        else:
            webbrowser.open(url, new=2)
    except Exception as e:
        log(f"Failed to open browser: {e}")


def service_running() -> bool:
    pid = read_pid()
    if pid and process_exists(pid):
        return True

    if pid and not process_exists(pid):
        cleanup_pid_files()

    return is_port_open(resolve_backend_port())


def managed_supervisor_running() -> bool:
    pid = read_pid()
    if pid and process_exists(pid):
        return True

    if pid and not process_exists(pid):
        cleanup_pid_files()

    return False


def stop_service() -> int:
    port = resolve_backend_port()
    pid = read_pid()
    if pid and process_exists(pid):
        log(f"Stopping Metadelphi service supervisor (pid {pid})")
        if sys.platform == "win32":
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                print(result.stderr.strip() or "Failed to stop the running service.")
                return 1
        else:
            os.kill(pid, signal.SIGTERM)
            deadline = time.time() + 10
            while time.time() < deadline:
                if not process_exists(pid):
                    break
                time.sleep(0.2)

            if process_exists(pid):
                os.kill(pid, signal.SIGKILL)

        cleanup_pid_files()
        return 0

    if is_port_open(port):
        print(f"Port {port} is in use, but no managed Metadelphi service supervisor was found.")
        return 1

    print("Metadelphi service is not running.")
    cleanup_pid_files()
    return 0


def print_status(quiet: bool = False) -> int:
    port = resolve_backend_port()
    pid = read_pid()
    backend_ready = is_port_open(port)

    if pid and not process_exists(pid):
        cleanup_pid_files()
        pid = None

    if pid and process_exists(pid):
        if not quiet:
            status = "ready" if backend_ready else "starting"
            print(f"Metadelphi service supervisor is running (pid {pid}, port {port}, status: {status}).")
        return 0

    if backend_ready:
        if not quiet:
            print(f"Metadelphi is already reachable on port {port}.")
        return 0

    if not quiet:
        print("Metadelphi service is not running.")
    return 1


def start_service(port: Optional[int], open_browser_flag: bool = True) -> int:
    effective_port = resolve_backend_port(cli_port=port, ignore_saved=True)

    if service_running() and read_port_file() == effective_port:
        print(f"Metadelphi service is already running on port {effective_port}.")
        if open_browser_flag:
            open_browser(f"http://127.0.0.1:{effective_port}/")
        return 0

    # If running on a different port, stop it first so we can switch.
    if managed_supervisor_running():
        stop_service()

    ensure_runtime_dirs()
    write_port_file(effective_port)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["API_PORT"] = str(effective_port)

    kwargs: dict = {
        "cwd": APP_DIR,
        "env": env,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    try:
        proc = subprocess.Popen([sys.executable, str(APP_DIR / "service_runner.py"), "run"], **kwargs)
    except Exception as e:
        print(f"Failed to start Metadelphi service: {e}")
        return 1

    deadline = time.time() + 15
    while time.time() < deadline:
        if service_running():
            pid = read_pid()
            print(f"Metadelphi service started on port {effective_port} (supervisor pid {pid}).")
            if open_browser_flag:
                open_browser(f"http://127.0.0.1:{effective_port}/")
            return 0
        if proc.poll() is not None:
            print(f"Service supervisor exited early with code {proc.returncode}.")
            return 1
        time.sleep(0.5)

    print("Metadelphi service is starting; use 'metadelphi status' to check progress.")
    if open_browser_flag:
        open_browser(f"http://127.0.0.1:{effective_port}/")
    return 0


def restart_service(port: Optional[int], open_browser_flag: bool = True) -> int:
    stop_service()
    return start_service(port=port, open_browser_flag=open_browser_flag)


def show_logs(follow: bool = False, lines: int = 50) -> int:
    if not BACKEND_LOG.exists():
        print(f"No backend log found at {BACKEND_LOG}")
        return 1

    try:
        with BACKEND_LOG.open("r", encoding="utf-8", errors="replace") as handle:
            all_lines = handle.readlines()
            for line in all_lines[-lines:]:
                print(line, end="")
    except OSError as e:
        print(f"Failed to read log: {e}")
        return 1

    if not follow:
        return 0

    try:
        with BACKEND_LOG.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(0, os.SEEK_END)
            while True:
                where = handle.tell()
                line = handle.readline()
                if not line:
                    time.sleep(0.5)
                    handle.seek(where)
                else:
                    print(line, end="")
    except KeyboardInterrupt:
        return 0
    except OSError as e:
        print(f"Failed to follow log: {e}")
        return 1


def terminate_process(proc: subprocess.Popen[bytes], name: str) -> None:
    if proc.poll() is not None:
        return

    log(f"Stopping {name} process (pid {proc.pid})")
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        log(f"Force killing {name} process (pid {proc.pid})")
        proc.kill()
        proc.wait(timeout=5)


def run_supervisor() -> int:
    ensure_runtime_dirs()

    if managed_supervisor_running():
        log("Metadelphi service is already running; skipping duplicate start.")
        return 0

    port = resolve_backend_port(ignore_saved=True)

    backend_ready = is_port_open(port)
    if backend_ready:
        log(f"Port {port} is already in use; not starting a duplicate service.")
        return 0

    write_pid_file()
    backend_log_handle = BACKEND_LOG.open("a", buffering=1)
    backend_proc: Optional[subprocess.Popen[bytes]] = None

    def shutdown(signum: int, _frame: object) -> None:
        log(f"Received signal {signum}; shutting down Metadelphi service.")
        if backend_proc is not None:
            terminate_process(backend_proc, "backend")
        cleanup_pid_files()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("API_PORT", str(port))

    try:
        log("Starting Metadelphi backend service.")
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "backend.main"],
            cwd=APP_DIR,
            env=env,
            stdout=backend_log_handle,
            stderr=subprocess.STDOUT,
        )

        write_children_file(backend_proc.pid)

        deadline = time.time() + 15
        while time.time() < deadline:
            if backend_proc.poll() is not None:
                log(f"Backend exited during startup with code {backend_proc.returncode}.")
                return 1
            if is_port_open(port):
                break
            time.sleep(0.5)

        log("Metadelphi background service is running.")

        while True:
            if backend_proc.poll() is not None:
                log(f"Backend exited with code {backend_proc.returncode}.")
                return backend_proc.returncode or 1

            time.sleep(1)

    finally:
        backend_log_handle.close()
        cleanup_pid_files()


def open_config_port(print_url: bool = False) -> int:
    port = resolve_backend_port()
    url = f"http://127.0.0.1:{port}/"
    if print_url:
        print(url)
        return 0

    print(f"Opening {url} in your browser...")
    open_browser(url)
    return 0


def run_update(version: Optional[str]) -> int:
    """Delegate to installer/update.py as a subprocess so this file isn't replaced mid-run."""
    update_script = APP_DIR / "installer" / "update.py"
    if not update_script.exists():
        print(f"Update script not found: {update_script}")
        return 1

    cmd = [sys.executable, str(update_script), "--install-dir", str(APP_DIR)]
    if version:
        cmd.extend(["--version", version])

    return subprocess.run(cmd).returncode


def run_uninstall(remove_data: bool, keep_data: bool) -> int:
    """Delegate to installer/uninstall.py as a subprocess so this file can be removed."""
    uninstall_script = APP_DIR / "installer" / "uninstall.py"
    if not uninstall_script.exists():
        print(f"Uninstall script not found: {uninstall_script}")
        return 1

    cmd = [sys.executable, str(uninstall_script), "--install-dir", str(APP_DIR)]
    if remove_data:
        cmd.append("--remove-data")
    if keep_data:
        cmd.append("--keep-data")

    return subprocess.run(cmd).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the Metadelphi background service.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run", help="Run the Metadelphi background supervisor.")

    start_parser = subparsers.add_parser("start", help="Start the Metadelphi background service.")
    start_parser.add_argument("-p", "--port", type=validate_port, default=None, help="Port to run the backend on (default: resolved from config or 8000).")
    start_parser.add_argument("--no-browser", action="store_true", help="Do not open the browser after starting.")

    subparsers.add_parser("stop", help="Stop the running service supervisor.")

    restart_parser = subparsers.add_parser("restart", help="Restart the Metadelphi background service.")
    restart_parser.add_argument("-p", "--port", type=validate_port, default=None, help="Port to run the backend on (default: resolved from config or 8000).")
    restart_parser.add_argument("--no-browser", action="store_true", help="Do not open the browser after restarting.")

    status_parser = subparsers.add_parser("status", help="Check service status.")
    status_parser.add_argument("--quiet", action="store_true", help="Suppress status output.")

    logs_parser = subparsers.add_parser("logs", help="Show the backend log.")
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Follow log output.")
    logs_parser.add_argument("-n", "--lines", type=int, default=50, help="Number of lines to show (default: 50).")

    config_parser = subparsers.add_parser("config", help="Open the Metadelphi web UI in your browser.")
    config_parser.add_argument("--print-url", action="store_true", help="Print the URL instead of opening the browser.")

    update_parser = subparsers.add_parser("update", help="Update Metadelphi to the latest release.")
    update_parser.add_argument("--version", default=None, help="Install a specific version instead of the latest.")

    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall Metadelphi from this machine.")
    uninstall_parser.add_argument("--remove-data", action="store_true", help="Delete user data without prompting.")
    uninstall_parser.add_argument("--keep-data", action="store_true", help="Back up user data without prompting.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        return run_supervisor()
    if args.command == "start":
        return start_service(port=args.port, open_browser_flag=not args.no_browser)
    if args.command == "stop":
        return stop_service()
    if args.command == "restart":
        return restart_service(port=args.port, open_browser_flag=not args.no_browser)
    if args.command == "status":
        return print_status(quiet=args.quiet)
    if args.command == "logs":
        return show_logs(follow=args.follow, lines=args.lines)
    if args.command == "config":
        return open_config_port(print_url=args.print_url)
    if args.command == "update":
        return run_update(version=args.version)
    if args.command == "uninstall":
        return run_uninstall(remove_data=args.remove_data, keep_data=args.keep_data)

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
