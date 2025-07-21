from fastapi import Request, HTTPException, APIRouter
from google.oauth2 import id_token
from google.auth.transport.requests import Request as GoogleRequest
from dotenv import load_dotenv
from contextlib import closing
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from logging import Logger
from typing import Match, Any, Mapping, Optional, Coroutine
from sqlite3 import Cursor
import logging, os, sqlite3, requests, base64, re


router: APIRouter = APIRouter()
load_dotenv()
WEB_CLIENT_ID: str | None = os.environ.get("WEB_CLIENT_ID")
CLIENT_SECRET: str | None = os.environ.get("CLIENT_SECRET")

logger: Logger = logging.getLogger(__name__)


@router.post("/gmail/read-messages")
async def read_messages(request: Request) -> list[dict]:
    try:
        body: dict = await request.json()
        token: Optional[str] = body.get("id_token")

        info: Mapping[str, Any] = id_token.verify_oauth2_token(token, GoogleRequest(), WEB_CLIENT_ID)
        sub: Any | None = info.get("sub")

        return read_gmail_messages(sub)

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token")
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def read_gmail_messages(sub) -> list[dict]:
    def get_tokens_by_sub(sub) -> tuple[str, str] | tuple[None, None]:
        with closing(sqlite3.connect("db.sqlite")) as conn:
            cursor: Cursor = conn.cursor()
            cursor.execute(
                "SELECT access_token, refresh_token FROM users WHERE sub = ?", (sub,)
            )
            result: Any = cursor.fetchone()
            if result:
                return result[0], result[1]
            else:
                return None, None

    access_token, refresh_token = get_tokens_by_sub(sub)

    headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}

    # Zona horario de Perú (UTC-5)
    peru_offset: timedelta = timedelta(hours=-5)
    tz: timezone = timezone(peru_offset)

    # Medianoche en UTC-5
    midnight_yesterday: datetime = datetime.now(tz).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=1)
    midnight_today: datetime = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)

    # Hora actual en UTC-5
    now: datetime = datetime.now(tz)

    # Convertir a timestamps
    after: int = int(midnight_today.timestamp())
    before: int = int(now.timestamp())

    # Crear el query
    interbank_filter: str = (
        f"from:servicioalcliente@netinterbank.com.pe after:{after} before:{before}"
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
            data: dict[str, str | None] = {
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
                cursor: Cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET access_token = ? WHERE sub = ?",
                    (access_token, sub),
                )
                conn.commit()
        else:
            raise Exception("No refresh_token disponible para renovar el access_token")

    movements_list: list[dict] = access_messages(search_response, headers)

    return movements_list


def access_messages(search_response, headers) -> list[dict[Any, Any]]:
    movements_list: list[dict] = []

    message_list: list[dict] = search_response.json().get("messages", [])

    for message in message_list:
        dict_to_send: dict[str, int | str] = {
            "data": "",
            "amount": 0,
            "category": "",
            "title": "",
            "note": "",
            "beneficiary": "",
            "account": "",
        }
        message_id: Any = message["id"]
        message_response = requests.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            headers=headers,
        )
        full_message = message_response.json()

        access_message_body(full_message, dict_to_send)

        movements_list.append(dict_to_send)

    return movements_list


def access_message_body(full_message, dict_to_send) -> None:
    payload = full_message.get("payload", {})
    parts_1 = payload.get("parts", [])
    parts_2 = parts_1[0]
    parts_3 = parts_2.get("parts", [])
    parts_4 = parts_3[0]

    for key in parts_4:
        if key == "mimeType":
            message_body_dict = parts_4.get("body")
            message_body_coded = message_body_dict.get("data")

            # Decodificando el contenido del correo
            message_body_decoded = base64.urlsafe_b64decode(
                message_body_coded + "=" * (-len(message_body_coded) % 4)
            )
            decoded_html = message_body_decoded.decode("utf-8")

            soup = BeautifulSoup(decoded_html, "lxml")
            body_message_text = soup.get_text(separator=" ")
            cleaned_text = " ".join(body_message_text.split())

            save_data_in_dict(cleaned_text, dict_to_send)

        break


def save_data_in_dict(text, dict_to_send) -> None:
    amount_regex: float = float(str(re.search(r"\d+\.\d+", text)))
    date_regex: Match[str] | None = re.search(r"\d{1,2}\s\w+\s\d{4}\s\d{1,2}:\d{2}\s[AP]M", text)
    destinatary_regex: Match[str] | None = re.search(r"Destinatario:\s(.+?)\sDestino:", text)
    if destinatary_regex:
        destinatary: str | Any = destinatary_regex.group(1)
    else:
        destinatary = ""

    # Guardar los datos en el diccionario
    dict_to_send["amount"] = amount_regex
    dict_to_send["data"] = date_regex
    dict_to_send["beneficiary"] = destinatary_regex
