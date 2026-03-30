import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import ws_manager

router = APIRouter()

@router.websocket("/ws/robots")
async def robot_websocket(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            try:
                from app.main import app
                store = app.state.robot_store
                states = []
                for robot_id, state in store._store.items():
                    raw_status = state.get("status", {}).get("state", "idle") if state.get("status") else "idle"
                    status_map = {
                        "idle": "idle",
                        "navigating": "working",
                        "charging": "charging",
                        "error": "error",
                        "unknown": "idle",
                    }
                    states.append({
                        "id": robot_id,
                        "name": robot_id,
                        "x": state.get("pose", {}).get("x", 0) if state.get("pose") else 0,
                        "y": state.get("pose", {}).get("y", 0) if state.get("pose") else 0,
                        "status": status_map.get(raw_status, "idle"),
                        "battery": state.get("battery", {}).get("percentage", 100) if state.get("battery") else 100,
                        "current_task_id": None,
                        "updated_at": state.get("last_seen", ""),
                    })
                await websocket.send_json({
                    "type": "robot_states",
                    "data": states
                })
            except WebSocketDisconnect:
                break
            except Exception:
                break
            await asyncio.sleep(0.5)
    finally:
        try:
            ws_manager.disconnect(websocket)
        except Exception:
            pass