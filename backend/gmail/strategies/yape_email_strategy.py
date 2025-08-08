from gmail.strategies.email_strategy_interface import EmailStrategy
from typing import Match, Any
from helpers.parse_date_multilocale import parse_date_multilocale
import requests, re, base64, logging

logger = logging.getLogger(__name__)


class YapeEmailStrategy(EmailStrategy):
    async def process_messages(
        self, after, before, refresh_token, sub, headers, db
    ) -> list[dict]:
        try:
            search_response = await self.ask_google(
                "notificaciones@yape.pe",
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
                    "account": "BCP",
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

                message_body_decoded = base64.urlsafe_b64decode(message_body).decode(
                    "utf-8"
                )

                amount_regex: Match[str] | None = re.search(
                    r"\d+\.\d+", message_body_decoded
                )
                if amount_regex:
                    amount: float = float(amount_regex.group())
                    dict_to_send["amount"] = -amount

                date_regex: Match[str] | None = re.search(
                    r"(\d{1,2}\s\w+\s\d{4})\s-\s(\d{2}:\d{2}\s[ap]\.\sm\.)",
                    message_body_decoded,
                )
                if date_regex:
                    date = date_regex.group()
                    dt = parse_date_multilocale(date, "%d %B %Y - %I:%M %p")
                    formatted = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
                    dict_to_send["date"] = formatted

                beneficiary_regex: Match[str] | None = re.search(
                    r"Nombre del Beneficiario\s([^\r\n]+)", message_body_decoded
                )
                if beneficiary_regex:
                    beneficiary: str = str(beneficiary_regex.group(1))
                    dict_to_send["beneficiary"] = beneficiary

                movements_list.append(dict_to_send)

            return movements_list
        except Exception as e:
            logger.warning(e)
            return []
