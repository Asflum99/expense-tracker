from db_initializer import db_initializer
from category_assigner_with_ai import process_movements
from csv_generator import generate_csv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from google.oauth2 import id_token
from dotenv import load_dotenv
from google.auth.transport.requests import Request as GoogleRequest
from contextlib import closing
import os, logging, secrets, string, hashlib, base64, urllib.parse, uuid, uvicorn, requests, sqlite3, time

app = FastAPI()
logger = logging.getLogger(__name__)
load_dotenv()
CLIENT_ID = os.environ.get("CLIENT_ID")
NGROK_URL = os.environ.get("NGROK_URL")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")


def load_data(state):
    with closing(sqlite3.connect("db.sqlite")) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT code_verifier FROM oauth_sessions WHERE state = ?", (state,)
        )
        result = cursor.fetchone()
        return result[0] if result else None


def save_data(code_verifier, state):
    with closing(sqlite3.connect("db.sqlite")) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_verifier TEXT NOT NULL,
                state TEXT NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            INSERT INTO oauth_sessions (code_verifier, state) VALUES (?, ?)
            """,
            (code_verifier, state),
        )

        conn.commit()


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
                user_id TEXT PRIMARY KEY,
                email TEXT,
                name TEXT,
                access_token TEXT,
                refresh_token TEXT,
                expires_in INTEGER
            )
            """
        )

        user_id = data["user"]["id"]
        email = data["user"]["email"]
        name = data["user"]["name"]
        access_token = data["access_token"]
        refresh_token = data.get("refresh_token")
        expires_in = int(time.time()) + data["expires_in"]

        cursor.execute(
            """
            INSERT OR REPLACE INTO users (user_id, email, name, access_token, refresh_token, expires_in) VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, email, name, access_token, refresh_token, expires_in)
        )

        conn.commit()


@app.post("/users/auth/google")
async def google_auth(request: Request):
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
        }
        return f"{base_url}?{urllib.parse.urlencode(params)}"

    try:
        # Leer el body
        body = await request.json()
        token = body.get("id_token")

        if not token:
            raise HTTPException(status_code=400, detail="Missing ID token")

        if not CLIENT_ID:
            raise HTTPException(status_code=500, detail="Missing CLIENT_ID")

        id_token.verify_oauth2_token(token, GoogleRequest(), CLIENT_ID)

        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        state = str(uuid.uuid4())
        try:
            save_data(code_verifier, state)
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Duplicated state")
        auth_url = build_google_auth_url(
            CLIENT_ID,
            "cashew:/oauth2callback",
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


@app.get("/oauth2callback")
async def oauth2callback(request: Request):
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
                raise Exception("Missing access_token in response")
            return result
        else:
            raise Exception(f"Token exchange failed: {response.text}")

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    code_verifier = load_data(state)

    if not code_verifier:
        raise HTTPException(400, "Missing code_verifier")

    if error:
        raise HTTPException(status_code=400, detail=f"Authorization failed: {error}")

    if code:
        tokens = exchange_code_for_token(
            CLIENT_ID, CLIENT_SECRET, code, code_verifier, f"{NGROK_URL}/oauth2callback"
        )
        delete_data(state)

        # Llamar a la API de Google para obtener los datos del usuario
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        userinfo_response = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo?alt=json", headers=headers
        )
        if userinfo_response.status_code != 200:
            raise HTTPException(500, "Error obteniendo información del usuario de Google")
        userinfo = userinfo_response.json()
        save_token({
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens["expires_in"],
            "user": userinfo,
        })
        return {"message": "Authorization successful", "user": userinfo}

    raise HTTPException(status_code=400, detail="No code or error received")


@app.post("/process-expenses")
async def process_expenses(request: Request):
    body = await request.json()

    conn, cursor = db_initializer()
    process_movements(conn, cursor, body)
    csv_path = generate_csv(body)
    conn.close()

    # Abrimos el archivo como stream
    file_stream = open(csv_path, mode="rb")
    response = StreamingResponse(file_stream, media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=gastos.csv"

    def remove_file():
        file_stream.close()
        os.remove(csv_path)

    background_task = BackgroundTask(remove_file)

    response = StreamingResponse(
        file_stream, media_type="text/csv", background=background_task
    )
    response.headers["Content-Disposition"] = "attachment; filename=gastos.csv"

    return response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)