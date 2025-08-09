from gmail.strategies.interface import EmailStrategy
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import requests, re, base64, logging

logger = logging.getLogger(__name__)

BANK_EMAIL = "servicioalcliente@netinterbank.com.pe"
BENEFICIARY_PATTERN = r"Destinatario:\s(.+?)\sDestino:"
DATE_PATTERN = r"\d{1,2}\s\w+\s\d{4}\s\d{1,2}:\d{2}\s[AP]M"
BANK_NAME = "Interbank"


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

        self.find_amount(cleaned_text, dict_to_send)
        _find_date(cleaned_text, dict_to_send)
        self.find_beneficiary(cleaned_text, dict_to_send, BENEFICIARY_PATTERN)
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


def _find_date(cleaned_text: str, dict_to_send: dict[str, float | str]) -> None:
    date_match = re.search(DATE_PATTERN, cleaned_text)

    if date_match:
        date_regex: str = date_match.group()
    else:
        raise ValueError("No se encontró la fecha en el texto limpio.")

    date_parts = date_regex.split()
    date_parts[1] = date_parts[1].lower()
    date_regex_fixed = " ".join(date_parts)
    dt = datetime.strptime(date_regex_fixed, "%d %b %Y %I:%M %p")
    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
    dict_to_send["date"] = formatted_time
