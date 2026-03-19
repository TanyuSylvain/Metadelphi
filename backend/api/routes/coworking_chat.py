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
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, FileResponse

from backend.api.schemas import CoworkingChatRequest, OpenFileRequest
from backend.api.run_control import CANCELLATION_MESSAGE, persist_cancellation_notice, run_manager
from backend.core.coworking_agent import (
    CoworkingAgent,
    ensure_coworking_session_state,
)
from backend.core.run_manager import RunCancelledError
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
async def coworking_chat_stream(http_request: Request, request: CoworkingChatRequest):
    """
    Send a message and get a streaming coworking agent response.

    Streams Server-Sent Events (SSE) with event types:
    - plan_ready: Parsed workflow plan
    - round_start: Start of a ReAct round
    - reasoning_chunk: User-facing worklog token for a round
    - tool_start: Before tool execution
    - tool_result: After tool execution
    - round_complete: ReAct round completed
    - file_created: File written to workspace
    - file_deleted: File removed from workspace during the round
    - session_notice: Session-level file tracking notice for the chat window
    - final_start: Final-answer phase begins
    - final_chunk: Final response token
    - done: Workflow complete
    - error: Error occurred
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Validate workspace path
    if not os.path.isabs(request.workspace_path):
        raise HTTPException(status_code=400, detail="workspace_path must be an absolute path")
    workspace_path = os.path.abspath(request.workspace_path)

    # Resolve model
    model_id = request.model or settings.default_model
    conversation_id = request.conversation_id or str(uuid.uuid4())

    run_context = await run_manager.create_run(mode="coworking", conversation_id=conversation_id)

    async def generate():
        """Generate SSE stream of coworking agent events."""
        task = asyncio.current_task()
        if task:
            await run_context.register_task(task)
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
                web_search=request.web_search or False,
                run_context=run_context,
            ):
                if await http_request.is_disconnected():
                    await run_context.cancel()
                    raise RunCancelledError("Client disconnected")
                event_data = json.dumps(event, ensure_ascii=False)
                yield f"data: {event_data}\n\n"

        except asyncio.CancelledError:
            await run_context.cancel()
            await persist_cancellation_notice(_storage, conversation_id)
        except RunCancelledError:
            await persist_cancellation_notice(_storage, conversation_id)
            if not await http_request.is_disconnected():
                event_data = json.dumps({"type": "cancelled", "message": CANCELLATION_MESSAGE}, ensure_ascii=False)
                yield f"data: {event_data}\n\n"
        except Exception as e:
            error_event = json.dumps({
                "type": "error",
                "error": str(e)
            }, ensure_ascii=False)
            yield f"data: {error_event}\n\n"
        finally:
            if task:
                await run_context.unregister_task(task)
            await run_manager.finish_run(run_context.run_id)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-ID": conversation_id,
            "X-Run-ID": run_context.run_id,
            "X-Model-ID": model_id
        }
    )


@router.get("/session-state")
async def get_coworking_session_state(
    conversation_id: str = Query(..., description="Conversation ID"),
    workspace_path: str = Query(..., description="Absolute workspace directory path"),
):
    """Validate and return the coworking file-tracking state for session recovery."""
    if not await _storage.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")

    if not os.path.isabs(workspace_path):
        raise HTTPException(status_code=400, detail="workspace_path must be an absolute path")
    workspace_path = os.path.abspath(workspace_path)

    state = await ensure_coworking_session_state(
        storage=_storage,
        conversation_id=conversation_id,
        workspace_path=workspace_path,
        add_reset_notice_message=True,
    )

    generated_files = []
    for file_path in state["generated_files"]:
        try:
            file_size = os.path.getsize(os.path.join(workspace_path, file_path))
        except Exception:
            file_size = 0
        generated_files.append({"path": file_path, "size": file_size})

    return {
        "generated_files": generated_files,
        "deleted_files": state["deleted_files"],
        "state_reset_due_to_inconsistency": state["did_reset"],
        "reset_notice": state["reset_notice"],
    }


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
