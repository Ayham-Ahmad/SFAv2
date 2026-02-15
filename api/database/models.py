import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    modify_key = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)
    ui_prefs = Column(JSON, default=dict)
    
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    user_created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company_id = Column(Integer, ForeignKey("companies.company_id"))

    user_company = relationship("Company", back_populates="managers")
    active_sessions = relationship("Session", back_populates="user_session")
    modifications = relationship("Modification", back_populates="actor")

class Company(Base):
    __tablename__ = "companies"

    company_id = Column(Integer, primary_key=True, index=True)
    modify_key = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String, unique=True, index=True)
    plan = Column(String, default="free")
    settings = Column(JSON, default=dict)
    databases_count = Column(Integer, default=0)
    total_tables_count = Column(Integer, default=0)
    total_storage_mb = Column(Float, default=0)
    managers_count = Column(Integer, default=0)
    company_created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    managers = relationship("User", back_populates="user_company")
    tents = relationship("TentDatabase", back_populates="db_company")

class TentDatabase(Base):
    __tablename__ = "tents"

    db_id = Column(Integer, primary_key=True, index=True)
    modify_key = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    db_name = Column(String, index=True) 
    db_type = Column(String)

    connection_config = Column(JSON, nullable=True)

    cached_schema = Column(JSON, nullable=True, default=list) 
    last_synced = Column(DateTime, nullable=True)
    
    is_connected = Column(Boolean, default=False)
    last_ping = Column(DateTime, nullable=True)
    
    is_active = Column(Boolean, default=True)
    db_created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company_id = Column(Integer, ForeignKey("companies.company_id"))
    db_company = relationship("Company", back_populates="tents")

class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean, default=True)
    session_created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    session_ended_at = Column(DateTime, nullable=True)

    user_id = Column(Integer, ForeignKey("users.user_id"))

    user_session = relationship("User", back_populates="active_sessions")
    interactions = relationship("Interaction", back_populates="session")

class Interaction(Base):
    __tablename__ = "interactions"

    interaction_id = Column(Integer, primary_key=True, index=True)
    interaction_content = Column(JSON, nullable=True)
    agent_steps = Column(JSON, nullable=True)
    
    model_used = Column(String, nullable=True)
    status = Column(String, default="pending")
    cost = Column(Float, default=0.0)
    user_feedback = Column(Boolean, nullable=True)
    
    response_time = Column(Float, nullable=True)
    token_count = Column(Integer, nullable=True)
    api_call_count = Column(Integer, nullable=True)
    memory_usage = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session_id = Column(Integer, ForeignKey("sessions.session_id"))
    session = relationship("Session", back_populates="interactions")

class Modification(Base):
    __tablename__ = "modifications"

    modify_id = Column(Integer, primary_key=True, index=True)
    modify_key = Column(String, index=True)
    table_name = Column(String)
    action_type = Column(String) 
    previous_value = Column(JSON, nullable=True)
    snapshot = Column(JSON, nullable=True)
    is_last_modified = Column(Boolean, default=True)
    modified_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True, index=True)

    actor = relationship("User", back_populates="modifications")