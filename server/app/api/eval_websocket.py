import uuid
import json
import logging
import asyncio
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ws", tags=["websocket"])


class EvalProgressManager:
    """Manages WebSocket connections for evaluation progress updates."""

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, job_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(job_id, set()).add(ws)
        logger.info(f"WebSocket connected for job {job_id}")

    def disconnect(self, job_id: str, ws: WebSocket):
        if job_id in self._connections:
            self._connections[job_id].discard(ws)
            if not self._connections[job_id]:
                del self._connections[job_id]

    async def send_progress(self, job_id: str, data: dict):
        if job_id not in self._connections:
            return
        dead = []
        for ws in self._connections[job_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[job_id].discard(ws)


eval_progress = EvalProgressManager()


@router.websocket("/evaluation/{job_id}")
async def evaluation_ws(websocket: WebSocket, job_id: str):
    await eval_progress.connect(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        eval_progress.disconnect(job_id, websocket)
