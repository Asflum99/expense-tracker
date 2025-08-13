import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from gmail.services.auth_service import authenticate_user
from gmail.services.csv_service import create_csv_response
from gmail.services.gmail_service import fetch_and_process_messages
from gmail.services.time_service import get_time_range

router: APIRouter = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/gmail/get-gmail-messages")
async def get_gmail_messages(
    authorization: str = Header(),
    device_time: str = Header(alias="Device-Time"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    try:
        user_sub, access_token, refresh_token = await authenticate_user(
            authorization, db
        )
        midnight_today, now = get_time_range(device_time)
        movements = await fetch_and_process_messages(
            midnight_today, now, access_token, refresh_token, user_sub, db
        )
        return create_csv_response(movements)

    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error desconocido.")
