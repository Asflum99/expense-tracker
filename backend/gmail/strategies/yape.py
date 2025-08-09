from gmail.strategies.interface import EmailStrategy
from datetime import datetime
import requests, re, base64, logging

logger = logging.getLogger(__name__)

BENEFICIARY_PATTERN = r"Nombre del Beneficiario\s([^\r\n]+)"
DATE_PATTERN = r"(\d{1,2}\s\w+\s\d{4})\s-\s(\d{2}:\d{2}\s[ap]\.\sm\.)"
BANK_EMAIL = "notificaciones@yape.pe"
BANK_NAME = "BCP"


class YapeEmailStrategy(EmailStrategy):
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

            messages_list: list[dict] = search_response.json().get("messages", [])

            if not messages_list:
                return []

            _iterate_messages(self, messages_list, movements_list, headers)

            return movements_list
        except Exception as e:
            logger.warning(e)
            return []


def _iterate_messages(
    self: YapeEmailStrategy, messages_list, movements_list: list[dict], headers
):

    for message in messages_list:
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
            full_message.get("payload", {})
            .get("parts", [{}])[0]
            .get("body", {})
            .get("data")
        )

        cleaned_text = base64.urlsafe_b64decode(message_body).decode("utf-8")

        self.find_amount(cleaned_text, dict_to_send)
        _find_date(cleaned_text, dict_to_send)
        self.find_beneficiary(cleaned_text, dict_to_send, BENEFICIARY_PATTERN)
        movements_list.append(dict_to_send)


def _find_date(cleaned_text, dict_to_send):
    date_regex = re.search(
        DATE_PATTERN,
        cleaned_text,
    )

    if date_regex:
        date = date_regex.group()
        date = date.replace("a. m.", "AM").replace("p. m.", "PM")
        dt = datetime.strptime(date, "%d %B %Y - %I:%M %p")
        formatted = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        dict_to_send["date"] = formatted
