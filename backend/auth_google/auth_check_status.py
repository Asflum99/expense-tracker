import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import OAuthSession, Users

router = APIRouter()

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"


@router.get("/users/auth/status/{session_id}")
async def check_auth_status(session_id: str, db: AsyncSession = Depends(get_db)):
    oauth_session = await db.scalar(
        select(OAuthSession).where(OAuthSession.session_id == session_id)
    )

    if oauth_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if str(oauth_session.status) == "completed":
        user_result = await db.execute(
            select(Users).where(Users.sub == oauth_session.sub)
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        session_token = _generate_session_token(user)

        await db.execute(
            delete(OAuthSession).where(OAuthSession.session_id == session_id)
        )
        await db.commit()

        return {"status": "completed", "session_token": session_token}

    raise HTTPException(status_code=202, detail="Authentication pending")


def _generate_session_token(user: Users) -> str:
    payload = {
        "sub": user.sub,
        "user_id": user.id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "session_token",
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token
