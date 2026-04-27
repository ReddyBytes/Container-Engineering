"""
JWT Auth API — Full Solution
==============================
Complete implementation: register, login, /me protected route.

Routes:
  POST /register  — hash password, store user in PostgreSQL
  POST /login     — verify credentials, return signed JWT
  GET  /me        — decode JWT from Authorization header, return user
  GET  /health    — liveness probe for Docker health check

Run locally (without Docker):
  DATABASE_URL=postgresql://... SECRET_KEY=... uvicorn src.solution:app --reload

Run with Docker Compose:
  docker compose up --build
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
# All values injected at runtime — never hardcoded here.
# In Docker Compose these come from the environment: block in docker-compose.yml.
# In production they come from --env-file or Docker secrets.

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is required")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


# ── Database ──────────────────────────────────────────────────────────────────

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # test connection before using from pool (handles restarts)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)


# Creates the users table if it does not already exist.
# In production you would use Alembic migrations instead.
Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a database session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Return bcrypt hash of plain-text password.

    bcrypt automatically generates a random salt and embeds it in the hash.
    The output is a string like: $2b$12$<22-char-salt><31-char-hash>
    """
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the bcrypt hash. Constant-time comparison."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(username: str) -> str:
    """Encode a JWT with subject claim and expiry.

    The payload {"sub": username, "exp": ...} is signed with SECRET_KEY.
    Anyone with SECRET_KEY can verify the signature — nobody needs a database
    lookup to authenticate a valid token.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT. Raises HTTPException on failure.

    jwt.decode() verifies:
    - Signature (was this token signed with our SECRET_KEY?)
    - Expiry (has the exp claim passed?)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="JWT Auth API", version="1.0.0")
security = HTTPBearer()  # parses "Authorization: Bearer <token>" header


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Liveness probe. Docker HEALTHCHECK polls this endpoint every 30 seconds."""
    return {"status": "ok"}


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user.

    Hashes the password with bcrypt before storage.
    Returns 400 if the username already exists.
    """
    hashed = hash_password(user.password)
    db_user = UserModel(username=user.username, hashed_password=hashed)
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)  # reload to get the generated id
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    return {"message": "User registered successfully", "username": db_user.username}


@app.post("/login", response_model=TokenResponse)
def login(user: UserCreate, db: Session = Depends(get_db)):
    """Authenticate a user and return a signed JWT.

    Uses the same error message for "user not found" and "wrong password"
    to avoid leaking information about which usernames exist.
    """
    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()

    # Deliberate: same 401 for "not found" and "wrong password"
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(db_user.username)
    return TokenResponse(access_token=token)


@app.get("/me", response_model=UserResponse)
def me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Return the currently authenticated user.

    Decodes the JWT from the Authorization header.
    No database lookup happens until the token signature is verified.
    """
    payload = decode_access_token(credentials.credentials)
    username: str = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    db_user = db.query(UserModel).filter(UserModel.username == username).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(id=db_user.id, username=db_user.username)
