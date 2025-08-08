from gmail.strategies.email_strategy_interface import EmailStrategy
from datetime import datetime
from typing import Match, Any
from bs4 import BeautifulSoup
import requests, re, base64, logging

logger = logging.getLogger(__name__)


class ScotiabankEmailStrategy(EmailStrategy):
    async def process_messages(
        self, after, before, refresh_token, sub, headers, db
    ) -> list[dict]:
        try:
            search_response = await self.ask_google(
                "bancadigital@scotiabank.com.pe",
                after,
                before,
                refresh_token,
                db,
                sub,
                headers,
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
                    "account": "Scotiabank",
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

                # Extraer año
                year_1 = payload.get("headers")
                year_2 = {}
                for i in year_1:
                    if i["name"] == "Date":
                        year_2 = i
                        break
                year_3 = year_2.get("value")
                if year_3:
                    exact_year = re.search(r"(?<![-\d])\d{4}(?!\d)", year_3)
                    if exact_year is not None:
                        exact_year = exact_year.group()
                else:
                    # Handle the case where year_3 is None
                    exact_year = None
                    print("Error: Could not extract year from message headers")

                message_body_decoded = base64.urlsafe_b64decode(
                    message_body + "=" * (-len(message_body) % 4)
                )
                decoded_html = message_body_decoded.decode("utf-8")

                soup = BeautifulSoup(decoded_html, "lxml")
                body_message_text = soup.get_text(separator=" ")
                cleaned_text = " ".join(body_message_text.split())

                amount_regex = re.search(r"\d+\.\d+", cleaned_text)
                if amount_regex:
                    amount = float(amount_regex.group())
                    dict_to_send["amount"] = -amount

                date_regex = re.search(
                    r"\d{1,2}\s\w+[,\.]+\s\d{2}:\d{2}\s[ap]m", cleaned_text
                )
                if date_regex:
                    date_regex = date_regex.group()

                # Transformar a la pedida por Cashew
                date_complete = f"{exact_year} {date_regex}"
                clean_date = date_complete.replace(".", "").replace(",", "")

                dt = datetime.strptime(clean_date, "%Y %d %b %I:%M %p")

                real_time = dt.strftime("%Y-%m-%d %H:%M:%S.%f")

                beneficiary_regex: Match[str] | None = re.search(
                    r"Enviado a:\s*((?!\d)[A-ZÁÉÍÓÚÑa-záéíóúñ\s]+?)(?=\s(?:Con|S\/|\d|$))",
                    cleaned_text,
                )
                if beneficiary_regex:
                    beneficiary: str | Any = beneficiary_regex.group(1)
                else:
                    beneficiary = ""

                # Guardar los datos en el diccionario
                dict_to_send["date"] = real_time
                dict_to_send["beneficiary"] = beneficiary

                movements_list.append(dict_to_send)

            return movements_list
        except Exception as e:
            logger.warning(e)
            return []
