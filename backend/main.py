from db_initializer import db_initializer
from category_assigner_with_ai import process_movements
from csv_generator import generate_csv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from google.oauth2 import id_token
from dotenv import load_dotenv
from pathlib import Path
from google.auth.transport.requests import Request as GoogleRequest
import os, logging, secrets, string, hashlib, base64, urllib.parse, uuid, uvicorn, json, requests

app = FastAPI()
logger = logging.getLogger(__name__)
load_dotenv()
CLIENT_ID = os.environ.get("CLIENT_ID")
NGROK_URL = os.environ.get("NGROK_URL")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
VERIFIER_FILE = Path("verifiers.json")


def load_verifier_store():
    if VERIFIER_FILE.exists():
        with open(VERIFIER_FILE, "r") as f:
            return json.load(f)
    return {}

def save_verifier_store(store):
    with open(VERIFIER_FILE, "w") as f:
        json.dump(store, f)

@app.post("/users/auth/google")
async def google_auth(request: Request):
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
        verifier_store = load_verifier_store()
        state = str(uuid.uuid4())
        verifier_store[state] = code_verifier
        save_verifier_store(verifier_store)
        auth_url = build_google_auth_url(
            CLIENT_ID,
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


def generate_code_verifier(length=128):
    allowed_chars = string.ascii_letters + string.digits + "-._~"
    return "".join(secrets.choice(allowed_chars) for _ in range(length))


def generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")


def build_google_auth_url(client_id, redirect_uri, scope, code_challenge, state) -> str:
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


@app.get("/oauth2callback")
def oauth2callback(request: Request):
    verifier_store = load_verifier_store()

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")
    
    code_verifier = verifier_store.get(state)

    if not code_verifier:
        raise HTTPException(400, "Missing code_verifier")

    if error:
        raise HTTPException(status_code=400, detail=f"Authorization failed: {error}")

    if code:
        tokens = exchange_code_for_token(
            CLIENT_ID, CLIENT_SECRET,code, code_verifier, f"{NGROK_URL}/oauth2callback"
        )
        code_verifier = verifier_store.pop(state, None)
        save_verifier_store(verifier_store)
        return {"message": "Authorization code received", "tokens": tokens}

    raise HTTPException(status_code=400, detail="No code or error received")


def exchange_code_for_token(client_id, client_secret, code, code_verifier, redirect_uri):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "code_verifier": code_verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }

    response = requests.post(token_url, data=data)

    if response.status_code == 200:
        result = response.json()
        if "access_token" not in result:
            raise Exception("Missing access_token in response")
        return result
    else:
        raise Exception(f"Token exchange failed: {response.text}")


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
