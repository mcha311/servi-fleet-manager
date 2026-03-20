"""
Connection Manager
==================
- 프론트엔드 WebSocket 클라이언트 관리
- ROS2 Bridge WebSocket 참조 유지
- 메시지 브로드캐스트
"""

import logging
from typing import Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # 프론트엔드 연결들
        self.frontend_connections: list[WebSocket] = []
        # ROS2 Bridge 연결 (1개)
        self._bridge_ws: Optional[WebSocket] = None

    # ─── 프론트엔드 ───────────────────────────────────────────

    async def connect_frontend(self, ws: WebSocket):
        await ws.accept()
        self.frontend_connections.append(ws)
        logger.info(f"Frontend connected. Total: {len(self.frontend_connections)}")

    def disconnect_frontend(self, ws: WebSocket):
        if ws in self.frontend_connections:
            self.frontend_connections.remove(ws)
        logger.info(f"Frontend disconnected. Total: {len(self.frontend_connections)}")

    async def broadcast(self, message: dict):
        """모든 프론트엔드에 브로드캐스트"""
        disconnected = []
        for ws in self.frontend_connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect_frontend(ws)

    # ─── ROS2 Bridge ─────────────────────────────────────────

    def set_bridge(self, ws: WebSocket):
        self._bridge_ws = ws
        logger.info("ROS2 Bridge WebSocket registered")

    def unset_bridge(self):
        self._bridge_ws = None

    def is_bridge_connected(self) -> bool:
        return self._bridge_ws is not None

    async def send_to_bridge(self, message: dict) -> bool:
        """ROS2 Bridge로 커맨드 전송"""
        if not self._bridge_ws:
            logger.warning("No ROS2 Bridge connected - cannot send command")
            return False
        try:
            await self._bridge_ws.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send to bridge: {e}")
            self.unset_bridge()
            return False