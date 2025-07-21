import urllib.parse
from fastapi import Request, HTTPException, APIRouter
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from contextlib import closing
from dotenv import load_dotenv
from logging import Logger
import sqlite3, base64, urllib, uuid, hashlib, secrets, string, logging, os

router = APIRouter()

logger: Logger = logging.getLogger(__name__)
load_dotenv()
ANDROID_CLIENT_ID = os.environ.get("ANDROID_CLIENT_ID")
WEB_CLIENT_ID = os.environ.get("WEB_CLIENT_ID")
NGROK_URL = os.environ.get("NGROK_URL")


@router.post("/users/auth/google")
async def google_auth(request: Request):
    def save_data(sub, code_verifier, state):
        with closing(sqlite3.connect("db.sqlite")) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sub TEXT NOT NULL,
                    code_verifier TEXT NOT NULL,
                    state TEXT NOT NULL UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                INSERT INTO oauth_sessions (sub, code_verifier, state) VALUES (?, ?, ?)
                """,
                (sub, code_verifier, state),
            )

            conn.commit()

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
        # Leer el body
        body = await request.json()
        token = body.get("id_token")

        if not token:
            raise HTTPException(status_code=400, detail="Missing ID token")

        if not ANDROID_CLIENT_ID:
            raise HTTPException(status_code=500, detail="Missing ANDROID_CLIENT_ID")

        info = id_token.verify_oauth2_token(token, GoogleRequest(), WEB_CLIENT_ID)
        sub = info.get("sub")

        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        state = str(uuid.uuid4())
        try:
            save_data(sub, code_verifier, state)
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Duplicated state")
        auth_url = build_google_auth_url(
            WEB_CLIENT_ID,
            f"{NGROK_URL}/oauth2callback",
            "https://www.googleapis.com/auth/gmail.readonly",
            code_challenge,
            state,
        )

        return {"auth_url": auth_url}

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token")
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
