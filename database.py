from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime, timezone
import uuid
from config import settings

class Base(DeclarativeBase):
    pass

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, default="New Chat")
    status = Column(String, default="planning")  # planning, generating, completed, pushed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    code = Column(Text, nullable=True)
    files_plan = Column(JSON, nullable=True)  # AI battae ga kon kon se files banegi
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    session = relationship("ChatSession", back_populates="messages")

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    name = Column(String, nullable=False)
    files = Column(JSON, nullable=True)  # Store all generated files
    repo_url = Column(String, nullable=True)
    pushed = Column(String, default="no")  # no, yes
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    session = relationship("ChatSession", back_populates="projects")

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()