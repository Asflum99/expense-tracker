import re
from abc import ABC, abstractmethod
from datetime import datetime

import httpx
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from models import Users

WEB_CLIENT_ID = settings.web_client_id
CLIENT_SECRET = settings.client_secret
AMOUNT_PATTERN = r"S\/\s*(\d+\.?\d{0,2})"
FORMAT_TIME = "%Y-%m-%d %H:%M:%S.%f"  # Formato que pide Cashew


class EmailStrategy(ABC):
    BANK_NAME = ""

    @abstractmethod
    async def read_messages(
        self,
        midnight_today: str,
        now: str,
        refresh_token: str,
        sub: str,
        headers: dict[str, str],
        db: AsyncSession,
    ) -> list[dict[str, float | str]]:
        pass

    def create_movement_dict(self) -> dict[str, float | str]:
        return {
            "date": "",
            "amount": 0.0,
            "category": "",
            "title": "",
            "note": "",
            "beneficiary": "",
            "account": self.BANK_NAME,
        }

    async def search_by_date_range(
        self,
        bank_email: str,
        midnight_today: str,
        now: str,
        refresh_token: str,
        db: AsyncSession,
        sub: str,
        headers: dict[str, str],
    ) -> httpx.Response:
        query = f"(from:{bank_email} after:{midnight_today} before:{now})"
        return await self.gmail_search(query, headers, refresh_token, db, sub)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    )
    async def gmail_search(
        self, query: str, headers: dict, refresh_token: str, db: AsyncSession, sub: str
    ) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            search_response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                params={"q": query},
                headers=headers,
                timeout=10.0,
            )

            if search_response.status_code == 401:
                await self.update_access_token(refresh_token, db, sub, headers)
                raise httpx.RequestError("Token expired, retrying")
            elif search_response.status_code != 200:
                raise httpx.RequestError(f"HTTP {search_response.status_code}")

            return search_response

    async def update_access_token(
        self, refresh_token: str, db: AsyncSession, sub: str, headers: dict
    ) -> None:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": WEB_CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)

            if response.status_code != 200:
                raise Exception(f"Error al refrescar token: {response.text}")

            access_token = response.json().get("access_token")

            stmt = (
                update(Users).where(Users.sub == sub).values(access_token=access_token)
            )
            await db.execute(stmt)
            await db.commit()

            headers["Authorization"] = f"Bearer {access_token}"

    def find_amount(
        self, cleaned_text: str, dict_to_send: dict[str, float | str]
    ) -> None:
        if match := re.search(AMOUNT_PATTERN, cleaned_text):
            dict_to_send["amount"] = -float(match.group(1))
        else:
            dict_to_send["amount"] = 0

    def find_beneficiary(
        self, cleaned_text: str, dict_to_send: dict[str, float | str], pattern: str
    ) -> None:
        if match := re.search(pattern, cleaned_text):
            dict_to_send["beneficiary"] = match.group(1)
        else:
            dict_to_send["beneficiary"] = ""

    def format_date(
        self, date: str, date_format: str, dict_to_send: dict[str, float | str]
    ):
        dt = datetime.strptime(date, date_format)
        formatted_time = dt.strftime(FORMAT_TIME)
        dict_to_send["date"] = formatted_time

    def get_html_body_data(self, payload):
        if payload.get("mimeType") == "text/html" and "data" in payload.get("body", {}):
            return payload["body"]["data"]

        for part in payload.get("parts", []):
            result = self.get_html_body_data(part)
            if result:
                return result
        return ""
