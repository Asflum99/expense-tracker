import asyncio
from database import engine, Base
from models import Users, Beneficiaries, OAuthSession

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init())