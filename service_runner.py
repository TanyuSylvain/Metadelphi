#!/usr/bin/env python3
"""
Supervise the UnifyLLM backend and frontend for background service usage.
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
from pathlib import Path
from typing import Optional


APP_DIR = Path(__file__).resolve().parent
BACKEND_PORT = 8000
FRONTEND_PORT = 8080


def get_state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "UnifyLLM"
        return Path.home() / "AppData" / "Local" / "UnifyLLM"

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "UnifyLLM"

    base = os.environ.get("XDG_STATE_HOME")
    if base:
        return Path(base) / "unifyllm"
    return Path.home() / ".local" / "state" / "unifyllm"


STATE_DIR = get_state_dir()
LOG_DIR = STATE_DIR / "logs"
PID_FILE = STATE_DIR / "service.pid"
CHILDREN_FILE = STATE_DIR / "children.json"
SUPERVISOR_LOG = LOG_DIR / "service.log"
BACKEND_LOG = LOG_DIR / "backend.log"
FRONTEND_LOG = LOG_DIR / "frontend.log"


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


def write_children_file(backend_pid: int, frontend_pid: int) -> None:
    ensure_runtime_dirs()
    payload = {
        "backend_pid": backend_pid,
        "frontend_pid": frontend_pid,
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


def service_running() -> bool:
    pid = read_pid()
    if pid and process_exists(pid):
        return True

    if pid and not process_exists(pid):
        cleanup_pid_files()

    return is_port_open(BACKEND_PORT) and is_port_open(FRONTEND_PORT)


def managed_supervisor_running() -> bool:
    pid = read_pid()
    if pid and process_exists(pid):
        return True

    if pid and not process_exists(pid):
        cleanup_pid_files()

    return False


def stop_service() -> int:
    pid = read_pid()
    if pid and process_exists(pid):
        log(f"Stopping UnifyLLM service supervisor (pid {pid})")
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

    if is_port_open(BACKEND_PORT) or is_port_open(FRONTEND_PORT):
        print("Ports are in use, but no managed UnifyLLM service supervisor was found.")
        return 1

    print("UnifyLLM service is not running.")
    cleanup_pid_files()
    return 0


def print_status(quiet: bool = False) -> int:
    pid = read_pid()
    backend_ready = is_port_open(BACKEND_PORT)
    frontend_ready = is_port_open(FRONTEND_PORT)

    if pid and not process_exists(pid):
        cleanup_pid_files()
        pid = None

    if pid and process_exists(pid):
        if not quiet:
            status = "ready" if backend_ready and frontend_ready else "starting"
            print(f"UnifyLLM service supervisor is running (pid {pid}, status: {status}).")
        return 0

    if backend_ready and frontend_ready:
        if not quiet:
            print("UnifyLLM is already reachable on ports 8000 and 8080.")
        return 0

    if not quiet:
        print("UnifyLLM service is not running.")
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
        log("UnifyLLM service is already running; skipping duplicate start.")
        return 0

    backend_ready = is_port_open(BACKEND_PORT)
    frontend_ready = is_port_open(FRONTEND_PORT)
    if backend_ready or frontend_ready:
        if backend_ready and frontend_ready:
            log("Ports 8000 and 8080 are already in use; not starting a duplicate service.")
            return 0

        log("Port conflict detected while starting UnifyLLM; one required port is already in use.")
        return 0

    write_pid_file()
    backend_log_handle = BACKEND_LOG.open("a", buffering=1)
    frontend_log_handle = FRONTEND_LOG.open("a", buffering=1)
    backend_proc: Optional[subprocess.Popen[bytes]] = None
    frontend_proc: Optional[subprocess.Popen[bytes]] = None

    def shutdown(signum: int, _frame: object) -> None:
        log(f"Received signal {signum}; shutting down UnifyLLM service.")
        if frontend_proc is not None:
            terminate_process(frontend_proc, "frontend")
        if backend_proc is not None:
            terminate_process(backend_proc, "backend")
        cleanup_pid_files()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    frontend_dir = APP_DIR / "frontend" / "src"

    try:
        log("Starting UnifyLLM backend service.")
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "backend.main"],
            cwd=APP_DIR,
            env=env,
            stdout=backend_log_handle,
            stderr=subprocess.STDOUT,
        )

        log("Starting UnifyLLM frontend service.")
        frontend_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "http.server",
                str(FRONTEND_PORT),
                "--directory",
                str(frontend_dir),
            ],
            cwd=APP_DIR,
            env=env,
            stdout=frontend_log_handle,
            stderr=subprocess.STDOUT,
        )

        write_children_file(backend_proc.pid, frontend_proc.pid)

        deadline = time.time() + 15
        while time.time() < deadline:
            if backend_proc.poll() is not None:
                log(f"Backend exited during startup with code {backend_proc.returncode}.")
                terminate_process(frontend_proc, "frontend")
                return 1
            if frontend_proc.poll() is not None:
                log(f"Frontend exited during startup with code {frontend_proc.returncode}.")
                terminate_process(backend_proc, "backend")
                return 1
            if is_port_open(BACKEND_PORT) and is_port_open(FRONTEND_PORT):
                break
            time.sleep(0.5)

        log("UnifyLLM background service is running.")

        while True:
            if backend_proc.poll() is not None:
                log(f"Backend exited with code {backend_proc.returncode}; stopping frontend.")
                terminate_process(frontend_proc, "frontend")
                return backend_proc.returncode or 1

            if frontend_proc.poll() is not None:
                log(f"Frontend exited with code {frontend_proc.returncode}; stopping backend.")
                terminate_process(backend_proc, "backend")
                return frontend_proc.returncode or 1

            time.sleep(1)

    finally:
        backend_log_handle.close()
        frontend_log_handle.close()
        cleanup_pid_files()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the UnifyLLM background service.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run", help="Run the UnifyLLM background supervisor.")

    status_parser = subparsers.add_parser("status", help="Check service status.")
    status_parser.add_argument("--quiet", action="store_true", help="Suppress status output.")

    subparsers.add_parser("stop", help="Stop the running service supervisor.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        return run_supervisor()
    if args.command == "status":
        return print_status(quiet=args.quiet)
    if args.command == "stop":
        return stop_service()

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
