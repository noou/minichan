from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./minichan.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    image = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    bumped_at = Column(DateTime, default=datetime.utcnow)

    posts = relationship("Post", back_populates="thread", cascade="all, delete-orphan")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False)
    content = Column(Text, nullable=False)
    image = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    thread = relationship("Thread", back_populates="posts")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)