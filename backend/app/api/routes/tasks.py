# Spring의 @RestController + @Service 합친 느낌
# Pydantic BaseModel = Spring의 @RequestBody DTO

import uuid
import math
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.ros2_bridge.robot_simulator import (
    get_available_robots,
    assign_task_to_robot,
    get_all_robots
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Spring의 @RequestBody DTO 클래스와 동일
class TaskRequest(BaseModel):
    table_number: str      # 테이블 번호 (예: "A1", "B3")
    destination_x: float  # 목적지 x 좌표
    destination_y: float  # 목적지 y 좌표

def find_nearest_robot(robots: list, target_x: float, target_y: float):
    """
    가장 가까운 idle 로봇 찾기 (Greedy 알고리즘)
    거리 = sqrt((x2-x1)² + (y2-y1)²)
    """
    nearest = None
    min_dist = float('inf')

    for robot in robots:
        dist = math.sqrt(
            (robot["x"] - target_x) ** 2 +
            (robot["y"] - target_y) ** 2
        )
        if dist < min_dist:
            min_dist = dist
            nearest = robot

    return nearest

# POST /api/tasks - 새 작업 생성 + 로봇 자동 배정
# Spring의 @PostMapping("/tasks") 와 동일
@router.post("")
async def create_task(request: TaskRequest):
    # 가용 로봇 확인
    available = get_available_robots()
    if not available:
        raise HTTPException(
            status_code=503,
            detail="사용 가능한 로봇이 없습니다"
        )

    # 가장 가까운 로봇 선택
    nearest_robot = find_nearest_robot(
        available,
        request.destination_x,
        request.destination_y
    )

    # 작업 ID 생성 + 로봇에 배정
    task_id = str(uuid.uuid4())
    await assign_task_to_robot(
        robot_id=nearest_robot["id"],
        task_id=task_id,
        target_x=request.destination_x,
        target_y=request.destination_y
    )

    return {
        "task_id": task_id,
        "assigned_robot": nearest_robot["name"],
        "table_number": request.table_number,
        "destination": {"x": request.destination_x, "y": request.destination_y},
        "status": "in_progress"
    }

# GET /api/tasks/status - 전체 작업 현황
@router.get("/status")
async def get_task_status():
    robots = get_all_robots()
    working = [r for r in robots if r["status"] == "working"]
    return {
        "total_robots": len(robots),
        "working": len(working),
        "idle": len([r for r in robots if r["status"] == "idle"]),
        "charging": len([r for r in robots if r["status"] == "charging"]),
        "active_tasks": [
            {"robot": r["name"], "task_id": r["current_task_id"]}
            for r in working
        ]
    }