# Spring의 @Test 메서드들이랑 동일
# pytest는 test_ 로 시작하는 함수를 자동으로 테스트로 인식

import pytest

# @pytest.mark.asyncio = 비동기 테스트 표시
# Spring은 기본 동기라 이게 필요 없지만 FastAPI는 비동기라 필요

@pytest.mark.asyncio
async def test_health_check(client):
    """헬스체크 API 테스트"""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_get_robots(client):
    """전체 로봇 조회 테스트"""
    response = await client.get("/api/robots")
    assert response.status_code == 200

    robots = response.json()
    assert len(robots) == 5  # 초기 로봇 5대

    # 각 로봇이 필수 필드를 가지고 있는지 확인
    for robot in robots:
        assert "id" in robot
        assert "name" in robot
        assert "status" in robot
        assert "battery" in robot
        assert 0 <= robot["battery"] <= 100  # 배터리는 0~100

@pytest.mark.asyncio
async def test_get_available_robots(client):
    """가용 로봇 조회 테스트"""
    response = await client.get("/api/robots/available")
    assert response.status_code == 200

    robots = response.json()
    # 가용 로봇은 전부 idle 상태여야 함
    for robot in robots:
        assert robot["status"] == "idle"