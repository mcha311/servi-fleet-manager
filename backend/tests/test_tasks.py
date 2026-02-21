import pytest

@pytest.mark.asyncio
async def test_create_task_success(client):
    """작업 생성 + 로봇 자동 배정 테스트"""
    response = await client.post("/api/tasks", json={
        "table_number": "A1",
        "destination_x": 2.0,
        "destination_y": 2.0
    })
    assert response.status_code == 200

    data = response.json()
    assert "task_id" in data
    assert "assigned_robot" in data       # 로봇이 배정됐는지
    assert data["table_number"] == "A1"
    assert data["status"] == "in_progress"


@pytest.mark.asyncio
async def test_task_assigns_nearest_robot():
    """
    가장 가까운 로봇에 배정되는지 테스트 (로직 직접 테스트)
    """
    from app.api.routes.tasks import find_nearest_robot
    
    robots = [
        {"id": "robot-001", "name": "Servi-1", "x": 1.0, "y": 1.0},
        {"id": "robot-002", "name": "Servi-2", "x": 5.0, "y": 5.0},
    ]
    
    nearest = find_nearest_robot(robots, 1.5, 1.5)
    assert nearest["name"] == "Servi-1"  # (1,1)이 (1.5,1.5)에 더 가까움

@pytest.mark.asyncio
async def test_get_task_status(client):
    """작업 현황 조회 테스트"""
    response = await client.get("/api/tasks/status")
    assert response.status_code == 200

    data = response.json()
    assert "total_robots" in data
    assert data["total_robots"] == 5
    assert "working" in data
    assert "idle" in data