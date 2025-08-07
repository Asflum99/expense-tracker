from fastapi import HTTPException, APIRouter, Depends, Header
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from dotenv import load_dotenv
from datetime import datetime
from logging import Logger
from typing import Any, Mapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from gmail.strategies.email_strategy_interface import EmailStrategy
from gmail.strategies.yape_email_strategy import YapeEmailStrategy
from gmail.strategies.interbank_email_strategy import InterbankEmailStrategy
from gmail.strategies.scotiabank_email_strategy import ScotiabankEmailStrategy
from gmail.strategies.bcp_email_strategy import BcpEmailStrategy
from pydantic import BaseModel
from models import Users
from zoneinfo import ZoneInfo
from jwt import InvalidTokenError
import logging, os, jwt


router: APIRouter = APIRouter()
load_dotenv()
WEB_CLIENT_ID: str | None = os.environ.get("WEB_CLIENT_ID")
JWT_SECRET_KEY: str | None = os.environ.get("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"

logger: Logger = logging.getLogger(__name__)


class TokenBody(BaseModel):
    id_token: str


@router.get("/gmail/read-messages")
async def read_messages(
    authorization: str = Header(), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")

        session_token = authorization.replace("Bearer ", "")

        try:
            payload = jwt.decode(
                session_token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
            )
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        user_sub = payload.get("sub")

        return await read_gmail_messages(user_sub, db)

    except ValueError as e:
        print(f"{str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
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
    tz = ZoneInfo("America/Lima")

    # Medianoche en UTC-5
    midnight_today: datetime = datetime.now(tz).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}

    # Hora actual en UTC-5
    now: datetime = datetime.now(tz)

    # Convertir a timestamps
    after: int = int(midnight_today.timestamp())
    before: int = int(now.timestamp())

    strategies: list[EmailStrategy] = [
        InterbankEmailStrategy(),
        YapeEmailStrategy(),
        ScotiabankEmailStrategy(),
        BcpEmailStrategy(),
    ]

    movements_list: list[dict] = []

    for strategy in strategies:
        dicts_to_add = await strategy.process_messages(
            after, before, refresh_token, sub, headers, db
        )
        if not dicts_to_add:
            continue
        for dicts in dicts_to_add:
            movements_list.append(dicts)

    return movements_list
