from fastapi import FastAPI
from auth_google import auth_user, auth_status, oauth2callback, auth_check_status
from gmail import read_messages
from expenses import process_expenses
from database import engine, Base
from contextlib import asynccontextmanager
import locale, traceback


def setup_locale():
    locale.setlocale(locale.LC_TIME, "es_PE.UTF-8")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        setup_locale()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        traceback.print_exc()
        raise
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth_check_status.router)
app.include_router(auth_user.router)
app.include_router(auth_status.router)
app.include_router(oauth2callback.router)
app.include_router(read_messages.router)
app.include_router(process_expenses.router)
