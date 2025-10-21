from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from jose import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from pathlib import Path
import sqlite3
import os
import json
import logging

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Validate JWT_SECRET
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY or SECRET_KEY == "secret-key":
    logger.warning("⚠️  WARNING: JWT_SECRET not properly configured, using insecure default!")
    SECRET_KEY = "secret-key"
else:
    logger.info("✅ JWT_SECRET configured")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 3

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Initialize password context at module level (more efficient)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database path helper - matches server.py logic
def get_db_path():
    """Get the correct database path based on environment"""
    if os.path.exists("/data"):
        return "/data/handoff.sqlite"
    return str(Path(__file__).parent / "handoff.sqlite")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: int
    tenant_id: int
    email: str
    name: str
    role: str


class UserOut(BaseModel):
    id: int
    tenant_id: int
    email: str
    name: str
    role: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password, hashed_password):
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_email(email: str):
    """Retrieve user from database by email address"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, name, role, password_hash, tenant_id FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "id": row[0],
                "email": row[1],
                "name": row[2],
                "role": row[3],
                "password_hash": row[4],
                "tenant_id": row[5],
            }
        return None
    except sqlite3.OperationalError as e:
        logger.error(f"Database error in get_user_by_email: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_user_by_email: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(**payload)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(required_roles: list):
    def dependency(user: TokenData = Depends(get_current_user)):
        if user.role not in required_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return dependency


def log_event(user_id: int, tenant_id: int, type: str, payload: dict):
    """Log an event to the database"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO events (user_id, tenant_id, type, payload, ts) VALUES (?, ?, ?, ?, datetime('now'))",
            (user_id, tenant_id, type, json.dumps(payload))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log event: {e}")
        # Don't raise - logging failure shouldn't break the main flow


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return JWT access token"""
    try:
        logger.info(f"Login attempt for user: {form_data.username}")

        user = get_user_by_email(form_data.username)
        if not user:
            logger.warning(f"Login failed: user not found - {form_data.username}")
            raise HTTPException(status_code=401, detail="Invalid username or password")

        if not verify_password(form_data.password, user["password_hash"]):
            logger.warning(f"Login failed: invalid password - {form_data.username}")
            raise HTTPException(status_code=401, detail="Invalid username or password")

        token_data = {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "tenant_id": user["tenant_id"]
        }

        access_token = create_access_token(token_data)
        logger.info(f"Login successful: {user['email']} ({user['role']})")
        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException:
        # Re-raise HTTP exceptions (401 from get_user_by_email or password verification)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during login")


@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: TokenData = Depends(get_current_user)):
    try:
        log_event(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            type="auth_checked",
            payload={"email": current_user.email}
        )
    except Exception as e:
        print(f"[Analytics Logging Failed] {e}")
    return current_user