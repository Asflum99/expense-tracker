import logging

import jwt
from fastapi import HTTPException
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from models import Users

JWT_SECRET_KEY = Settings.jwt_secret_key
JWT_ALGORITHM = "HS256"

logger = logging.getLogger(__name__)


def _extract_user_sub(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        logger.warning("Invalid authorization header format")
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    session_token = authorization.removeprefix("Bearer ")

    try:
        payload = jwt.decode(session_token, JWT_SECRET_KEY, [JWT_ALGORITHM])
        sub = payload.get("sub")

        if not sub:
            logger.warning("Token missing 'sub' claim")
            raise HTTPException(status_code=401, detail="Invalid token")

        return sub

    except ExpiredSignatureError:
        logger.info("Expired token attempt")
        raise HTTPException(status_code=401, detail="Token has expired")

    except InvalidTokenError:
        logger.warning("Invalid token attempt")
        raise HTTPException(status_code=401, detail="Invalid token")

    except HTTPException:
        raise

    except Exception as e:
        logger.critical(f"Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def _get_tokens_by_sub(sub: str, db: AsyncSession) -> tuple[str, str]:
    try:
        result = await db.execute(
            select(Users.access_token, Users.refresh_token).where(Users.sub == sub)
        )

        if tokens := result.fetchone():
            access_token, refresh_token = tokens[0], tokens[1]

            # Verificar que los tokens no estén vacíos
            if not access_token or not refresh_token:
                logger.error(f"get_tokens_by_sub: Empty tokens found for sub {sub}")
                raise HTTPException(status_code=401, detail="Invalid tokens found")

            return access_token, refresh_token
        else:
            logger.error(f"get_tokens_by_sub: No tokens found for sub {sub}")
            raise HTTPException(status_code=401, detail="No se encontraron tokens")

    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"get_tokens_by_sub: Database error for sub {sub}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")


async def authenticate_user(authorization: str, db: AsyncSession):
    """
    Autentica usuario y retorna sub + tokens.
    """
    user_sub = _extract_user_sub(authorization)
    access_token, refresh_token = await _get_tokens_by_sub(user_sub, db)
    return user_sub, access_token, refresh_token
