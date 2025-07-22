from fastapi import HTTPException, Request, APIRouter
from contextlib import closing
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import sqlite3, logging, os, requests, time

load_dotenv()
router = APIRouter()
logger = logging.getLogger(__name__)
WEB_CLIENT_ID = os.environ.get("WEB_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
NGROK_URL = os.environ.get("NGROK_URL")


@router.get("/oauth2callback")
async def oauth2callback(request: Request):
    def load_data(state):
        with closing(sqlite3.connect("db.sqlite")) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT code_verifier FROM oauth_sessions WHERE state = ?", (state,)
            )
            result = cursor.fetchone()
            return result[0] if result else None

    def get_sub_by_state(state):
        with closing(sqlite3.connect("db.sqlite")) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sub FROM oauth_sessions WHERE state = ?", (state,))
            result = cursor.fetchone()
            return result[0]

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
                raise HTTPException(status_code=400, detail="Missing access token in response")
            return result
        else:
            raise HTTPException(f"Token exchange failed: {response.text}")

    def delete_data(state):
        with closing(sqlite3.connect("db.sqlite")) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM oauth_sessions WHERE state = ?", (state,))
            conn.commit()

    def save_token(data):
        with closing(sqlite3.connect("db.sqlite")) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    sub TEXT UNIQUE,
                    access_token TEXT,
                    refresh_token TEXT,
                    expires_in INTEGER
                )
                """
            )

            sub = data["sub"]
            access_token = data["access_token"]
            refresh_token = data.get("refresh_token")
            expires_in = int(time.time()) + data["expires_in"]

            cursor.execute(
                """
                INSERT OR REPLACE INTO users (sub, access_token, refresh_token, expires_in) VALUES (?, ?, ?, ?)
                """,
                (sub, access_token, refresh_token, expires_in),
            )

            conn.commit()

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        raise HTTPException(status_code=400, detail=f"Authorization failed: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    code_verifier = load_data(state)
    if not code_verifier:
        raise HTTPException(400, "Missing code_verifier")
    sub = get_sub_by_state(state)

    if code:
        tokens = exchange_code_for_token(
            WEB_CLIENT_ID,
            CLIENT_SECRET,
            code,
            code_verifier,
            f"{NGROK_URL}/oauth2callback",
        )
        delete_data(state)

        save_token(
            {
                "sub": sub,
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens["expires_in"],
            }
        )

        html_content = """
        <html>
            <head><title>Redirigiendo...</title></head>
            <body>
                <script>
                    window.location.href = "cashew://oauth2callback";
                </script>
                <h1>Ya puedes cerrar esta ventana.</h1>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    raise HTTPException(status_code=400, detail="No code or error received")
