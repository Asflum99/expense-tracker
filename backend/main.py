from db_initializer import db_initializer
from category_assigner_with_ai import process_movements
from csv_generator import generate_csv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, RedirectResponse
from starlette.background import BackgroundTask
from google.oauth2 import id_token
from dotenv import load_dotenv
from google.auth.transport.requests import Request as GoogleRequest
from contextlib import closing
from datetime import datetime, timedelta, timezone
import os, logging, secrets, string, hashlib, base64, urllib.parse, uuid, uvicorn, requests, sqlite3, time, base64

app = FastAPI()
logger = logging.getLogger(__name__)
load_dotenv()
ANDROID_CLIENT_ID = os.environ.get("ANDROID_CLIENT_ID")
WEB_CLIENT_ID = os.environ.get("WEB_CLIENT_ID")
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


@app.post("/users/auth/status")
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


@app.post("/users/auth/google")
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
            "prompt": "consent"
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


@app.get("/oauth2callback")
async def oauth2callback(request: Request):
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
                raise Exception("Missing access_token in response")
            return result
        else:
            raise Exception(f"Token exchange failed: {response.text}")

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    code_verifier = load_data(state)
    sub = get_sub_by_state(state)

    if not code_verifier:
        raise HTTPException(400, "Missing code_verifier")

    if error:
        raise HTTPException(status_code=400, detail=f"Authorization failed: {error}")

    if code:
        tokens = exchange_code_for_token(
            WEB_CLIENT_ID, CLIENT_SECRET, code, code_verifier, f"{NGROK_URL}/oauth2callback"
        )
        delete_data(state)

        save_token(
            {
                "sub": sub,
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "expires_in": tokens["expires_in"]
            }
        )
        return RedirectResponse("cashew://oauth2callback", status_code=302)

    raise HTTPException(status_code=400, detail="No code or error received")


def access_message_body(full_message):
    payload = full_message.get("payload", {})
    parts = payload.get("parts", [])

    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part["body"]["data"]

            # Decodificando el contenido del correo
            decoded_bytes = base64.urlsafe_b64decode(data)
            decoded_text = decoded_bytes.decode("utf-8")

            return decoded_text


def access_messages(search_response, headers):
    message_list = search_response.json().get("messages", [])

    for message in message_list:
        message_id = message["id"]
        message_response = requests.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            headers=headers,
        )
        full_message = message_response.json()

        access_message_body(full_message)


def read_gmail_messages(sub):
    def get_tokens_by_sub(sub):
        with closing(sqlite3.connect("db.sqlite")) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT access_token, refresh_token FROM users WHERE sub = ?", (sub,))
            result = cursor.fetchone()
            if result:
                return result[0], result[1]
            else:
                return None, None

    access_token, refresh_token = get_tokens_by_sub(sub)
    
    headers = {"Authorization": f"Bearer {access_token}"}

    # Zona horario de Perú (UTC-5)
    peru_offset = timedelta(hours=-5)
    tz = timezone(peru_offset)

    # Medianoche en UTC-5
    midnight_yesterday = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    midnight_today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

    # Hora actual en UTC-5
    now = datetime.now(tz)

    # Convertir a timestamps
    after = int(midnight_today.timestamp())
    before = int(now.timestamp())

    # Crear el query
    interbank_filter = (
        f"from:notificaciones@yape.pe after:{after} before:{before}"
    )

    while True:
        search_response = requests.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers=headers,
            params={"q": interbank_filter},
        )

        if search_response.status_code == 200:
            break

        if refresh_token:
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": WEB_CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }

            response = requests.post(token_url, data)

            if response.status_code != 200:
                raise Exception(f"Error al refrescar token: {response.text}")

            access_token = response.json().get("access_token")
            headers = {"Authorization": f"Bearer {access_token}"}

            # 🔄 Importante: Actualiza también en la base de datos el nuevo access_token
            with closing(sqlite3.connect("db.sqlite")) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET access_token = ? WHERE sub = ?",
                    (access_token, sub)
                )
                conn.commit()
        else:
            raise Exception("No refresh_token disponible para renovar el access_token")

    access_messages(search_response, headers)

    pass


@app.post("/gmail/read-messages")
async def read_messages(request: Request):
    try:
        body = await request.json()
        token = body.get("id_token")

        if not token:
            raise HTTPException(status_code=400, detail="Missing ID token")

        info = id_token.verify_oauth2_token(token, GoogleRequest(), WEB_CLIENT_ID)
        sub = info.get("sub")

        read_gmail_messages(sub)

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token")
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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
