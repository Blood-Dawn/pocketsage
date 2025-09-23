from sqlmodel import SQLModel, create_engine, Session
import os

def get_engine():
    url = os.getenv("DATABASE_URL", "sqlite:///pocketsage.db")
    engine = create_engine(url, echo=False)
    return engine

def init_db():
    engine = get_engine()
    SQLModel.metadata.create_all(engine)

def get_session():
    engine = get_engine()
    return Session(engine)
