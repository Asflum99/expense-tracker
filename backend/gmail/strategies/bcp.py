from gmail.strategies.interface import EmailStrategy
from bs4 import BeautifulSoup
from datetime import datetime
import requests, re, base64, logging

logger = logging.getLogger(__name__)

BENEFICIARY_PATTERN = r"Destinatario:\s(.+?)\sDestino:"
DATE_PATTERN = r"\d+\sde\s\w+\sde\s\d{4}\s-\s\d{2}:\d{2}"
BANK_EMAIL = "notificaciones@notificacionesbcp.com.pe"
BANK_NAME = "BCP"


class BcpEmailStrategy(EmailStrategy):
    async def process_messages(
        self, after, before, refresh_token, sub, headers, db
    ) -> list[dict]:
        try:
            search_response = await self.ask_google(
                BANK_EMAIL,
                after,
                before,
                refresh_token,
                db,
                sub,
                headers,
            )

            movements_list: list[dict] = []

            messages_list = search_response.json().get("messages", [])

            if not messages_list:
                return []

            _iterate_messages(self, messages_list, headers, movements_list)

            return movements_list
        except Exception as e:
            logger.warning(e)
            return []


def _iterate_messages(
    self: BcpEmailStrategy, messages_list, headers, movements_list: list[dict]
):
    for message in messages_list:
        try:
            dict_to_send: dict[str, float | str] = {
                "date": "",
                "amount": 0.0,
                "category": "",
                "title": "",
                "note": "",
                "beneficiary": "",
                "account": BANK_NAME,
            }
            message_id = message["id"]
            message_response = requests.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                headers=headers,
            )
            full_message = message_response.json()
            message_body = (
                full_message.get("payload", {}).get("parts")[1].get("body").get("data")
            )

            message_body_decoded = base64.urlsafe_b64decode(
                message_body + "=" * (-len(message_body) % 4)
            )

            decoded_html = message_body_decoded.decode("utf-8")

            soup = BeautifulSoup(decoded_html, "lxml")

            body_message_text = soup.get_text(separator=" ")
            cleaned_text = " ".join(body_message_text.split())
            logger.info(cleaned_text)

            self.find_amount(cleaned_text, dict_to_send)
            _find_date(cleaned_text, dict_to_send)
            self.find_beneficiary(cleaned_text, dict_to_send, BENEFICIARY_PATTERN)
        except Exception:
            continue
        movements_list.append(dict_to_send)


def _find_date(cleaned_text: str, dict_to_send):
    date_regex = re.findall(DATE_PATTERN, cleaned_text)
    if date_regex:
        date = date_regex[0]
        dt = datetime.strptime(date, "%d de %B de %Y - %H:%M")
        formatted_time = datetime.strftime(dt, "%Y-%m-%d %H:%M:%S.%f")
        dict_to_send["date"] = formatted_time
    else:
        # Handle the case where date_regex is empty
        formatted_time = None
