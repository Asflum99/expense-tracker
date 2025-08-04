from fastapi import HTTPException, APIRouter, Depends
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from dotenv import load_dotenv
from logging import Logger
from database import get_db
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from models import OAuthSession
from datetime import datetime, timedelta, timezone
import base64, urllib, uuid, hashlib, secrets, string, logging, os, urllib.parse

router = APIRouter()

logger: Logger = logging.getLogger(__name__)
load_dotenv()
ANDROID_CLIENT_ID = os.environ.get("ANDROID_CLIENT_ID")
WEB_CLIENT_ID = os.environ.get("WEB_CLIENT_ID")
API_URL = os.environ.get("API_URL")


class TokenBody(BaseModel):
    id_token: str


@router.post("/users/auth/google")
async def google_auth(token_body: TokenBody, db: AsyncSession = Depends(get_db)):
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

    try:
        token = token_body.id_token

        if not token:
            raise HTTPException(status_code=400, detail="Missing ID token")

        if not ANDROID_CLIENT_ID:
            raise HTTPException(status_code=500, detail="Missing ANDROID_CLIENT_ID")

        info = id_token.verify_oauth2_token(token, GoogleRequest(), WEB_CLIENT_ID)
        sub = info.get("sub")

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
                session_id=session_id,
                status="pending",
                expires_at=expires_at  # NUEVO
            )
        )
        await db.commit()
        auth_url = build_google_auth_url(
            WEB_CLIENT_ID,
            f"{API_URL}/oauth2callback",  # MODIFICADO
            "https://www.googleapis.com/auth/gmail.readonly",
            code_challenge,
            state,
        )

        return {
            "auth_url": auth_url,
            "session_id": session_id  # NUEVO
        }

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token")
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
