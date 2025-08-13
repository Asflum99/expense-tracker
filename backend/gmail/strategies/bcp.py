import base64
import binascii
import logging
import re

import httpx
from bs4 import BeautifulSoup

from gmail.strategies.interface import EmailStrategy

logger = logging.getLogger(__name__)

BENEFICIARY_PATTERN = r"Empresa\s(.+?)\sNúmero"
DATE_PATTERN = r"\d{1,2}\sde\s\w+\sde\s\d{4}\s-\s\d{2}:\d{2}\s[AP]M"
BANK_EMAIL = "notificaciones@notificacionesbcp.com.pe"
BANK_NAME = "BCP"
BCP_DATE_FORMAT = "%d de %B de %Y - %H:%M %p"


class BcpEmailStrategy(EmailStrategy):
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

            await _iterate_messages(self, messages_list, headers, movements_list)

            return movements_list
        except Exception as e:
            logger.warning(e)
            return []


async def _iterate_messages(
    self: BcpEmailStrategy, messages_list, headers: dict[str, str], movements_list: list[dict[str, float | str]]
):
    async with httpx.AsyncClient() as client:
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
                message_response = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                    headers=headers,
                    timeout=10.0,
                )
                
                if message_response.status_code != 200:
                    logger.warning(f"Error fetching message {message_id}: {message_response.status_code}")
                    continue
                
                payload = message_response.json().get("payload", {})
                message_body = self.get_html_body_data(payload)
                message_body_decoded = base64.urlsafe_b64decode(
                    message_body + "=" * (-len(message_body) % 4)
                )
                decoded_html = message_body_decoded.decode("utf-8")
                soup = BeautifulSoup(decoded_html, "lxml")
                body_message_text = soup.get_text(separator=" ")
                cleaned_text = " ".join(body_message_text.split())
                
                if "Realizaste un consumo" in cleaned_text:
                    self.find_amount(cleaned_text, dict_to_send)
                    self.find_beneficiary(cleaned_text, dict_to_send, BENEFICIARY_PATTERN)
                    _find_date(self, cleaned_text, dict_to_send)
                    movements_list.append(dict_to_send)
                    
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                logger.warning(f"Network error processing message {message.get('id', 'unknown')}: {e}")
                continue
            except (UnicodeDecodeError, binascii.Error) as e:
                logger.warning(f"Decode error processing message {message.get('id', 'unknown')}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing message {message.get('id', 'unknown')}: {e}")
                continue


def _find_date(self: BcpEmailStrategy, cleaned_text: str, dict_to_send: dict[str, float | str]):
    if match := re.search(DATE_PATTERN, cleaned_text):
        date = match.group()
        self.format_date(date, BCP_DATE_FORMAT, dict_to_send)
    else:
        dict_to_send["date"] = ""
