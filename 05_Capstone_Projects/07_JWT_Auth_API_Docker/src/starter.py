"""
JWT Auth API — Starter Scaffold
================================
Complete the TODO blocks to build a working JWT authentication API.

Routes:
  POST /register  — create a new user
  POST /login     — verify credentials, return JWT
  GET  /me        — protected: decode JWT, return current user
  GET  /health    — health check (no auth required)

Dependencies (requirements.txt):
  fastapi==0.111.0
  uvicorn[standard]==0.29.0
  sqlalchemy==2.0.30
  psycopg2-binary==2.9.9
  PyJWT==2.8.0
  bcrypt==4.1.3
  python-dotenv==1.0.1
  pydantic==2.7.1
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

# ── Configuration ────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")          # injected by Docker Compose
SECRET_KEY = os.getenv("SECRET_KEY")              # injected by Docker Compose
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# ── Database setup ────────────────────────────────────────────────────────────

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)


Base.metadata.create_all(bind=engine)  # creates table if it doesn't exist


def get_db():
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


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="JWT Auth API")
security = HTTPBearer()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    # TODO: Hash user.password with bcrypt
    # TODO: Create a UserModel with username and hashed_password
    # TODO: Add to db, commit, handle IntegrityError (duplicate username → 400)
    # TODO: Return {"message": "User registered successfully", "username": user.username}
    pass


@app.post("/login", response_model=TokenResponse)
def login(user: UserCreate, db: Session = Depends(get_db)):
    # TODO: Query db for UserModel where username == user.username
    # TODO: If not found or password doesn't match bcrypt hash → raise 401
    # TODO: Create JWT payload: {"sub": username, "exp": now + timedelta(minutes=...)}
    # TODO: Encode with jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    # TODO: Return TokenResponse(access_token=token)
    pass


@app.get("/me")
def me(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    # TODO: Decode credentials.credentials with jwt.decode(...)
    # TODO: Handle jwt.ExpiredSignatureError → raise 401 "Token expired"
    # TODO: Handle jwt.InvalidTokenError → raise 401 "Invalid token"
    # TODO: Extract username from payload["sub"]
    # TODO: Query db for the user, return {"id": ..., "username": ...}
    pass
