import os
import re
import httpx
from abc import ABC, abstractmethod
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from models import Users

WEB_CLIENT_ID = os.environ.get("WEB_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
AMOUNT_PATTERN = r"(\d+\.?\d{0,2})\s"

class EmailStrategy(ABC):
    
    @abstractmethod
    async def process_messages(
        self, after: str, before: str, refresh_token: str, sub: str, headers: dict, db: AsyncSession
    ) -> list[dict]:
        pass
    
    async def ask_google(
        self, bank_email: str, after: str, before: str, refresh_token: str, 
        db: AsyncSession, sub: str, headers: dict
    ) -> httpx.Response:
        query = f"(from:{bank_email} after:{after} before:{before})"
        return await self.search_messages(query, headers, refresh_token, db, sub)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    )
    async def search_messages(
        self, query: str, headers: dict, refresh_token: str, db: AsyncSession, sub: str
    ) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            search_response = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                params={"q": query},
                headers=headers,
                timeout=10.0
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
            
            stmt = update(Users).where(Users.sub == sub).values(access_token=access_token)
            await db.execute(stmt)
            await db.commit()
            
            headers["Authorization"] = f"Bearer {access_token}"
    
    def find_amount(self, cleaned_text: str, dict_to_send: dict) -> None:
        if match := re.search(AMOUNT_PATTERN, cleaned_text):
            dict_to_send["amount"] = -float(match.group(1))
        else:
            dict_to_send["amount"] = 0
    
    def find_beneficiary(self, cleaned_text: str, dict_to_send: dict, pattern: str) -> None:
        if match := re.search(pattern, cleaned_text):
            dict_to_send["beneficiary"] = match.group(1)
        else:
            dict_to_send["beneficiary"] = ""