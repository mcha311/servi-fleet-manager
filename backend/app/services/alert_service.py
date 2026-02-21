# Spring의 @Service + ApplicationEventPublisher 느낌
# 백그라운드에서 계속 돌면서 이상 감지하면 WebSocket으로 알림

import asyncio
from datetime import datetime
from app.ros2_bridge.robot_simulator import get_all_robots
from app.services.websocket_manager import ws_manager
from app.core.config import settings

# 이미 알림 보낸 것 중복 방지
sent_alerts: set = set()

async def check_and_send_alerts():
    """
    1초마다 로봇 상태 체크
    - 배터리 20% 미만 → 알림
    - 에러 상태 → 알림
    - 배터리 회복되면 알림 초기화
    """
    while True:
        robots = get_all_robots()

        for robot in robots:
            robot_id = robot["id"]
            battery = robot["battery"]
            status = robot["status"]

            # 배터리 부족 알림
            alert_key = f"battery:{robot_id}"
            if battery < settings.BATTERY_ALERT_THRESHOLD:
                if alert_key not in sent_alerts:
                    sent_alerts.add(alert_key)
                    await ws_manager.broadcast({
                        "type": "alert",
                        "level": "warning",
                        "robot_id": robot_id,
                        "robot_name": robot["name"],
                        "message": f"{robot['name']} 배터리 부족! ({battery:.1f}%)",
                        "timestamp": datetime.utcnow().isoformat()
                    })

            # 배터리 회복되면 알림 초기화
            elif battery > settings.BATTERY_ALERT_THRESHOLD + 10:
                sent_alerts.discard(alert_key)

            # 에러 상태 알림
            error_key = f"error:{robot_id}"
            if status == "error":
                if error_key not in sent_alerts:
                    sent_alerts.add(error_key)
                    await ws_manager.broadcast({
                        "type": "alert",
                        "level": "error",
                        "robot_id": robot_id,
                        "robot_name": robot["name"],
                        "message": f"{robot['name']} 오류 발생!",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            else:
                sent_alerts.discard(error_key)

        await asyncio.sleep(1)