# redis.asyncio = Spring의 RedisTemplate (비동기 버전)
# 실시간 로봇 상태를 Redis에 저장/조회할 때 사용

import json
import redis.asyncio as aioredis
from app.core.config import settings

redis_client: aioredis.Redis = None

async def get_redis() -> aioredis.Redis:
    return redis_client

async def init_redis():
    global redis_client
    redis_client = await aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True  # bytes 말고 string으로 자동 변환
    )

async def close_redis():
    if redis_client:
        await redis_client.aclose()

# 로봇 상태 Redis에 저장
# Spring의 redisTemplate.opsForValue().set("robot:id", value) 와 동일
async def set_robot_state(robot_id: str, state: dict):
    await redis_client.set(
        f"robot:{robot_id}",
        json.dumps(state),
        ex=60  # 60초 TTL (로봇이 60초 이상 응답 없으면 자동 삭제)
    )

# 로봇 상태 Redis에서 조회
async def get_robot_state(robot_id: str) -> dict | None:
    data = await redis_client.get(f"robot:{robot_id}")
    return json.loads(data) if data else None

# 전체 로봇 상태 조회
async def get_all_robot_states() -> list[dict]:
    keys = await redis_client.keys("robot:*")
    if not keys:
        return []
    values = await redis_client.mget(keys)
    return [json.loads(v) for v in values if v]