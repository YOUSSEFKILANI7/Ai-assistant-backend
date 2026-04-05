from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.Config import settings
from app.Firebase_admin import initialize_firebase
from app.routes import auth, guardian, raspberry_pi
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="AI Assistant API with Firestore",
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials="*" not in settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    initialize_firebase()
    logger.info("🚀 Server started")
    print("\n" + "="*60)
    print("🚀 AI Assistant API - Server Started!")
    print("="*60)
    print(f"📖 Docs: http://localhost:8000/docs")
    print(f"🔥 Firebase: Connected")
    print(f"💾 Database: Firestore")
    print(f"🔐 Auth: Firebase Auth")
    print("="*60 + "\n")

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(guardian.router, prefix=settings.API_V1_PREFIX)
app.include_router(raspberry_pi.router, prefix=settings.API_V1_PREFIX)

@app.get("/")
async def root():
    return {
        "message": "AI Assistant API",
        "version": "1.0.0",
        "database": "Firestore",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
