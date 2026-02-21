# sqlalchemy = JPA/Hibernate
# create_async_engine = DataSource (DB 연결 풀)
# AsyncSession = EntityManager (실제 쿼리 실행)
# declarative_base = @Entity 붙일 베이스 클래스

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG  # True면 실행되는 SQL 로그 출력 (Spring의 show-sql: true)
)

# Spring의 @Transactional 안에서 쓰는 EntityManager랑 동일
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()  # 모든 @Entity 클래스가 상속할 베이스

# Spring의 @Autowired EntityManager 대신 FastAPI는 의존성 주입으로
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session  # 요청마다 새 세션, 끝나면 자동 close