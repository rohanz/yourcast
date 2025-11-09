import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.episodes import router as episodes_router
from app.api.users import router as users_router
from app.database.connection import engine
from app.models import Base
from app.config import settings

app = FastAPI(
    title="YourCast API",
    description="API for generating micro-podcasts from news articles",
    version="0.1.0",
)

from app.config import config

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create storage directory and mount static files
print(f"DEBUG: STORAGE_DIR environment variable: {os.getenv('STORAGE_DIR', 'NOT SET')}")
print(f"DEBUG: settings.storage_dir value: {settings.storage_dir}")
print(f"DEBUG: Current working directory: {os.getcwd()}")
os.makedirs(settings.storage_dir, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.storage_dir), name="storage")

# Database initialization is deferred to /init endpoint to avoid startup failures

app.include_router(episodes_router, prefix="/episodes", tags=["episodes"])
app.include_router(users_router, prefix="/users", tags=["users"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/init")
def init_database():
    """Initialize database tables. Call this endpoint after deployment."""
    try:
        from app.database.connection import get_engine
        from sqlalchemy import inspect
        engine = get_engine()
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        if not existing_tables or 'episodes' not in existing_tables:
            print("Creating database tables...")
            Base.metadata.create_all(bind=engine)
            return {"status": "success", "message": "Database tables created"}
        else:
            return {"status": "success", "message": "Database tables already exist"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)