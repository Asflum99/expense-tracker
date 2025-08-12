import base64
import logging
import re

import requests
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from gmail.strategies.interface import EmailStrategy

logger = logging.getLogger(__name__)

BANK_EMAIL = "servicioalcliente@netinterbank.com.pe"
BENEFICIARY_PATTERN = r"Destinatario:\s(.+?)\sDestino:"
DATE_PATTERN = r"\d{1,2}\s\w+\s\d{4}\s\d{1,2}:\d{2}\s[AP]M"
BANK_NAME = "Interbank"
INTERBANK_DATE_FORMAT = "%d %b %Y %I:%M %p"


class InterbankEmailStrategy(EmailStrategy):
    async def process_messages(
        self, after, before, refresh_token, sub, headers, db: AsyncSession
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

            messages_list: list[dict] = search_response.json().get("messages")

            if not messages_list:
                return []

            _iterate_messages(self, messages_list, headers, movements_list)

            return movements_list
        except Exception as e:
            logger.warning(e)
            return []


def _iterate_messages(
    self: InterbankEmailStrategy, messages_list, headers, movements_list: list[dict]
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
        message_body_coded = self.get_html_body_data(payload)
        if message_body_coded == "":
            continue

        message_body_decoded = base64.urlsafe_b64decode(
            message_body_coded + "=" * (-len(message_body_coded) % 4)
        )
        decoded_html = message_body_decoded.decode("utf-8")

        soup = BeautifulSoup(decoded_html, "lxml")
        body_message_text = soup.get_text(separator=" ")
        cleaned_text = " ".join(body_message_text.split())

        self.find_amount(cleaned_text, dict_to_send)
        self.find_beneficiary(cleaned_text, dict_to_send, BENEFICIARY_PATTERN)
        _find_date(self, cleaned_text, dict_to_send)
        movements_list.append(dict_to_send)


def _find_date(
    self: InterbankEmailStrategy,
    cleaned_text: str,
    dict_to_send: dict[str, float | str],
) -> None:
    if match := re.search(DATE_PATTERN, cleaned_text):
        date_regex = match.group()
        self.format_date(date_regex, INTERBANK_DATE_FORMAT, dict_to_send)
    else:
        dict_to_send["date"] = ""
