from strategies.email_strategy_interface import EmailStrategy
from dotenv import load_dotenv
from datetime import datetime
from typing import Match, Any
from backend.models import Users
from sqlalchemy import update
import requests, os, re, base64

load_dotenv()
WEB_CLIENT_ID: str | None = os.environ.get("WEB_CLIENT_ID")
CLIENT_SECRET: str | None = os.environ.get("CLIENT_SECRET")


class YapeEmailStrategy(EmailStrategy):
    async def process_messages(
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
                await db.execute(stmt)
                await db.commit()

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
            dict_to_send: dict[str, float | str] = {
                "date": "",
                "amount": 0.0,
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

            amount_regex: Match[str] | None = re.search(
                r"\d+\.\d+", message_body_decoded
            )
            if amount_regex:
                amount: float = float(amount_regex.group())
                dict_to_send["amount"] = -amount

            date_regex: Match[str] | None = re.search(
                r"(\d{1,2}\s\w+\s\d{4})\s-\s(\d{2}:\d{2}\s[ap]\.\sm\.)",
                message_body_decoded,
            )
            if date_regex:
                date = date_regex.group()
                date = date.replace("a. m.", "AM").replace("p. m.", "PM")
                dt = datetime.strptime(date, "%d %B %Y - %I:%M %p")
                formatted = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                dict_to_send["date"] = formatted

            beneficiary_regex: Match[str] | None = re.search(
                r"Nombre del Beneficiario\s([^\r\n]+)", message_body_decoded
            )
            if beneficiary_regex:
                beneficiary: str = str(beneficiary_regex.group(1))
                dict_to_send["beneficiary"] = beneficiary

            movements_list.append(dict_to_send)

        return movements_list
