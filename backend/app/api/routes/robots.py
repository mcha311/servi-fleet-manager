# APIRouter = @RestController
# Depends(get_db) = @Autowired (의존성 주입)

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.robot_simulator import get_all_robots, get_available_robots

router = APIRouter(prefix="/api/robots", tags=["robots"])

# GET /api/robots - 전체 로봇 조회
# Spring의 @GetMapping("/robots") 와 동일
@router.get("")
async def get_robots():
    return get_all_robots()

# GET /api/robots/available - 작업 배정 가능한 로봇만 조회
@router.get("/available")
async def get_available():
    return get_available_robots()