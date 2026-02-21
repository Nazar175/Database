import hashlib
import hmac
import os
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import DATABASE_URL, get_db
from models import User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

def _stable_default_signing_key() -> str:
    seed = DATABASE_URL or "shop-db-default-seed"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


JWT_SIGNING_KEY = os.getenv("JWT_SIGNING_KEY", _stable_default_signing_key())
PASSWORD_SIGNING_KEY = os.getenv("PASSWORD_SIGNING_KEY", JWT_SIGNING_KEY)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
router = APIRouter()


def _hs256_sign(value: str, key: str) -> str:
    return hmac.new(key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SIGNING_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password, hashed_password):
    expected_hash = _hs256_sign(plain_password, PASSWORD_SIGNING_KEY)
    return hmac.compare_digest(expected_hash, hashed_password)


def get_password_hash(password):
    return _hs256_sign(password, PASSWORD_SIGNING_KEY)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, JWT_SIGNING_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/register")
def register(username: str, email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter((User.username == username)|(User.email == email)).first()
    if user:
        raise HTTPException(status_code=400, detail="User already exists")
    new_user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}
