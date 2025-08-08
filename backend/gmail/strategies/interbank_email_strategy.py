from gmail.strategies.email_strategy_interface import EmailStrategy
from bs4 import BeautifulSoup
from typing import Match, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import requests, re, base64, logging

logger = logging.getLogger(__name__)


class InterbankEmailStrategy(EmailStrategy):
    async def process_messages(
        self, after, before, refresh_token, sub, headers, db: AsyncSession
    ) -> list[dict]:
        try:
            search_response = await self.ask_google(
                "servicioalcliente@netinterbank.com.pe",
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

            _iterate_messages(messages_list, headers, movements_list)

            return movements_list
        except Exception as e:
            logger.warning(e)
            return []


def _iterate_messages(messages_list, headers, movements_list: list[dict]) -> str | None:
    for message in messages_list:
        dict_to_send: dict[str, float | str] = {
            "date": "",
            "amount": 0.0,
            "category": "",
            "title": "",
            "note": "",
            "beneficiary": "",
            "account": "Interbank",
        }
        message_id = message["id"]
        message_response = requests.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            headers=headers,
        )
        full_message = message_response.json()
        payload = full_message.get("payload", {})

        message_body_coded = _get_html_body_data(payload)

        message_body_decoded = base64.urlsafe_b64decode(
            message_body_coded + "=" * (-len(message_body_coded) % 4)
        )
        decoded_html = message_body_decoded.decode("utf-8")

        soup = BeautifulSoup(decoded_html, "lxml")
        body_message_text = soup.get_text(separator=" ")
        cleaned_text = " ".join(body_message_text.split())

        _find_amount(cleaned_text, dict_to_send)
        _find_date(cleaned_text, dict_to_send)
        _find_beneficiary(cleaned_text, dict_to_send)
        movements_list.append(dict_to_send)


def _get_html_body_data(payload):
    """
    Recorre recursivamente la estructura MIME del mensaje para encontrar
    la primera parte con mimeType = 'text/html' y que contenga 'body.data'.
    """
    if payload.get("mimeType") == "text/html" and "data" in payload.get("body", {}):
        return payload["body"]["data"]

    for part in payload.get("parts", []):
        result = _get_html_body_data(part)
        if result:
            return result
    return ""


def _find_amount(cleaned_text, dict_to_send):
    amount_match = re.search(r"\d+\.\d+", cleaned_text)

    if amount_match:
        amount_regex: float = float(amount_match.group())
    else:
        raise ValueError("No se encontró un número decimal en el texto limpio.")
    dict_to_send["amount"] = -amount_regex


def _find_date(cleaned_text, dict_to_send):
    date_match = re.search(r"\d{1,2}\s\w+\s\d{4}\s\d{1,2}:\d{2}\s[AP]M", cleaned_text)

    if date_match:
        date_regex: str = date_match.group()
    else:
        raise ValueError("No se encontró la fecha en el texto limpio.")

    date_parts = date_regex.split()
    date_parts[1] = date_parts[1].lower()  # Solo el mes (segunda palabra)
    date_regex_fixed = " ".join(date_parts)
    dt = datetime.strptime(date_regex_fixed, "%d %b %Y %I:%M %p")
    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
    dict_to_send["date"] = formatted_time


def _find_beneficiary(cleaned_text, dict_to_send):
    beneficiary_regex: Match[str] | None = re.search(
        r"Destinatario:\s(.+?)\sDestino:", cleaned_text
    )
    if beneficiary_regex:
        beneficiary: str | Any = beneficiary_regex.group(1)
    else:
        beneficiary = ""
    dict_to_send["beneficiary"] = beneficiary
