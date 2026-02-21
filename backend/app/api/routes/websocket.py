# @MessageMapping 이랑 동일한 역할
# 클라이언트가 ws://localhost:8000/ws/robots 로 연결하면 실시간 데이터 수신

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import ws_manager
from app.core.redis import get_all_robot_states

router = APIRouter()

@router.websocket("/ws/robots")
async def robot_websocket(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # 1초마다 Redis에서 전체 로봇 상태 가져와서 클라이언트에 전송
            states = await get_all_robot_states()
            await websocket.send_json({
                "type": "robot_states",
                "data": states
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)