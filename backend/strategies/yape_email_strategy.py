from strategies.email_strategy_interface import EmailStrategy
from dotenv import load_dotenv
from datetime import datetime
from typing import Match, Any
from models import Users
from sqlalchemy import update
import requests, os, re, base64, locale

load_dotenv()
WEB_CLIENT_ID: str | None = os.environ.get("WEB_CLIENT_ID")
CLIENT_SECRET: str | None = os.environ.get("CLIENT_SECRET")


class YapeEmailStrategy(EmailStrategy):
    def process_messages(
        self, after, before, refresh_token, sub, headers, db
    ) -> list[dict]:
        query = f"(from:notificaciones@yape.pe after:{after} before:{before})"

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
                db.execute(stmt)
                db.commit()

                headers = {"Authorization": f"Bearer {new_access_token}"}
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
                "account": "BCP",
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
            parts_3 = parts_2.get("body", [])
            message_body = parts_3.get("data", {})

            message_body_decoded = base64.urlsafe_b64decode(message_body).decode(
                "utf-8"
            )

            amount_regex: Match[str] = re.search(r"\d+\.\d+", message_body_decoded)
            if amount_regex:
                amount_regex: float = float(amount_regex.group())

            date_regex: Match[str] | None = re.search(
                r"(\d{1,2}\s\w+\s\d{4})\s-\s(\d{2}:\d{2}\s[ap]\.\sm\.)",
                message_body_decoded,
            )
            if date_regex:
                date_regex: str = str(date_regex.group())

            date_regex = date_regex.replace("p. m.", "PM").replace("a. m.", "AM")

            # Convertir fecha a la requerida por Cashew
            locale.setlocale(locale.LC_TIME, "es_PE.utf8")
            dt = datetime.strptime(date_regex, "%d %B %Y - %I:%M %p")
            formatted = dt.strftime("%Y-%m-%d %H:%M:%S.%f")

            beneficiary_regex: Match[str] | None = re.search(
                r"Nombre del Beneficiario\s([^\r\n]+)", message_body_decoded
            )
            if beneficiary_regex:
                beneficiary_regex: str = str(beneficiary_regex.group(1))

            # Guardar los datos en el diccionario
            dict_to_send["amount"] = -amount_regex
            dict_to_send["date"] = formatted
            dict_to_send["beneficiary"] = beneficiary_regex

            movements_list.append(dict_to_send)

        return movements_list
