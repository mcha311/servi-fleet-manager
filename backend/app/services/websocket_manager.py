# WebSocket 연결된 클라이언트들 관리
# Spring의 SimpMessagingTemplate.convertAndSend() 와 동일한 역할

import json
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        # 연결된 클라이언트 목록
        # Spring의 WebSocketSession 목록이랑 동일
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ 클라이언트 연결됨. 현재 연결 수: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"❌ 클라이언트 해제됨. 현재 연결 수: {len(self.active_connections)}")

    # 모든 연결된 클라이언트에게 브로드캐스트
    # Spring의 simpMessagingTemplate.convertAndSend("/topic/robots", data) 와 동일
    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        data = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                # 끊긴 연결 무시
                pass

# 싱글톤으로 사용 (Spring의 @Bean 싱글톤이랑 동일)
ws_manager = WebSocketManager()