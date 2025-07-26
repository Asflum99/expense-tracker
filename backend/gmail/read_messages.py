from fastapi import HTTPException, APIRouter, Depends
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from dotenv import load_dotenv
from datetime import datetime, timedelta
from logging import Logger
from typing import Any, Mapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from strategies.yape_email_strategy import YapeEmailStrategy
from strategies.interbank_email_strategy import InterbankEmailStrategy
from strategies.scotiabank_email_strategy import ScotiabankEmailStrategy
from strategies.bcp_email_strategy import BcpEmailStrategy
from pydantic import BaseModel
from models import Users
from zoneinfo import ZoneInfo
import logging, os


router: APIRouter = APIRouter()
load_dotenv()
WEB_CLIENT_ID: str | None = os.environ.get("WEB_CLIENT_ID")

logger: Logger = logging.getLogger(__name__)


class TokenBody(BaseModel):
    id_token: str


@router.post("/gmail/read-messages")
async def read_messages(
    token_body: TokenBody, db: AsyncSession = Depends(get_db)
) -> list[dict]:

    try:
        token = token_body.id_token

        info: Mapping[str, Any] = id_token.verify_oauth2_token(
            token, GoogleRequest(), WEB_CLIENT_ID
        )
        sub: Any | None = info.get("sub")

        return await read_gmail_messages(sub, db)

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token")
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def read_gmail_messages(sub, db: AsyncSession) -> list[dict]:
    async def get_tokens_by_sub(sub) -> tuple[str, str] | tuple[None, None]:
        result = await db.execute(
            select(Users.access_token, Users.refresh_token).where(Users.sub == sub)
        )
        tokens = result.fetchone()
        if tokens:
            return tokens[0], tokens[1]
        else:
            return None, None

    access_token, refresh_token = await get_tokens_by_sub(sub)

    # Zona horario de Perú (UTC-5)
    tz = ZoneInfo('America/Lima')

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

    strategies = [
        InterbankEmailStrategy(),
        YapeEmailStrategy(),
        ScotiabankEmailStrategy(),
        BcpEmailStrategy()
    ]

    movements_list: list[dict] = []

    for strategy in strategies:
        dicts_to_add = strategy.process_messages(
            after, before, refresh_token, sub, headers, db
        )
        if not dicts_to_add:
            continue
        for dicts in dicts_to_add:
            movements_list.append(dicts)

    return movements_list
