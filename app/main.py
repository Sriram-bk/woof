from fastapi import FastAPI
from .database import engine
from .models import models
from .routers import banking, auth

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Banking API")

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(banking.router, prefix="/api/v1", tags=["banking"]) 