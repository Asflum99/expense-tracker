from fastapi import APIRouter, Depends, Header, HTTPException
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token as id_token_verifier
from google.auth.exceptions import GoogleAuthError
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from models import Users, OAuthSession
from database import get_db
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import logging, os, string, secrets, uuid, hashlib, base64, urllib.parse, jwt

router = APIRouter()

logger = logging.getLogger(__name__)

WEB_CLIENT_ID = os.environ.get("WEB_CLIENT_ID")
API_URL = os.environ.get("API_URL")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"


class IdToken(BaseModel):
    idToken: str


@router.post("/users/authenticate")
async def google_auth_status(
    authorization: str = Header(), db: AsyncSession = Depends(get_db)
):
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")

        id_token = authorization.replace("Bearer ", "")
        info = id_token_verifier.verify_oauth2_token(
            id_token, GoogleRequest(), WEB_CLIENT_ID
        )
        sub = info.get("sub")

        result = await db.execute(select(Users).where(Users.sub == sub))
        user = result.scalar_one_or_none()

        if user is None:
            auth_url, session_id = await _register_new_user(sub, db)
            return {
                "status": "unauthenticated",
                "auth_url": auth_url,
                "session_id": session_id,
            }

        session_token = await _generate_session_token(user)
        return {"status": "authenticated", "session_token": session_token}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def _register_new_user(sub: str, db: AsyncSession):
    def generate_code_verifier(length=128):
        allowed_chars = string.ascii_letters + string.digits + "-._~"
        return "".join(secrets.choice(allowed_chars) for _ in range(length))

    def generate_code_challenge(verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")

    def build_google_auth_url(
        client_id, redirect_uri, scope, code_challenge, state
    ) -> str:
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{base_url}?{urllib.parse.urlencode(params)}"

    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    await db.execute(
        insert(OAuthSession).values(
            sub=sub,
            code_verifier=code_verifier,
            state=state,
            session_id=session_id,  # OJO A ESTO
            status="pending",
            expires_at=expires_at,
        )
    )
    await db.commit()
    auth_url = build_google_auth_url(
        WEB_CLIENT_ID,
        f"{API_URL}/oauth2callback",
        "https://www.googleapis.com/auth/gmail.readonly",
        code_challenge,
        state,
    )

    return auth_url, session_id


async def _generate_session_token(user: Users) -> str:
    payload = {
        "sub": user.sub,
        "user_id": user.id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "session_token",
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token
