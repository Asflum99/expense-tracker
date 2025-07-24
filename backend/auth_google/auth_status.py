from fastapi import APIRouter, Depends
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Users
from database import get_db
from pydantic import BaseModel
import logging, os

router = APIRouter()

logger = logging.getLogger(__name__)

load_dotenv()
WEB_CLIENT_ID = os.environ.get("WEB_CLIENT_ID")


class TokenBody(BaseModel):
    id_token: str


@router.post("/users/auth/status")
async def google_auth_status(token_body: TokenBody, db: AsyncSession = Depends(get_db)):
    try:
        token = token_body.id_token

        info = id_token.verify_oauth2_token(token, GoogleRequest(), WEB_CLIENT_ID)
        sub = info.get("sub")

        result = await db.execute(select(Users.access_token).where(Users.sub == sub))
        access_token = result.scalar_one_or_none()

        return {"authenticated": bool(access_token)}

    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        return {"authenticated": False}
