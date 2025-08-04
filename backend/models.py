from sqlalchemy import Column, Integer, String, DateTime, func, UniqueConstraint
from database import Base

class OAuthSession(Base):
    __tablename__ = "oauth_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    sub = Column(String, nullable=False)
    code_verifier = Column(String, nullable=False)
    state = Column(String, nullable=False, unique=True)
    session_id = Column(String, nullable=False, unique=True, index=True)  # MEJORADO
    status = Column(String, nullable=False, default="pending")  # MEJORADO
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))  # NUEVO (opcional pero recomendado)

class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    sub = Column(String, unique=True, nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_in = Column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("sub", name="uix_sub"),)

class Beneficiaries(Base):
    __tablename__ = "beneficiaries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)