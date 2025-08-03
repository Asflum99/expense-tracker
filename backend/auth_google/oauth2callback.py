from fastapi import HTTPException, APIRouter, Depends
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from models import OAuthSession, Users
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from pydantic import BaseModel
from typing import Optional
import logging, os, requests

load_dotenv()
router = APIRouter()
logger = logging.getLogger(__name__)
WEB_CLIENT_ID = os.environ.get("WEB_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
API_URL = os.environ.get("API_URL")


class OAuth2CallbackParams(BaseModel):
    code: str
    state: str
    error: Optional[str] = None


@router.get("/oauth2callback")
async def oauth2callback(
    params: OAuth2CallbackParams = Depends(), db: AsyncSession = Depends(get_db)
):
    def exchange_code_for_token(
        client_id, client_secret, code, code_verifier, redirect_uri
    ):
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        response = requests.post(token_url, data)

        if response.status_code == 200:
            result = response.json()
            if "access_token" not in result:
                raise HTTPException(
                    status_code=400, detail="Missing access token in response"
                )
            return result
        else:
            raise HTTPException(f"Token exchange failed: {response.text}")

    code = params.code
    state = params.state
    error = params.error

    if error:
        raise HTTPException(status_code=400, detail=f"Authorization failed: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    result_code_verifier = await db.execute(
        select(OAuthSession.code_verifier).where(OAuthSession.state == state)
    )
    code_verifier = result_code_verifier.scalar_one_or_none()
    if not code_verifier:
        raise HTTPException(400, "Missing code_verifier")

    sub_result = await db.execute(
        select(OAuthSession.sub).where(OAuthSession.state == state)
    )
    sub = sub_result.scalar_one_or_none()

    if code:
        tokens = exchange_code_for_token(
            WEB_CLIENT_ID,
            CLIENT_SECRET,
            code,
            code_verifier,
            f"{API_URL}/oauth2callback",
        )
        await db.execute(delete(OAuthSession).where(OAuthSession.state == state))
        await db.commit()

        stmt = insert(Users).values(
            sub=sub,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens["expires_in"],
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["sub"],
            set_={
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens["expires_in"],
            },
        )
        await db.execute(stmt)
        await db.commit()

        html_content = """
        <html>
            <head><title>Redirigiendo...</title></head>
            <body>
                <script>
                    window.location.href = "expensetracker://oauth2callback";
                </script>
                <h1>Ya puedes cerrar esta ventana.</h1>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    raise HTTPException(status_code=400, detail="No code or error received")
