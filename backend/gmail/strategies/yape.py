import base64
import binascii
import logging
import re

import httpx
from bs4 import BeautifulSoup

from gmail.strategies.interface import EmailStrategy

logger = logging.getLogger(__name__)

BENEFICIARY_PATTERN = r"Nombre del Beneficiario\s(.+?)\sN"
DATE_PATTERN = r"(\d{1,2}\s\w+\s\d{4})\s-\s(\d{2}:\d{2}\s[ap]\.\sm\.)"
BANK_EMAIL = "notificaciones@yape.pe"
YAPE_DATE_FORMAT = "%d %B %Y - %I:%M %p"


class YapeEmailStrategy(EmailStrategy):
    BANK_NAME = "BCP"

    async def read_messages(
        self, midnight_today, now, refresh_token, sub, headers, db
    ) -> list[dict[str, float | str]]:
        try:
            search_response = await self.search_by_date_range(
                BANK_EMAIL,
                midnight_today,
                now,
                refresh_token,
                db,
                sub,
                headers,
            )

            movements_list: list[dict[str, float | str]] = []

            messages_list: list = search_response.json().get("messages", [])

            if not messages_list:
                return []

            await _iterate_messages(self, messages_list, movements_list, headers)

            return movements_list
        except Exception as e:
            logger.warning(e)
            return []


async def _iterate_messages(
    self: YapeEmailStrategy,
    messages_list,
    movements_list: list[dict[str, float | str]],
    headers: dict[str, str],
):
    async with httpx.AsyncClient() as client:
        for message in messages_list:
            try:
                dict_to_send = self.create_movement_dict()
                message_id = message["id"]
                message_response = await client.get(
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
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                logger.warning(
                    f"Network error processing message {message.get('id', 'unknown')}: {e}"
                )
                continue
            except (UnicodeDecodeError, binascii.Error) as e:
                logger.warning(
                    f"Decode error processing message {message.get('id', 'unknown')}: {e}"
                )
                continue
            except Exception as e:
                logger.error(
                    f"Unexpected error processing message {message.get('id', 'unknown')}: {e}"
                )
                continue


def _find_date(
    self: YapeEmailStrategy, cleaned_text: str, dict_to_send: dict[str, float | str]
):
    if date_regex := re.search(DATE_PATTERN, cleaned_text):
        date = date_regex.group()
        date = date.replace("a. m.", "AM").replace("p. m.", "PM")
        self.format_date(date, YAPE_DATE_FORMAT, dict_to_send)
    else:
        dict_to_send["date"] = ""
