#!/usr/bin/env python3
"""
Update Metadelphi to the latest release version.

This is invoked as a subprocess by service_runner.py so that the running
service_runner.py file is not replaced underneath itself during the update.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def run_command(cmd: list[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=check, text=True, capture_output=True)


def require_python() -> None:
    version = sys.version_info
    if version < (3, 10):
        fail(f"Python 3.10 or newer is required. Found {version.major}.{version.minor}.")


def check_internet() -> bool:
    try:
        urllib.request.urlopen("https://github.com", timeout=10)
        return True
    except urllib.error.URLError:
        return False


def resolve_latest_version(repo: str, token: Optional[str] = None) -> str:
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(api_url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            fail("GitHub API rate limit exceeded.\nSet GITHUB_TOKEN or specify a version with --version.")
        fail(f"Failed to resolve latest release: {e}")
    except urllib.error.URLError as e:
        fail(f"Failed to reach GitHub: {e}")

    match = re.search(r'"tag_name"\s*:\s*"v?([^"]+)"', data)
    if not match:
        fail("Could not determine the latest release version.\nCheck your internet connection or specify a version.")

    return match.group(1)


def download_file(url: str, output: Path) -> None:
    print(f"Downloading {url}...")
    try:
        urllib.request.urlretrieve(url, output)
    except urllib.error.URLError as e:
        fail(f"Download failed: {e}")

    if output.stat().st_size == 0:
        fail("Downloaded archive is empty.")


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
    print("Stopping Metadelphi service...")
    runner = app_dir / "service_runner.py"
    try:
        subprocess.run([sys.executable, str(runner), "stop"], check=False, capture_output=True)
    except Exception:
        pass


def service_running(app_dir: Path) -> bool:
    runner = app_dir / "service_runner.py"
    try:
        result = subprocess.run(
            [sys.executable, str(runner), "status", "--quiet"],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


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


def restore_user_data(app_dir: Path, backup_dir: Path) -> None:
    files_to_restore = ["config.toml", "conversations.db"]
    for name in files_to_restore:
        src = backup_dir / name
        if src.exists():
            print(f"Restoring {name}...")
            shutil.copy2(src, app_dir / name)

    state_backup = backup_dir / "state"
    if state_backup.exists():
        print("Restoring runtime state...")
        state_dir = get_state_dir()
        state_dir.mkdir(parents=True, exist_ok=True)
        for item in state_backup.iterdir():
            dest = state_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)


def install_dependencies(app_dir: Path) -> None:
    venv_python = app_dir / ".venv" / "bin" / "python"
    if sys.platform == "win32":
        venv_python = app_dir / ".venv" / "Scripts" / "python.exe"

    if not venv_python.exists():
        fail("Virtual environment not found after update.")

    print("Upgrading pip...")
    run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], cwd=app_dir)

    print("Installing dependencies...")
    run_command([str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"], cwd=app_dir)


def build_frontend(app_dir: Path) -> None:
    if not (app_dir / "frontend-react" / "package.json").exists():
        return

    npm = shutil.which("npm")
    if not npm:
        print("npm not found; skipping frontend build.")
        return

    print("Building React frontend...")
    try:
        run_command([npm, "install"], cwd=app_dir / "frontend-react")
        run_command([npm, "run", "build"], cwd=app_dir / "frontend-react")
    except subprocess.CalledProcessError as e:
        print(f"Warning: frontend build failed: {e.stderr}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Metadelphi to the latest release.")
    parser.add_argument("--install-dir", required=True, type=Path, help="Path to the Metadelphi installation directory.")
    parser.add_argument("--version", default=None, help="Install a specific version instead of the latest.")
    args = parser.parse_args()

    app_dir: Path = args.install_dir.resolve()
    if not app_dir.is_dir():
        fail(f"Install directory does not exist: {app_dir}")

    require_python()

    if not check_internet():
        fail("Internet connectivity check failed.")

    was_running = service_running(app_dir)
    saved_port: Optional[int] = None
    if was_running:
        # Remember the port the service was using so we can restart on the same port.
        state_dir = get_state_dir()
        port_file = state_dir / "service.port"
        if port_file.exists():
            try:
                saved_port = int(port_file.read_text(encoding="utf-8").strip())
            except ValueError:
                pass
        stop_service(app_dir)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = Path.home() / f"Metadelphi-backup-{timestamp}"
    backup_user_data(app_dir, backup_dir)

    repo_owner = os.environ.get("METADELPHI_REPO_OWNER", "TanyuSylvain")
    repo_name = os.environ.get("METADELPHI_REPO_NAME", "metadelphi")
    repo = f"{repo_owner}/{repo_name}"

    version: str = args.version or resolve_latest_version(repo, token=os.environ.get("GITHUB_TOKEN"))
    version_tag = f"v{version.lstrip('v')}"
    archive_name = f"Metadelphi-Installer-{version_tag}.tar.gz"

    custom_url = os.environ.get("METADELPHI_DOWNLOAD_URL")
    if custom_url:
        download_url = custom_url
    else:
        download_url = f"https://github.com/{repo}/releases/download/{version_tag}/{archive_name}"

    tmp_dir = Path(tempfile.mkdtemp(prefix="metadelphi-update-"))
    try:
        archive_path = tmp_dir / archive_name
        download_file(download_url, archive_path)

        print("Extracting archive...")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(tmp_dir)

        extracted = tmp_dir / f"Metadelphi-Installer-{version_tag}"
        if not extracted.is_dir():
            fail(f"Expected extracted directory not found: {extracted}")

        # Atomic replacement: move current dir to .bak, move extracted to app_dir.
        backup_app_dir = Path(f"{app_dir}.bak")
        if backup_app_dir.exists():
            shutil.rmtree(backup_app_dir)

        print("Replacing installation...")
        shutil.move(str(app_dir), str(backup_app_dir))
        try:
            shutil.move(str(extracted), str(app_dir))
        except Exception:
            # Rollback on failure.
            if app_dir.exists():
                shutil.rmtree(app_dir)
            shutil.move(str(backup_app_dir), str(app_dir))
            raise

        # Preserve the virtual environment to avoid re-downloading packages.
        venv_source = backup_app_dir / ".venv"
        venv_target = app_dir / ".venv"
        if venv_source.exists() and not venv_target.exists():
            print("Preserving virtual environment...")
            shutil.copytree(venv_source, venv_target, symlinks=True)

        restore_user_data(app_dir, backup_dir)

        # Restore service.port so restart uses the same port.
        if saved_port is not None:
            state_dir = get_state_dir()
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "service.port").write_text(f"{saved_port}\n", encoding="utf-8")

        install_dependencies(app_dir)
        build_frontend(app_dir)

        # Clean up successful backup.
        shutil.rmtree(backup_app_dir)
        shutil.rmtree(backup_dir)

        print(f"Metadelphi updated to {version_tag}.")

        if was_running:
            print("Restarting Metadelphi service...")
            runner = app_dir / "service_runner.py"
            port_arg = ["--port", str(saved_port)] if saved_port else []
            result = subprocess.run([sys.executable, str(runner), "start"] + port_arg)
            return result.returncode

        return 0

    except Exception as e:
        print(f"Update failed: {e}", file=sys.stderr)
        # Rollback if possible.
        backup_app_dir = Path(f"{app_dir}.bak")
        if backup_app_dir.exists() and app_dir.exists():
            shutil.rmtree(app_dir)
            shutil.move(str(backup_app_dir), str(app_dir))
        return 1

    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    sys.exit(main())
