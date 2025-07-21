from fastapi import Request, HTTPException, APIRouter
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from dotenv import load_dotenv
from contextlib import closing
from datetime import datetime, timedelta, timezone
from logging import Logger
from typing import Any, Mapping, Optional
from sqlite3 import Cursor
from strategies.yape_email_strategy import YapeEmailStrategy
from strategies.interbank_email_strategy import InterbankEmailStrategy
import logging, os, sqlite3


router: APIRouter = APIRouter()
load_dotenv()
WEB_CLIENT_ID: str | None = os.environ.get("WEB_CLIENT_ID")

logger: Logger = logging.getLogger(__name__)


@router.post("/gmail/read-messages")
async def read_messages(request: Request) -> list[dict]:

    try:
        body: dict = await request.json()
        token: Optional[str] = body.get("id_token")

        info: Mapping[str, Any] = id_token.verify_oauth2_token(
            token, GoogleRequest(), WEB_CLIENT_ID
        )
        sub: Any | None = info.get("sub")

        return read_gmail_messages(sub)

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token")
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def read_gmail_messages(sub) -> list[dict]:
    def get_tokens_by_sub(sub) -> tuple[str, str] | tuple[None, None]:
        with closing(sqlite3.connect("db.sqlite")) as conn:
            cursor: Cursor = conn.cursor()
            cursor.execute(
                "SELECT access_token, refresh_token FROM users WHERE sub = ?", (sub,)
            )
            result: Any = cursor.fetchone()
            if result:
                return result[0], result[1]
            else:
                return None, None

    access_token, refresh_token = get_tokens_by_sub(sub)

    # Zona horario de Perú (UTC-5)
    peru_offset: timedelta = timedelta(hours=-5)
    tz: timezone = timezone(peru_offset)

    # Medianoche en UTC-5
    midnight_yesterday: datetime = datetime.now(tz).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=1)
    midnight_today: datetime = datetime.now(tz).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}

    # Hora actual en UTC-5
    now: datetime = datetime.now(tz)

    # Convertir a timestamps
    after: int = int(midnight_today.timestamp())
    before: int = int(now.timestamp())

    strategies = [InterbankEmailStrategy(), YapeEmailStrategy()]

    movements_list: list[dict] = []
    
    for strategy in strategies:
        dicts_to_add = strategy.process_messages(after, before, refresh_token, sub, headers)
        if not dicts_to_add:
            continue
        for dicts in dicts_to_add:
            movements_list.append(dicts)

    return movements_list