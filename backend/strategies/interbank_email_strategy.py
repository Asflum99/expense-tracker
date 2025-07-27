from strategies.email_strategy_interface import EmailStrategy
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from typing import Match, Any
from datetime import datetime
from sqlalchemy import update
from models import Users
import requests, os, re, base64

load_dotenv()
WEB_CLIENT_ID: str | None = os.environ.get("WEB_CLIENT_ID")
CLIENT_SECRET: str | None = os.environ.get("CLIENT_SECRET")


class InterbankEmailStrategy(EmailStrategy):
    async def process_messages(
        self, after, before, refresh_token, sub, headers, db
    ) -> list[dict]:
        query = f"(from:servicioalcliente@netinterbank.com.pe after:{after} before:{before})"

        while True:
            search_response = requests.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params={"q": query},
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
                new_access_token = response.json().get("access_token")

                if response.status_code != 200:
                    raise Exception(f"Error al refrescar token: {response.text}")

                # 🔄 Importante: Actualiza también en la base de datos el nuevo access_token
                stmt = (
                    update(Users)
                    .where(Users.sub == sub)
                    .values(access_token=new_access_token)
                )
                await db.execute(stmt)
                await db.commit()

                headers: dict[str, str] = {
                    "Authorization": f"Bearer {new_access_token}"
                }
            else:
                raise Exception(
                    "No refresh_token disponible para renovar el access_token"
                )

        movements_list: list[dict] = []

        message_list: list[dict] = search_response.json().get("messages", [])

        if not message_list:
            return []

        for message in message_list:
            dict_to_send: dict[str, int | str] = {
                "date": "",
                "amount": 0,
                "category": "",
                "title": "",
                "note": "",
                "beneficiary": "",
                "account": "Interbank",
            }
            message_id: Any = message["id"]
            message_response = requests.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                headers=headers,
            )
            full_message = message_response.json()

            payload = full_message.get("payload", {})
            parts_1 = payload.get("parts", [])
            parts_2 = parts_1[0]
            parts_3 = parts_2.get("parts", [])
            parts_4 = parts_3[0]
            parts_5 = parts_4.get("body", {})

            message_body_coded = parts_5.get("data")

            # Decodificando el contenido del correo
            message_body_decoded = base64.urlsafe_b64decode(
                message_body_coded + "=" * (-len(message_body_coded) % 4)
            )
            decoded_html = message_body_decoded.decode("utf-8")

            soup = BeautifulSoup(decoded_html, "lxml")
            body_message_text = soup.get_text(separator=" ")
            cleaned_text = " ".join(body_message_text.split())

            amount_regex: float = float(
                str(re.search(r"\d+\.\d+", cleaned_text).group())
            )

            date_regex: str = re.search(
                r"\d{1,2}\s\w+\s\d{4}\s\d{1,2}:\d{2}\s[AP]M", cleaned_text
            ).group()

            dt = datetime.strptime(date_regex, "%d %b %Y %I:%M %p")

            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S.%f")

            beneficiary_regex: Match[str] | None = re.search(
                r"Destinatario:\s(.+?)\sDestino:", cleaned_text
            )
            if beneficiary_regex:
                beneficiary: str | Any = beneficiary_regex.group(1)
            else:
                beneficiary = ""

            # Guardar los datos en el diccionario
            dict_to_send["amount"] = -amount_regex
            dict_to_send["date"] = formatted_time
            dict_to_send["beneficiary"] = beneficiary

            movements_list.append(dict_to_send)

        return movements_list
