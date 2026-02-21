# 실제 ROS2 없어도 개발할 수 있게 가상 로봇 시뮬레이터
# Spring Boot 테스트에서 @MockBean 쓰는 것과 비슷한 개념

import asyncio
import random
import math
from datetime import datetime
from app.core.redis import set_robot_state, redis_client
from app.services.websocket_manager import ws_manager

# 초기 로봇 5대 설정 (Bear Robotics Servi 로봇들)
INITIAL_ROBOTS = [
    {"id": "robot-001", "name": "Servi-1", "x": 1.0, "y": 1.0},
    {"id": "robot-002", "name": "Servi-2", "x": 3.0, "y": 1.0},
    {"id": "robot-003", "name": "Servi-3", "x": 5.0, "y": 1.0},
    {"id": "robot-004", "name": "Servi-4", "x": 1.0, "y": 3.0},
    {"id": "robot-005", "name": "Servi-5", "x": 3.0, "y": 3.0},
]

# 로봇 내부 상태 (메모리에 유지)
robot_states = {
    r["id"]: {
        "id": r["id"],
        "name": r["name"],
        "status": "idle",
        "battery": random.uniform(60, 100),
        "x": r["x"],
        "y": r["y"],
        "current_task_id": None,
        "updated_at": datetime.utcnow().isoformat()
    }
    for r in INITIAL_ROBOTS
}

async def simulate_robot_movement():
    """
    로봇 움직임 시뮬레이션
    - idle: 제자리에서 미세하게 흔들림
    - working: 목적지로 이동
    - charging: 충전 중 (배터리 증가)
    - error: 움직임 없음
    """
    while True:
        for robot_id, state in robot_states.items():
            # 배터리 자연 감소 (working 상태일 때 더 빠르게)
            if state["status"] == "working":
                state["battery"] = max(0, state["battery"] - random.uniform(0.1, 0.3))
                # 목적지 방향으로 이동
                if "target_x" in state:
                    dx = state["target_x"] - state["x"]
                    dy = state["target_y"] - state["y"]
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist > 0.1:
                        speed = 0.05
                        state["x"] += (dx / dist) * speed
                        state["y"] += (dy / dist) * speed
                    else:
                        # 목적지 도착
                        state["status"] = "idle"
                        state["current_task_id"] = None

            elif state["status"] == "charging":
                state["battery"] = min(100, state["battery"] + random.uniform(0.5, 1.0))
                if state["battery"] >= 100:
                    state["status"] = "idle"

            elif state["status"] == "idle":
                state["battery"] = max(0, state["battery"] - random.uniform(0.01, 0.05))
                # 배터리 부족하면 자동 충전
                if state["battery"] < 20:
                    state["status"] = "charging"

            state["updated_at"] = datetime.utcnow().isoformat()

            # Redis에 최신 상태 저장
            await set_robot_state(robot_id, state)

        # WebSocket으로 브로드캐스트
        await ws_manager.broadcast({
            "type": "robot_states",
            "data": list(robot_states.values())
        })

        await asyncio.sleep(1)  # 1초마다 업데이트

async def assign_task_to_robot(robot_id: str, task_id: str, target_x: float, target_y: float):
    """특정 로봇에 작업 배정"""
    if robot_id in robot_states:
        robot_states[robot_id]["status"] = "working"
        robot_states[robot_id]["current_task_id"] = task_id
        robot_states[robot_id]["target_x"] = target_x
        robot_states[robot_id]["target_y"] = target_y
        await set_robot_state(robot_id, robot_states[robot_id])

def get_all_robots() -> list[dict]:
    """현재 모든 로봇 상태 반환"""
    return list(robot_states.values())

def get_available_robots() -> list[dict]:
    """idle 상태 로봇만 반환 (작업 배정 가능한 로봇)"""
    return [r for r in robot_states.values() if r["status"] == "idle"]