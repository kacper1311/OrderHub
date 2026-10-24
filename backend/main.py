from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel

import models
from database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}
