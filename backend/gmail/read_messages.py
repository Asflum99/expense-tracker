import csv
import io
import logging
import os
from datetime import datetime
from io import StringIO

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from groq import Groq
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from gmail.strategies.bcp import BcpEmailStrategy
from gmail.strategies.interbank import InterbankEmailStrategy
from gmail.strategies.interface import EmailStrategy
from gmail.strategies.scotiabank import ScotiabankEmailStrategy
from gmail.strategies.yape import YapeEmailStrategy
from models import Beneficiaries, Users
from config import Settings

router: APIRouter = APIRouter()
WEB_CLIENT_ID = Settings.web_client_id
JWT_SECRET_KEY = Settings.jwt_secret_key
GROQ_API_KEY = Settings.groq_api_key
AI_MODEL = "openai/gpt-oss-20b"
JWT_ALGORITHM = "HS256"
PROMPT_TEMPLATE = "categorization_prompt.md"

logger = logging.getLogger(__name__)


@router.get("/gmail/read-messages")
async def read_messages(
    authorization: str = Header(),
    device_time: str = Header(alias="Device-Time"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    try:
        user_sub = _extract_user_sub(authorization)
        access_token, refresh_token = await _get_tokens_by_sub(user_sub, db)
        after, before = _get_time(device_time)
        messages = await _fetch_and_process_messages(
            after, before, access_token, refresh_token, user_sub, db
        )
        return _create_csv_response(messages)

    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Error desconocido: {str(e)}")
        raise HTTPException(status_code=500, detail="Error desconocido.")


async def _process_messages(original_list, db: AsyncSession) -> list:
    async def obtain_category(obj, db: AsyncSession):
        try:
            result = await db.execute(
                select(Beneficiaries.category).where(
                    Beneficiaries.name == obj["beneficiary"]
                )
            )
            beneficiary = result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"DB error: {e}")
            raise

        if beneficiary is not None:
            return beneficiary
        else:
            category = assign_category(obj)
            await db.execute(
                insert(Beneficiaries).values(name=obj["beneficiary"], category=category)
            )
            await db.commit()
            return category

    try:
        for obj in original_list:
            category = await obtain_category(obj, db)
            obj["category"] = category

        return original_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_time(device_time: str) -> tuple[int, int]:
    now = datetime.strptime(device_time, "%Y-%m-%d %H:%M:%S")

    midnight_today = now.replace(hour=0, minute=0, second=0)

    # Convertir a timestamps
    after: int = int(midnight_today.timestamp())
    before: int = int(now.timestamp())

    return after, before


async def _get_tokens_by_sub(
    sub, db: AsyncSession
) -> tuple[str, str] | tuple[None, None]:
    result = await db.execute(
        select(Users.access_token, Users.refresh_token).where(Users.sub == sub)
    )
    if tokens := result.fetchone():
        return tokens[0], tokens[1]
    else:
        logger.error("No se encontraron tokens")
        raise HTTPException(status_code=401, detail="No se encontraron tokens")


async def _iterate_strategies(
    after, before, refresh_token, sub, headers, db
) -> list[dict]:
    movements_list: list[dict] = []
    strategies: list[EmailStrategy] = [
        BcpEmailStrategy(),
        InterbankEmailStrategy(),
        YapeEmailStrategy(),
        ScotiabankEmailStrategy(),
    ]

    for strategy in strategies:
        dicts_to_add = await strategy.process_messages(
            after, before, refresh_token, sub, headers, db
        )
        if not dicts_to_add:
            continue
        for dicts in dicts_to_add:
            movements_list.append(dicts)

    return movements_list


def _generate_csv_content(data: list[dict]) -> str:
    """Genera contenido CSV en memoria"""
    output = StringIO()
    keys = ["Date", "Amount", "Category", "Title", "Note", "Account"]

    writer = csv.writer(output)
    writer.writerow(keys)

    for obj in data:
        writer.writerow(
            [
                obj["date"],
                obj["amount"],
                obj["category"],
                obj["title"],
                obj["note"],
                obj["account"],
            ]
        )

    return output.getvalue()


def load_prompt_template(file_path: str) -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(current_dir, file_path)
    with open(full_path, "r", encoding="utf-8") as file:
        return file.read()


def assign_category(obj: dict) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    prompt_template = load_prompt_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(
        amount=obj["amount"], beneficiary=obj["beneficiary"]
    )
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}], model=AI_MODEL
    )
    if content := chat_completion.choices[0].message.content:
        return content
    else:
        raise ValueError("Error al asignar categoría")


def _extract_user_sub(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    session_token = authorization.removeprefix("Bearer ")
    payload = jwt.decode(session_token, JWT_SECRET_KEY, [JWT_ALGORITHM])
    return payload.get("sub")


async def _fetch_and_process_messages(
    after, before, access_token, refresh_token, user_sub, db
):
    headers = {"Authorization": f"Bearer {access_token}"}
    original_list = await _iterate_strategies(
        after, before, refresh_token, user_sub, headers, db
    )
    return await _process_messages(original_list, db)


def _create_csv_response(processed_list):
    csv_content = _generate_csv_content(processed_list)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=gastos.csv"},
    )
