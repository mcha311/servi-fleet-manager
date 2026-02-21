# Record: 로봇 상태를 타임스탬프와 함께 Redis에 저장
# Replay: 저장된 데이터를 시간순으로 재현

import json
import asyncio
from datetime import datetime
from fastapi import APIRouter
from app.core.redis import redis_client
from app.ros2_bridge.robot_simulator import get_all_robots
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/api/replay", tags=["replay"])

# 현재 녹화 세션 ID
recording_session: str | None = None

@router.post("/start")
async def start_recording():
    """녹화 시작"""
    global recording_session
    recording_session = f"session:{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    return {"session_id": recording_session, "status": "recording"}

@router.post("/stop")
async def stop_recording():
    """녹화 중지"""
    global recording_session
    session_id = recording_session
    recording_session = None
    return {"session_id": session_id, "status": "stopped"}

@router.get("/sessions")
async def get_sessions():
    """저장된 세션 목록 조회"""
    keys = await redis_client.keys("session:*")
    return {"sessions": keys}

@router.get("/{session_id}")
async def replay_session(session_id: str):
    """특정 세션 재현"""
    # Redis에서 해당 세션 데이터 조회
    data = await redis_client.lrange(session_id, 0, -1)
    if not data:
        return {"error": "세션을 찾을 수 없습니다"}

    frames = [json.loads(d) for d in data]

    # WebSocket으로 프레임 순서대로 재현
    async def send_replay():
        for frame in frames:
            await ws_manager.broadcast({
                "type": "replay_frame",
                "data": frame
            })
            await asyncio.sleep(0.1)

    asyncio.create_task(send_replay())
    return {"session_id": session_id, "total_frames": len(frames)}

async def record_frame():
    """1초마다 현재 상태 녹화"""
    while True:
        if recording_session:
            frame = {
                "timestamp": datetime.utcnow().isoformat(),
                "robots": get_all_robots()
            }
            await redis_client.rpush(
                recording_session,
                json.dumps(frame)
            )
            # 최대 3600프레임 (1시간) 유지
            await redis_client.ltrim(recording_session, -3600, -1)
        await asyncio.sleep(1)