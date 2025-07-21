from fastapi import HTTPException, Request, APIRouter
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from contextlib import closing
from dotenv import load_dotenv
import sqlite3, logging, os

router = APIRouter()

logger = logging.getLogger(__name__)

load_dotenv()
WEB_CLIENT_ID = os.environ.get("WEB_CLIENT_ID")


@router.post("/users/auth/status")
async def google_auth_status(request: Request):
    try:
        body = await request.json()
        token = body.get("id_token")

        if not token:
            raise HTTPException(status_code=400, detail="Missing ID token")

        info = id_token.verify_oauth2_token(token, GoogleRequest(), WEB_CLIENT_ID)
        sub = info.get("sub")

        with closing(sqlite3.connect("db.sqlite")) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT access_token FROM users WHERE sub = ?", (sub,))
            result = cursor.fetchone()
            if result:
                return {"authenticated": True}
            else:
                return {"authenticated": False}

    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        return {"authenticated": False}
