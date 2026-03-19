"""
Run control endpoints for cancelling active streaming requests.
"""

from fastapi import APIRouter

from backend.api.run_control import run_manager

router = APIRouter(prefix="/chat/runs", tags=["run-control"])


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: str):
    """Cancel an active streaming run if it is still running."""
    return await run_manager.cancel_run(run_id)
