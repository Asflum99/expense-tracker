from fastapi import FastAPI
from auth_google import auth_user, auth_status, oauth2callback
from gmail import read_messages
from expenses import process_expenses
from database import engine, Base
from contextlib import asynccontextmanager
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth_user.router)
app.include_router(auth_status.router)
app.include_router(oauth2callback.router)
app.include_router(read_messages.router)
app.include_router(process_expenses.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
