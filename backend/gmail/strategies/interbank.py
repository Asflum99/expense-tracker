import base64
import binascii
import logging
import re

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from gmail.strategies.interface import EmailStrategy

logger = logging.getLogger(__name__)

BANK_EMAIL = "servicioalcliente@netinterbank.com.pe"
BENEFICIARY_PATTERN = r"Destinatario:\s(.+?)\sDestino:"
DATE_PATTERN = r"\d{1,2}\s\w+\s\d{4}\s\d{1,2}:\d{2}\s[AP]M"
INTERBANK_DATE_FORMAT = "%d %b %Y %I:%M %p"


class InterbankEmailStrategy(EmailStrategy):
    BANK_NAME = "Interbank"

    async def read_messages(
        self, midnight_today, now, refresh_token, sub, headers, db: AsyncSession
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

            messages_list: list = search_response.json().get("messages")

            if not messages_list:
                return []

            await _iterate_messages(self, messages_list, headers, movements_list)

            return movements_list
        except Exception as e:
            logger.warning(e)
            return []


async def _iterate_messages(
    self: InterbankEmailStrategy,
    messages_list,
    headers: dict[str, str],
    movements_list: list[dict[str, float | str]],
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
    self: InterbankEmailStrategy,
    cleaned_text: str,
    dict_to_send: dict[str, float | str],
) -> None:
    if match := re.search(DATE_PATTERN, cleaned_text):
        date_regex = match.group()
        self.format_date(date_regex, INTERBANK_DATE_FORMAT, dict_to_send)
    else:
        dict_to_send["date"] = ""
