from fastapi import HTTPException, APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from backend.models import OAuthSession
from sqlalchemy import select, delete

router = APIRouter()

@router.get("/users/auth/status/{session_id}")
async def check_auth_status(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OAuthSession.status).where(OAuthSession.session_id == session_id)
    )
    status = result.scalar_one_or_none()
    
    if status is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if status == "completed":
        await db.execute(
            delete(OAuthSession).where(OAuthSession.session_id == session_id)
        )
        await db.commit()
    
    return {"status": status}