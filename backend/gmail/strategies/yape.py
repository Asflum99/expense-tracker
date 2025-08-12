import base64
import logging
import re

import requests
from bs4 import BeautifulSoup

from gmail.strategies.interface import EmailStrategy

logger = logging.getLogger(__name__)

BENEFICIARY_PATTERN = r"Nombre del Beneficiario\s(.+?)\sN"
DATE_PATTERN = r"(\d{1,2}\s\w+\s\d{4})\s-\s(\d{2}:\d{2}\s[ap]\.\sm\.)"
BANK_EMAIL = "notificaciones@yape.pe"
BANK_NAME = "BCP"
YAPE_DATE_FORMAT = "%d %B %Y - %I:%M %p"


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
        payload = message_response.json().get("payload", {})
        message_body = self.get_html_body_data(payload)

        text = base64.urlsafe_b64decode(message_body).decode("utf-8")
        soup = BeautifulSoup(text, "lxml")
        body_message_text = soup.get_text(separator=" ")
        cleaned_text = " ".join(body_message_text.split())

        self.find_amount(cleaned_text, dict_to_send)
        self.find_beneficiary(cleaned_text, dict_to_send, BENEFICIARY_PATTERN)
        _find_date(self, cleaned_text, dict_to_send)
        movements_list.append(dict_to_send)


def _find_date(self: YapeEmailStrategy, cleaned_text, dict_to_send):
    if date_regex := re.search(DATE_PATTERN, cleaned_text):
        date = date_regex.group()
        date = date.replace("a. m.", "AM").replace("p. m.", "PM")
        self.format_date(date, YAPE_DATE_FORMAT, dict_to_send)
    else:
        dict_to_send["date"] = ""
