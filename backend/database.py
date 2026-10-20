import os
from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import create_engine, Session

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Brak DATABASE_URL w pliku .env")

engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    with Session(engine) as session:
        yield session

    

