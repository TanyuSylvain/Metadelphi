"""
Run lifecycle management for cancellable streaming requests.
"""

import asyncio
import contextvars
import os
import signal
import uuid
from dataclasses import dataclass
from typing import Dict, Optional


class RunCancelledError(Exception):
    """Raised when a streaming run is cancelled by the user or disconnect."""


@dataclass(frozen=True)
class ManagedProcess:
    """Track a subprocess tied to a streaming run."""
    process: asyncio.subprocess.Process
    use_process_group: bool = False


_current_run_context: contextvars.ContextVar[Optional["RunContext"]] = contextvars.ContextVar(
    "current_run_context",
    default=None,
)


class RunContext:
    """Mutable cancellation state for a single active run."""

    def __init__(self, run_id: str, mode: str, conversation_id: Optional[str] = None):
        self.run_id = run_id
        self.mode = mode
        self.conversation_id = conversation_id
        self.cancel_event = asyncio.Event()
        self.finished_event = asyncio.Event()
        self._tasks: set[asyncio.Task] = set()
        self._processes: set[ManagedProcess] = set()
        self._lock = asyncio.Lock()

    @property
    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise RunCancelledError("Run cancelled")

    async def register_task(self, task: Optional[asyncio.Task] = None) -> None:
        task = task or asyncio.current_task()
        if task is None:
            return
        async with self._lock:
            self._tasks.add(task)
            cancelled = self.cancel_event.is_set()
        if cancelled:
            task.cancel()

    async def unregister_task(self, task: Optional[asyncio.Task] = None) -> None:
        task = task or asyncio.current_task()
        if task is None:
            return
        async with self._lock:
            self._tasks.discard(task)

    async def register_process(
        self,
        process: asyncio.subprocess.Process,
        use_process_group: bool = False,
    ) -> None:
        managed = ManagedProcess(process=process, use_process_group=use_process_group)
        async with self._lock:
            self._processes.add(managed)
            cancelled = self.cancel_event.is_set()
        if cancelled:
            await self._terminate_process(managed)

    async def unregister_process(self, process: asyncio.subprocess.Process) -> None:
        async with self._lock:
            self._processes = {
                managed for managed in self._processes if managed.process is not process
            }

    async def cancel(self) -> bool:
        async with self._lock:
            if self.cancel_event.is_set():
                return False
            self.cancel_event.set()
            tasks = list(self._tasks)
            processes = list(self._processes)

        current_task = asyncio.current_task()
        for task in tasks:
            if task is not current_task and not task.done():
                task.cancel()

        await asyncio.gather(
            *(self._terminate_process(process) for process in processes),
            return_exceptions=True,
        )
        return True

    def mark_finished(self) -> None:
        """Mark the run as fully cleaned up and no longer active."""
        self.finished_event.set()

    async def wait_finished(self) -> None:
        """Wait until the stream route has completed all cancellation cleanup."""
        await self.finished_event.wait()

    async def _terminate_process(self, managed: ManagedProcess) -> None:
        process = managed.process
        if process.returncode is not None:
            return

        try:
            if managed.use_process_group and process.pid:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    return
            else:
                process.terminate()
        except ProcessLookupError:
            return

        try:
            await asyncio.wait_for(process.wait(), timeout=2.0)
            return
        except asyncio.TimeoutError:
            pass

        try:
            if managed.use_process_group and process.pid:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    return
            else:
                process.kill()
            await asyncio.wait_for(process.wait(), timeout=2.0)
        except (ProcessLookupError, asyncio.TimeoutError):
            return


class RunManager:
    """Registry for active streaming runs."""

    def __init__(self):
        self._runs: Dict[str, RunContext] = {}
        self._lock = asyncio.Lock()

    async def create_run(self, mode: str, conversation_id: Optional[str] = None) -> RunContext:
        run_id = str(uuid.uuid4())
        context = RunContext(run_id=run_id, mode=mode, conversation_id=conversation_id)
        async with self._lock:
            self._runs[run_id] = context
        return context

    async def get_run(self, run_id: str) -> Optional[RunContext]:
        async with self._lock:
            return self._runs.get(run_id)

    async def cancel_run(self, run_id: str) -> dict:
        context = await self.get_run(run_id)
        if not context:
            return {
                "success": True,
                "run_id": run_id,
                "already_finished": True,
                "already_cancelled": False,
            }

        cancelled_now = await context.cancel()
        await context.wait_finished()
        return {
            "success": True,
            "run_id": run_id,
            "already_finished": False,
            "already_cancelled": not cancelled_now,
        }

    async def finish_run(self, run_id: str) -> None:
        async with self._lock:
            self._runs.pop(run_id, None)


class use_run_context:
    """Context manager that exposes the current run to nested tool helpers."""

    def __init__(self, run_context: Optional[RunContext]):
        self.run_context = run_context
        self._token = None

    async def __aenter__(self):
        self._token = _current_run_context.set(self.run_context)
        return self.run_context

    async def __aexit__(self, exc_type, exc, tb):
        _current_run_context.reset(self._token)
        return False


def get_current_run_context() -> Optional[RunContext]:
    """Return the active run context for the current task, if any."""
    return _current_run_context.get()


run_manager = RunManager()
