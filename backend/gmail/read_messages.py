from fastapi import HTTPException, APIRouter, Depends, Header
from datetime import datetime
from logging import Logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from gmail.strategies.email_strategy_interface import EmailStrategy
from gmail.strategies.yape_email_strategy import YapeEmailStrategy
from gmail.strategies.interbank_email_strategy import InterbankEmailStrategy
from gmail.strategies.scotiabank_email_strategy import ScotiabankEmailStrategy
from gmail.strategies.bcp_email_strategy import BcpEmailStrategy
from models import Users
from pathlib import Path
from models import Beneficiaries
from groq import Groq
from helpers.csv_generator import generate_csv
from sqlalchemy import insert
import logging, os, jwt, tempfile, uuid


router: APIRouter = APIRouter()
WEB_CLIENT_ID: str | None = os.environ.get("WEB_CLIENT_ID")
JWT_SECRET_KEY: str | None = os.environ.get("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"

logger: Logger = logging.getLogger(__name__)


@router.get("/gmail/read-messages")
async def read_messages(
    authorization: str = Header(),
    device_time: str = Header(alias="Device-Time"),
    db: AsyncSession = Depends(get_db),
) -> str:
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")

        session_token = authorization.replace("Bearer ", "")

        payload = jwt.decode(
            session_token,
            JWT_SECRET_KEY,
            [JWT_ALGORITHM],
        )

        user_sub = payload.get("sub")

        access_token, refresh_token = await _get_tokens_by_sub(user_sub, db)

        headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}

        after, before = _get_time(device_time)

        original_list = await _iterate_strategies(
            after, before, refresh_token, user_sub, headers, db
        )

        list_processed = await process_messages(original_list, db)

        return list_processed

    except ValueError:
        logger.error("Token inválido")
        raise HTTPException(status_code=401, detail=f"Token inválido.")
    except Exception as e:
        logger.critical(f"Error desconocido: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error desconocido.")


async def process_messages(original_list, db: AsyncSession) -> str:
    def assign_category(obj):
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

        prompt = f"""
        Eres un experto en categorización de transacciones bancarias.
        Responde solo con una de las siguientes categorías:
        Comida
        Comestibles
        Compras
        Transporte
        Entretenimiento
        Facturas y tarifas
        Regalos
        Belleza
        Trabajo
        Viajes
        Ingreso

        Tu tarea es analizar esta transacción y devolver la categoría más apropiada.
        Transacción:
        Monto: {obj["amount"]}
        Beneficiario: {obj["beneficiary"]}

        Responde solo con una de las categorías listadas arriba. No modifiques el nombre de la categoría.
        """

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], model="llama-3.1-8b-instant"
        )

        return chat_completion.choices[0].message.content

    async def obtain_category(obj, db: AsyncSession):
        try:
            result = await db.execute(
                select(Beneficiaries.category).where(
                    Beneficiaries.name == obj["beneficiary"]
                )
            )
            beneficiary = result.scalar_one_or_none()
        except Exception as e:
            print(f"DB error: {e}")
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

    def cleanup():
        try:
            if csv_path.exists():
                csv_path.unlink()
        except Exception as e:
            print(f"Error cleaning up {csv_path}: {e}")

    try:
        temp_dir = Path(tempfile.gettempdir())
        temp_dir.mkdir(exist_ok=True)
        csv_filename = f"gastos_{uuid.uuid4().hex}.csv"
        csv_path = temp_dir / csv_filename

        for obj in original_list:
            category = await obtain_category(obj, db)
            obj["category"] = category

        return generate_csv(original_list, str(csv_path))

    except Exception as e:
        cleanup()
        raise HTTPException(status_code=500, detail=str(e))


def _get_time(device_time: str) -> tuple[int, int]:
    now = datetime.strptime(device_time, "%Y-%m-%d %H:%M:%S")

    midnight_today: datetime = now.replace(hour=0, minute=0, second=0)

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
    tokens = result.fetchone()
    if tokens:
        return tokens[0], tokens[1]
    else:
        return None, None


async def _iterate_strategies(
    after, before, refresh_token, sub, headers, db
) -> list[dict]:
    movements_list: list[dict] = []
    strategies: list[EmailStrategy] = [
        InterbankEmailStrategy(),
        YapeEmailStrategy(),
        ScotiabankEmailStrategy(),
        BcpEmailStrategy(),
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
