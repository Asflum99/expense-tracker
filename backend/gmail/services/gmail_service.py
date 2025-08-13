import logging

from fastapi import HTTPException
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from gmail.services.categorization.categorization_service import assign_category
from gmail.strategies.bcp import BcpEmailStrategy
from gmail.strategies.interbank import InterbankEmailStrategy
from gmail.strategies.interface import EmailStrategy
from gmail.strategies.scotiabank import ScotiabankEmailStrategy
from gmail.strategies.yape import YapeEmailStrategy
from models import Beneficiaries

logger = logging.getLogger(__name__)


async def _get_cached_category(beneficiary_name: str, db: AsyncSession):
    result = await db.execute(
        select(Beneficiaries.category).where(Beneficiaries.name == beneficiary_name)
    )
    return result.scalar_one_or_none()


async def _save_category(beneficiary_name: str, category: str, db: AsyncSession):
    await db.execute(
        insert(Beneficiaries).values(name=beneficiary_name, category=category)
    )


async def _obtain_category(movement: dict[str, float | str], db: AsyncSession):
    try:
        beneficiary_name = str(movement["beneficiary"])

        if cached_category := await _get_cached_category(beneficiary_name, db):
            return cached_category

        # Si no existe, crear nueva
        category = assign_category(movement)
        await _save_category(beneficiary_name, category, db)
        return category

    except Exception as e:
        logger.error(f"DB error: {e}")
        raise


async def _categorize_movements(
    movements: list[dict[str, float | str]], db: AsyncSession
):
    try:
        for movement in movements:
            category = await _obtain_category(movement, db)
            movement["category"] = category

        await db.commit()
        return movements

    except Exception as e:
        logger.error(f"Error categorizing movements: {e}")
        await db.rollback()
        raise


async def fetch_and_process_messages(
    midnight_today: str,
    now: str,
    access_token: str,
    refresh_token: str,
    user_sub: str,
    db: AsyncSession,
):
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        movements: list[dict[str, float | str]] = []

        strategies: list[EmailStrategy] = [
            BcpEmailStrategy(),
            InterbankEmailStrategy(),
            YapeEmailStrategy(),
            ScotiabankEmailStrategy(),
        ]

        for strategy in strategies:
            try:
                dicts_to_add = await strategy.read_messages(
                    midnight_today, now, refresh_token, user_sub, headers, db
                )
                if dicts_to_add:
                    movements.extend(dicts_to_add)
            except Exception as e:
                logger.warning(f"Strategy {strategy.__class__.__name__} failed: {e}")
                continue

        return await _categorize_movements(movements, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Critical error in fetch_and_process_messages: {e}")
        raise HTTPException(status_code=500, detail="Error processing messages")
