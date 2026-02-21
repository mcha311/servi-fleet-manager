import pytest
from app.services.alert_service import check_and_send_alerts, sent_alerts
from app.ros2_bridge.robot_simulator import robot_states

@pytest.mark.asyncio
async def test_low_battery_alert():
    """
    배터리 20% 미만일 때 알림 발생하는지 테스트
    """
    # 테스트용으로 로봇 배터리 강제로 낮추기
    robot_states["robot-001"]["battery"] = 10.0

    alerts_received = []

    # ws_manager.broadcast 를 가짜로 교체 (Spring의 @MockBean 과 동일)
    from app.services import websocket_manager
    original_broadcast = websocket_manager.ws_manager.broadcast

    async def mock_broadcast(message):
        alerts_received.append(message)

    websocket_manager.ws_manager.broadcast = mock_broadcast

    # 알림 한 사이클 실행
    import asyncio
    from app.services.alert_service import check_and_send_alerts
    task = asyncio.create_task(check_and_send_alerts())
    await asyncio.sleep(1.5)
    task.cancel()

    # 배터리 알림이 왔는지 확인
    alert_types = [a.get("type") for a in alerts_received]
    assert "alert" in alert_types

    battery_alerts = [a for a in alerts_received if a.get("type") == "alert"]
    assert any("배터리" in a.get("message", "") for a in battery_alerts)

    # 원래대로 복구
    websocket_manager.ws_manager.broadcast = original_broadcast
    robot_states["robot-001"]["battery"] = 100.0
    sent_alerts.clear()