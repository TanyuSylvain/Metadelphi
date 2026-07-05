#!/usr/bin/env python3
"""
Uninstall Metadelphi from this machine.

This is invoked as a subprocess by service_runner.py so that the running
service_runner.py file and install directory can be removed safely.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


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


def stop_service(app_dir: Path) -> None:
    runner = app_dir / "service_runner.py"
    if runner.exists():
        print("Stopping Metadelphi service...")
        try:
            subprocess.run([sys.executable, str(runner), "stop"], check=False, capture_output=True)
        except Exception:
            pass


def remove_service_files() -> None:
    if sys.platform == "darwin":
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        for name in ["com.metadelphi.service.plist", "com.unifyllm.service.plist"]:
            path = plist_dir / name
            if path.exists():
                print(f"Removing {path}...")
                path.unlink()
    elif sys.platform == "linux":
        unit_dir = Path.home() / ".config" / "systemd" / "user"
        for name in ["metadelphi.service", "unifyllm.service"]:
            path = unit_dir / name
            if path.exists():
                print(f"Removing {path}...")
                path.unlink()
        try:
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False, capture_output=True)
        except Exception:
            pass


def remove_global_wrapper() -> None:
    bin_dir = Path.home() / ".local" / "bin"
    wrapper = bin_dir / "metadelphi"
    if wrapper.exists() or wrapper.is_symlink():
        print(f"Removing global CLI wrapper: {wrapper}")
        wrapper.unlink()


def remove_desktop_launchers() -> None:
    if sys.platform == "darwin":
        app = Path.home() / "Applications" / "Metadelphi.app"
        legacy_app = Path.home() / "Applications" / "UnifyLLM.app"
        for path in [app, legacy_app]:
            if path.exists():
                print(f"Removing {path}...")
                shutil.rmtree(path)
    elif sys.platform == "linux":
        desktop = Path.home() / "Desktop"
        apps = Path.home() / ".local" / "share" / "applications"
        for directory in [desktop, apps]:
            for name in ["Metadelphi.desktop", "UnifyLLM.desktop"]:
                path = directory / name
                if path.exists():
                    print(f"Removing {path}...")
                    path.unlink()


def prompt_user_data() -> bool:
    while True:
        response = input("Keep conversation history and settings? [Y/n]: ").strip().lower()
        if response in ("", "y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'.")


def backup_user_data(app_dir: Path, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    files_to_backup = ["config.toml", "conversations.db"]
    for name in files_to_backup:
        src = app_dir / name
        if src.exists():
            print(f"Backing up {name}...")
            shutil.copy2(src, backup_dir / name)

    state_dir = get_state_dir()
    if state_dir.exists():
        print("Backing up runtime state...")
        shutil.copytree(state_dir, backup_dir / "state", dirs_exist_ok=True)

    print(f"User data backed up to: {backup_dir}")


def remove_directory(path: Path) -> None:
    if path.exists():
        print(f"Removing {path}...")
        shutil.rmtree(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Uninstall Metadelphi from this machine.")
    parser.add_argument("--install-dir", required=True, type=Path, help="Path to the Metadelphi installation directory.")
    parser.add_argument("--remove-data", action="store_true", help="Delete user data without prompting.")
    parser.add_argument("--keep-data", action="store_true", help="Back up user data without prompting.")
    args = parser.parse_args()

    app_dir: Path = args.install_dir.resolve()
    if not app_dir.is_dir():
        fail(f"Install directory does not exist: {app_dir}")

    print("======================================")
    print("  Metadelphi Uninstaller")
    print("======================================")
    print()

    stop_service(app_dir)
    remove_service_files()
    remove_global_wrapper()
    remove_desktop_launchers()

    keep_data: Optional[bool] = None
    if args.remove_data:
        keep_data = False
    elif args.keep_data:
        keep_data = True
    else:
        keep_data = prompt_user_data()

    if keep_data:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = Path.home() / f"Metadelphi-backup-{timestamp}"
        backup_user_data(app_dir, backup_dir)

    remove_directory(get_state_dir())
    remove_directory(app_dir)

    print()
    print("======================================")
    print("  Uninstallation Complete")
    print("======================================")
    print()
    print("Metadelphi has been removed from your machine.")
    if keep_data:
        print("Your settings and conversations were backed up before removal.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
