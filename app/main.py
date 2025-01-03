from fastapi import FastAPI
from .routers import banking
from .models import models
from .database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Banking API")

app.include_router(banking.router, prefix="/api/v1", tags=["banking"]) 