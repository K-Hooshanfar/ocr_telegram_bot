import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from jose import jwt
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .auth import get_password_hash
from .config import settings
from .database import Base, SessionLocal, engine
from .logger import logger
from .models import User
from .routes import ocr, user


def create_initial_data() -> None:
    """Seed the database with an admin and test user if they don't exist."""
    db: Session = SessionLocal()
    users_to_seed = [
        {
            "username": settings.ADMIN_USER,
            "password": settings.ADMIN_PASS,
            "is_admin": True,
            "is_active": True,
            "credits": 100_000,
        },
        {
            "username": "test",
            "password": "test123",
            "is_admin": False,
            "is_active": True,
            "credits": 15,
        },
    ]

    for u in users_to_seed:
        if not db.query(User).filter(User.username == u["username"]).first():
            db.add(
                User(
                    username=u["username"],
                    hashed_password=get_password_hash(u["password"]),
                    is_admin=u["is_admin"],
                    is_active=u["is_active"],
                    credits=u["credits"],
                )
            )

    db.commit()
    db.close()


app = FastAPI(
    title="OCR API",
    description="Gemini-powered OCR REST API with JWT auth, credit system, and Telegram bot integration.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "OCR API"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    user_identifier = "anonymous"
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            user_identifier = payload.get("sub", user_identifier)
        except Exception:
            pass

    response = await call_next(request)
    logger.info(
        "%s %s — user=%s status=%s",
        request.method,
        request.url.path,
        user_identifier,
        response.status_code,
    )
    return response


@app.on_event("startup")
def on_startup():
    max_retries = 10
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            create_initial_data()
            logger.info("Database ready and initial data seeded.")
            break
        except OperationalError as e:
            logger.warning(
                "Database connection failed (attempt %s/%s): %s",
                attempt,
                max_retries,
                e,
            )
            time.sleep(2)
    else:
        logger.error("Could not connect to the database after multiple attempts.")
        raise RuntimeError("Database unavailable")


app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(ocr.router, prefix="/ocr", tags=["OCR"])
