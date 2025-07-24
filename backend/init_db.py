import asyncio
from backend.database import engine, Base
from backend.models import Users, Beneficiaries, OAuthSession

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)   # ⚠️ cuidado, borra todo
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init())