from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import init_redis, close_redis
from app import models
from app.api.routes import websocket, robots, tasks, replay
from app.api.ros2_router import router as ros2_router
from app.core.robot_simulator import simulate_robot_movement
from app.core.robot_state import RobotStateStore
from app.core.connection_manager import ConnectionManager
from app.services.alert_service import check_and_send_alerts
from app.api.routes.replay import record_frame
from prometheus_fastapi_instrumentator import Instrumentator

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.connection_manager = ConnectionManager()
    app.state.robot_store = RobotStateStore()
    Instrumentator().instrument(app).expose(app)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()

    tasks_bg = asyncio.gather(
        simulate_robot_movement(),
        check_and_send_alerts(),
        record_frame(),
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(websocket.router)
app.include_router(robots.router)
app.include_router(tasks.router)
app.include_router(replay.router)
app.include_router(ros2_router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}