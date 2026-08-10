from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime
from app.core.database import Base

class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # success, warning, error
    summary = Column(Text, nullable=True)
    decisions = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    estimated_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), index=True, nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
