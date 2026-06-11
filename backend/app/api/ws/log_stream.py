"""WebSocket log streaming endpoint."""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.task.log_bus import log_bus

router = APIRouter()


@router.websocket("/ws/log/{run_id}")
async def ws_log(websocket: WebSocket, run_id: int):
    """WebSocket endpoint for real-time log streaming for a specific run."""
    await log_bus.subscribe(run_id, websocket)
    try:
        while True:
            # Keep connection alive, receive any control messages
            data = await websocket.receive_text()
            # Client can send ping/pong or other messages
    except WebSocketDisconnect:
        log_bus.unsubscribe(run_id, websocket)


@router.websocket("/ws/logs")
async def ws_logs_global(websocket: WebSocket):
    """WebSocket endpoint for global real-time log streaming."""
    await log_bus.subscribe_global(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        log_bus.unsubscribe_global(websocket)
