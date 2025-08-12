from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from config import Settings

DATABASE_URL = Settings.database_url
if not DATABASE_URL:
    raise RuntimeError("No se configuró la variable de entorno para DATABASE_URL")

# Corrigiendo la DATABASE_URL proporcionada por Fly.io por una que pueda ser usada por SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")
if "sslmode=" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("sslmode=", "ssl=")

echo_value = Settings.sqlalchemy_echo

engine = create_async_engine(DATABASE_URL, echo=echo_value)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
