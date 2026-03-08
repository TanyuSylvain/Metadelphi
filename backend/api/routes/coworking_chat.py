"""
Coworking Agent Chat endpoints.

Provides endpoints for the coworking agent with tool calling,
file operations, and code execution within a workspace.
"""

import os
import sys
import json
import uuid
import asyncio
import subprocess
import shutil
import locale
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse

from backend.api.schemas import CoworkingChatRequest, OpenFileRequest
from backend.core.coworking_agent import CoworkingAgent
from backend.tools.workspace_tools import resolve_in_workspace
from backend.storage import get_storage
from backend.config import settings

router = APIRouter(prefix="/chat/coworking", tags=["coworking-chat"])

# Shared storage instance
_storage = get_storage(
    backend=settings.storage_backend,
    database_url=settings.database_url
)

# Agent pool (keyed by model_id:thinking)
_agents: dict[str, CoworkingAgent] = {}


def _decode_subprocess_output(raw: bytes) -> str:
    """Decode subprocess output using the active locale before falling back to UTF-8."""
    encoding = locale.getpreferredencoding(False) or "utf-8"
    return raw.decode(encoding, errors="replace").strip()


def _select_workspace_windows_tkinter() -> str | None:
    """Use the native Windows folder picker via tkinter."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()

    try:
        path = filedialog.askdirectory(
            parent=root,
            title="Select workspace folder",
            mustexist=False,
        )
    finally:
        root.destroy()

    path = (path or "").strip()
    if path and os.path.isdir(path):
        return path
    return None


async def _select_workspace_windows_powershell() -> str | None:
    """Fallback Windows folder picker using PowerShell."""
    ps_script = """
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "Select workspace folder"
    $dialog.ShowNewFolderButton = $true
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        Write-Output $dialog.SelectedPath
    }
    """
    proc = await asyncio.create_subprocess_exec(
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-STA",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        ps_script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

    if proc.returncode != 0:
        return None

    path = _decode_subprocess_output(stdout)
    if path and os.path.isdir(path):
        return path
    return None


def get_agent(model_id: str, thinking: bool = False) -> CoworkingAgent:
    """
    Get or create a coworking agent instance.

    Args:
        model_id: Model ID to use
        thinking: Enable thinking mode

    Returns:
        CoworkingAgent instance
    """
    global _agents, _storage

    agent_key = f"{model_id}:{thinking}"
    if agent_key not in _agents:
        _agents[agent_key] = CoworkingAgent(
            model_id=model_id,
            storage=_storage,
            thinking=thinking
        )
    return _agents[agent_key]


@router.post("/stream")
async def coworking_chat_stream(request: CoworkingChatRequest):
    """
    Send a message and get a streaming coworking agent response.

    Streams Server-Sent Events (SSE) with event types:
    - plan: Workflow plan steps
    - thinking_chunk: Agent reasoning token
    - tool_start: Before tool execution
    - tool_result: After tool execution
    - file_created: File written to workspace
    - response_chunk: Final response token
    - done: Workflow complete
    - error: Error occurred
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Validate workspace path
    workspace_path = os.path.abspath(request.workspace_path)
    if not os.path.isabs(request.workspace_path):
        raise HTTPException(status_code=400, detail="workspace_path must be an absolute path")

    # Resolve model
    model_id = request.model or settings.default_model
    conversation_id = request.conversation_id or str(uuid.uuid4())

    async def generate():
        """Generate SSE stream of coworking agent events."""
        try:
            agent = get_agent(
                model_id=model_id,
                thinking=request.thinking or False
            )

            async for event in agent.stream(
                question=request.message,
                conversation_id=conversation_id,
                workspace_path=workspace_path,
                max_iterations=request.max_iterations,
                web_search=request.web_search or False
            ):
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        except Exception as e:
            error_event = json.dumps({
                "type": "error",
                "error": str(e)
            }, ensure_ascii=False)
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-ID": conversation_id,
            "X-Model-ID": model_id
        }
    )


@router.get("/files")
async def download_file(
    workspace_path: str = Query(..., description="Workspace directory path"),
    file_path: str = Query(..., description="File path relative to workspace")
):
    """
    Download a file from the workspace.

    Args:
        workspace_path: Absolute path to workspace directory
        file_path: Relative path to file within workspace
    """
    try:
        resolved = resolve_in_workspace(workspace_path, file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not os.path.exists(resolved):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if not os.path.isfile(resolved):
        raise HTTPException(status_code=400, detail=f"Not a file: {file_path}")

    return FileResponse(
        path=resolved,
        filename=os.path.basename(resolved)
    )


@router.get("/select-workspace")
async def select_workspace():
    """
    Open a native folder picker dialog and return the selected path.
    Supports macOS (osascript), Linux (zenity/kdialog), and Windows (PowerShell).

    Returns:
        {"path": "/selected/path"} on success, {"path": null} if cancelled
    """
    try:
        if sys.platform == "darwin":
            # macOS: use osascript
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e",
                'POSIX path of (choose folder with prompt "Select workspace folder")',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            if proc.returncode != 0:
                return {"path": None}

            path = stdout.decode().strip().rstrip("/")
            if path and os.path.isdir(path):
                return {"path": path}
            return {"path": None}

        elif sys.platform.startswith("linux"):
            # Linux: try zenity first (GNOME), then kdialog (KDE)
            if shutil.which("zenity"):
                proc = await asyncio.create_subprocess_exec(
                    "zenity", "--file-selection", "--directory",
                    "--title=Select workspace folder",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

                if proc.returncode != 0:
                    return {"path": None}

                path = stdout.decode().strip()
                if path and os.path.isdir(path):
                    return {"path": path}
                return {"path": None}

            elif shutil.which("kdialog"):
                proc = await asyncio.create_subprocess_exec(
                    "kdialog", "--getexistingdirectory",
                    "--title", "Select workspace folder",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

                if proc.returncode != 0:
                    return {"path": None}

                path = stdout.decode().strip()
                if path and os.path.isdir(path):
                    return {"path": path}
                return {"path": None}

            else:
                # No dialog tool available
                raise HTTPException(
                    status_code=501,
                    detail="No folder picker available. Install 'zenity' (GNOME) or 'kdialog' (KDE)."
                )

        elif sys.platform == "win32":
            # Windows: prefer tkinter since it stays inside the running Python app.
            try:
                path = await asyncio.to_thread(_select_workspace_windows_tkinter)
            except Exception:
                path = await _select_workspace_windows_powershell()

            if path:
                return {"path": path}
            return {"path": None}

        else:
            # Unsupported platform
            raise HTTPException(
                status_code=501,
                detail=f"Unsupported platform: {sys.platform}"
            )

    except asyncio.TimeoutError:
        return {"path": None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/open-file")
async def open_file(request: OpenFileRequest):
    """
    Open a file from the workspace with the default macOS application.

    Args:
        request: OpenFileRequest with workspace_path and file_path
    """
    try:
        resolved = resolve_in_workspace(request.workspace_path, request.file_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not os.path.exists(resolved):
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")

    if not os.path.isfile(resolved):
        raise HTTPException(status_code=400, detail=f"Not a file: {request.file_path}")

    try:
        subprocess.Popen(["open", resolved])
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open file: {str(e)}")
