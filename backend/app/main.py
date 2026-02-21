from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import init_redis, close_redis
from app import models
from app.api.routes import websocket, robots, tasks, replay
from app.ros2_bridge.robot_simulator import simulate_robot_movement
from app.services.alert_service import check_and_send_alerts
from app.api.routes.replay import record_frame

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()

    # 백그라운드 태스크 3개 동시 실행
    tasks_bg = asyncio.gather(
        simulate_robot_movement(),  # 로봇 시뮬레이션
        check_and_send_alerts(),    # 알림 감지
        record_frame(),             # 녹화
    )
    print("🚀 Servi Fleet Manager 시작!")
    yield
    tasks_bg.cancel()
    await close_redis()

app = FastAPI(
    title=settings.APP_NAME,
    description="Robot Fleet Management System for Bear Robotics",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(websocket.router)
app.include_router(robots.router)
app.include_router(tasks.router)
app.include_router(replay.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}