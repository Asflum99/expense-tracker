from abc import ABC, abstractmethod
from requests import Response
from sqlalchemy import update
from models import Users
from sqlalchemy.ext.asyncio import AsyncSession
import requests, os

WEB_CLIENT_ID: str | None = os.environ.get("WEB_CLIENT_ID")
CLIENT_SECRET: str | None = os.environ.get("CLIENT_SECRET")


class EmailStrategy(ABC):

    @abstractmethod
    async def process_messages(
        self, after, before, refresh_token, sub, headers, db
    ) -> list[dict]:
        pass

    async def ask_google(
        self, bank_email, after, before, refresh_token, db, sub, headers
    ) -> Response:
        query = f"(from:{bank_email} after:{after} before:{before})"

        while True:
            search_response = requests.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                params={"q": query},
            )

            if search_response.status_code == 200:
                return search_response
            else:
                await self.update_access_token(refresh_token, db, sub, headers)
            pass

    async def update_access_token(
        self, refresh_token, db: AsyncSession, sub, headers
    ) -> None:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": WEB_CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        response = requests.post(token_url, data)
        if response.status_code != 200:
            raise Exception(f"Error al refrescar token: {response.text}")

        access_token = response.json().get("access_token")

        # Actualiza el token en la DB
        stmt = update(Users).where(Users.sub == sub).values(access_token=access_token)
        await db.execute(stmt)
        await db.commit()

        # Reemplaza el header sin redeclarar
        headers["Authorization"] = f"Bearer {access_token}"
