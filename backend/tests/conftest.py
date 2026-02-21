# pytest fixture = Spring의 @BeforeEach + @Autowired 합친 것
# 테스트마다 깨끗한 환경 만들어줌

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.redis import init_redis, close_redis

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_redis():
    """테스트 시작할 때 Redis 초기화"""
    await init_redis()
    yield
    try:
        await close_redis()
    except RuntimeError:
        pass  # Event loop 종료 에러 무시

@pytest_asyncio.fixture
async def client():
    """
    테스트용 HTTP 클라이언트
    Spring의 MockMvc 랑 동일한 역할
    실제 서버 안 띄워도 API 테스트 가능
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client