from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from jose import jwt
from datetime import datetime, timedelta
import sqlite3
import os  # ✅ REQUIRED for reading environment variables
import json

from dotenv import load_dotenv
load_dotenv()

print("🔐 JWT_SECRET =", os.getenv("JWT_SECRET"))

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

SECRET_KEY = os.getenv("JWT_SECRET", "secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 3

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_email(email: str):
    conn = sqlite3.connect("handoff.sqlite")
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
    conn = sqlite3.connect("handoff.sqlite")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO events (user_id, tenant_id, type, payload, ts) VALUES (?, ?, ?, ?, datetime('now'))",
        (user_id, tenant_id, type, json.dumps(payload))
    )
    conn.commit()
    conn.close()


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_email(form_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token_data = {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "tenant_id": user["tenant_id"]
    }

    access_token = create_access_token(token_data)
    return {"access_token": access_token, "token_type": "bearer"}


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