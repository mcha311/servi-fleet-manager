"""
FastAPI ROS2 Bridge Router
==========================
- /ws/ros2        : ROS2 Bridge Node와 WebSocket 연결
- /api/robots/{id}/navigate : REST로 nav goal 전송
- /api/robots/{id}/cancel   : 목표 취소
- /api/robots/{id}/cmd_vel  : 속도 제어

기존 robot_simulator.py 대신 실제 ROS2 데이터 사용
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from pydantic import BaseModel, Field

from app.core.connection_manager import ConnectionManager
from app.core.robot_state import RobotStateStore

logger = logging.getLogger(__name__)

router = APIRouter()

# ── 의존성: 싱글톤 매니저 ──────────────────────────────────
# main.py에서 app.state에 주입됨
def get_connection_manager() -> ConnectionManager:
    from app.main import app
    return app.state.connection_manager

def get_robot_store() -> RobotStateStore:
    from app.main import app
    return app.state.robot_store


# ─────────────────────────────────────────────────────────────
# WebSocket: ROS2 Bridge 전용 엔드포인트
# ─────────────────────────────────────────────────────────────

@router.websocket("/ws/ros2")
async def ros2_bridge_ws(
    websocket: WebSocket,
    manager: ConnectionManager = Depends(get_connection_manager),
    store: RobotStateStore = Depends(get_robot_store),
):
    """
    ROS2 Bridge Node와의 전용 WebSocket 채널
    - 수신: robot_pose / robot_status / robot_battery / robot_scan
    - 송신: navigate_to / cmd_vel / cancel_goal
    """
    await websocket.accept()
    bridge_id = "ros2_bridge"
    logger.info("🔌 ROS2 Bridge connected")

    try:
        async for raw_data in websocket.iter_text():
            try:
                message = json.loads(raw_data)
                msg_type = message.get("type")
                robot_id = message.get("robot_id")
                data = message.get("data", {})

                # ── 브릿지 연결 등록 ────────────────────────
                if msg_type == "bridge_connected":
                    robot_ids = message.get("robot_ids", [])
                    store.register_ros2_robots(robot_ids)
                    logger.info(f"✅ ROS2 robots registered: {robot_ids}")
                    await websocket.send_json({
                        "type": "bridge_ack",
                        "status": "connected",
                        "registered_robots": robot_ids,
                    })

                # ── 로봇 포즈 업데이트 ──────────────────────
                elif msg_type == "robot_pose" and robot_id:
                    store.update_pose(robot_id, data)
                    # 프론트엔드에 브로드캐스트
                    await manager.broadcast({
                        "type": "robot_update",
                        "robot_id": robot_id,
                        "pose": data,
                        "source": "ros2",
                    })

                # ── 로봇 상태 업데이트 ──────────────────────
                elif msg_type == "robot_status" and robot_id:
                    store.update_status(robot_id, data)
                    await manager.broadcast({
                        "type": "status_update",
                        "robot_id": robot_id,
                        "status": data,
                        "source": "ros2",
                    })

                # ── 배터리 업데이트 ─────────────────────────
                elif msg_type == "robot_battery" and robot_id:
                    store.update_battery(robot_id, data)
                    # 배터리 알림 체크
                    if data.get("percentage", 100) < 20:
                        await manager.broadcast({
                            "type": "alert",
                            "severity": "warning",
                            "robot_id": robot_id,
                            "message": f"배터리 부족: {data['percentage']}%",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                # ── 라이다 스캔 ─────────────────────────────
                elif msg_type == "robot_scan" and robot_id:
                    store.update_scan(robot_id, data)
                    await manager.broadcast({
                        "type": "scan_update",
                        "robot_id": robot_id,
                        "scan": data,
                        "source": "ros2",
                    })

                else:
                    logger.debug(f"Unhandled message type: {msg_type}")

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from bridge: {raw_data[:100]}")
            except Exception as e:
                logger.error(f"Bridge message error: {e}", exc_info=True)

    except WebSocketDisconnect:
        logger.warning("🔌 ROS2 Bridge disconnected")
        store.mark_bridge_disconnected()
        await manager.broadcast({
            "type": "bridge_disconnected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


# ─────────────────────────────────────────────────────────────
# REST API: 프론트엔드 → FastAPI → ROS2
# ─────────────────────────────────────────────────────────────

class NavGoalRequest(BaseModel):
    x: float = Field(..., description="목표 X 좌표 (m)")
    y: float = Field(..., description="목표 Y 좌표 (m)")
    yaw: float = Field(0.0, description="목표 방향각 (도)")
    task_id: Optional[str] = Field(None, description="연결된 작업 ID")


class CmdVelRequest(BaseModel):
    linear_x: float = Field(0.0, ge=-2.0, le=2.0, description="전진/후진 (m/s)")
    linear_y: float = Field(0.0, ge=-2.0, le=2.0, description="좌/우 (m/s)")
    angular_z: float = Field(0.0, ge=-3.14, le=3.14, description="회전 (rad/s)")


@router.post("/api/robots/{robot_id}/navigate")
async def navigate_to(
    robot_id: str,
    goal: NavGoalRequest,
    manager: ConnectionManager = Depends(get_connection_manager),
    store: RobotStateStore = Depends(get_robot_store),
):
    """로봇에게 목표 지점 이동 명령"""
    if not store.is_robot_available(robot_id):
        raise HTTPException(status_code=404, detail=f"Robot {robot_id} not available")

    command = {
        "type": "navigate_to",
        "robot_id": robot_id,
        "data": {
            "x": goal.x,
            "y": goal.y,
            "yaw": goal.yaw,
            "task_id": goal.task_id,
        },
    }

    # ROS2 Bridge로 전달
    sent = await manager.send_to_bridge(command)
    if not sent:
        raise HTTPException(status_code=503, detail="ROS2 Bridge not connected")

    # 상태 업데이트
    store.update_status(robot_id, {"state": "navigating", "goal": {"x": goal.x, "y": goal.y}})

    return {
        "status": "sent",
        "robot_id": robot_id,
        "goal": goal.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/api/robots/{robot_id}/cancel")
async def cancel_goal(
    robot_id: str,
    manager: ConnectionManager = Depends(get_connection_manager),
    store: RobotStateStore = Depends(get_robot_store),
):
    """로봇 현재 목표 취소"""
    command = {
        "type": "cancel_goal",
        "robot_id": robot_id,
        "data": {},
    }
    sent = await manager.send_to_bridge(command)
    store.update_status(robot_id, {"state": "idle"})

    return {"status": "cancelled", "robot_id": robot_id, "sent_to_bridge": sent}


@router.post("/api/robots/{robot_id}/cmd_vel")
async def send_cmd_vel(
    robot_id: str,
    cmd: CmdVelRequest,
    manager: ConnectionManager = Depends(get_connection_manager),
):
    """수동 속도 제어 (텔레오퍼레이션)"""
    command = {
        "type": "cmd_vel",
        "robot_id": robot_id,
        "data": cmd.model_dump(),
    }
    sent = await manager.send_to_bridge(command)
    return {"status": "sent", "robot_id": robot_id, "cmd": cmd.model_dump(), "sent_to_bridge": sent}


@router.get("/api/robots/{robot_id}/state")
async def get_robot_state(
    robot_id: str,
    store: RobotStateStore = Depends(get_robot_store),
):
    """로봇 현재 상태 조회 (ROS2 실시간 데이터)"""
    state = store.get_robot_state(robot_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")
    return state


@router.get("/api/bridge/status")
async def bridge_status(store: RobotStateStore = Depends(get_robot_store)):
    """ROS2 Bridge 연결 상태 확인"""
    return {
        "bridge_connected": store.is_bridge_connected(),
        "registered_robots": store.get_registered_robots(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }