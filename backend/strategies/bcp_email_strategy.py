from strategies.email_strategy_interface import EmailStrategy
from dotenv import load_dotenv
from models import Users
from datetime import datetime
from sqlalchemy import update
from bs4 import BeautifulSoup
import os, requests, re, base64

load_dotenv()
WEB_CLIENT_ID: str | None = os.environ.get("WEB_CLIENT_ID")
CLIENT_SECRET: str | None = os.environ.get("CLIENT_SECRET")


class BcpEmailStrategy(EmailStrategy):
    async def process_messages(
        self, after, before, refresh_token, sub, headers, db
    ) -> list[dict]:
        query = f"(from:notificaciones@notificacionesbcp.com.pe after:{after} before:{before})"

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

                stmt = (
                    update(Users)
                    .where(Users.sub == sub)
                    .values(access_token=new_access_token)
                )
                await db.execute(stmt)
                await db.commit()

                headers["Authorization"] = f"Bearer {new_access_token}"
            else:
                raise Exception(
                    "No refresh_token disponible para renovar el access_token"
                )

        movements_list: list[dict] = []

        message_list = search_response.json().get("messages", [])

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
            message_id = message["id"]
            message_response = requests.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                headers=headers,
            )
            
            full_message = message_response.json()
            payload = full_message.get("payload")
            part_1 = payload.get("body")
            message_body = part_1.get("data")

            message_body_decoded = base64.urlsafe_b64decode(message_body + "=" * (-len(message_body) % 4))

            decoded_html = message_body_decoded.decode("utf-8")

            soup = BeautifulSoup(decoded_html, "lxml")
            body_message_text = soup.get_text(separator=" ")
            cleaned_text = " ".join(body_message_text.split())

            amount_regex = float(re.search(r"\d+\.\d+", cleaned_text).group())

            date_regex = re.search(r"\d+\sde\s\w+\sde\s\d{4}\s-\s\d{2}:\d{2}\s[AP]M", cleaned_text).group()
            dt = datetime.strptime(date_regex, "%d de %B de %Y - %I:%M %p")
            formatted_time = datetime.strftime(dt, "%Y-%m-%d %H:%M:%S.%f")

            beneficiary_regex = re.search(r"Empresa\s(.*?)\sNúmero", cleaned_text).group(1)

            dict_to_send["date"] = formatted_time
            dict_to_send["amount"] = -amount_regex
            dict_to_send["beneficiary"] = beneficiary_regex

            movements_list.append(dict_to_send)

        return movements_list
            