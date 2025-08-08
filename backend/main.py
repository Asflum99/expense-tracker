from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from auth_google import auth_status, oauth2callback, auth_check_status
from gmail import read_messages
from database import engine, Base
from contextlib import asynccontextmanager
import locale, logging, sys, os, platform


os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/app.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


def setup_locale():
    system = platform.system().lower()

    if system == "windows":
        locales_to_try = ["Spanish_Peru", "Spanish_Peru.1252"]
    else:
        locales_to_try = ["es_PE.UTF-8", "es_PE"]

    for loc in locales_to_try:
        try:
            locale.setlocale(locale.LC_TIME, loc)
            return
        except locale.Error:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        setup_locale()
    except Exception:
        logger.critical("Error estableciendo el locale")
        raise

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        logger.critical("Error durante el ciclo de vida de la aplicación")
        raise

    yield


app = FastAPI(lifespan=lifespan)
app.include_router(auth_check_status.router)
app.include_router(auth_status.router)
app.include_router(oauth2callback.router)
app.include_router(read_messages.router)