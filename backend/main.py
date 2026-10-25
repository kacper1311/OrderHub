from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel

import models
from database import engine
from services.admin import create_admin_if_missing


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    create_admin_if_missing()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}
