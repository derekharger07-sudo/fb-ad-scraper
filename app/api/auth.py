import os
import hashlib
import base64
import hmac
from datetime import datetime, timedelta
from typing import Optional
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlmodel import Session, select
from app.db.models import User
from app.db.repo import engine

SESSION_SECRET = os.environ.get("SESSION_SECRET")
if not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET environment variable must be set for authentication to work!")

serializer = URLSafeTimedSerializer(SESSION_SECRET)

def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.scrypt(
        password.encode('utf-8'),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        dklen=64
    )
    return base64.b64encode(salt + key).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        decoded = base64.b64decode(hashed_password.encode('utf-8'))
        salt = decoded[:32]
        stored_key = decoded[32:]
        new_key = hashlib.scrypt(
            plain_password.encode('utf-8'),
            salt=salt,
            n=16384,
            r=8,
            p=1,
            dklen=64
        )
        return hmac.compare_digest(new_key, stored_key)
    except Exception:
        return False

def create_session_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id, "created_at": datetime.utcnow().isoformat()})

def verify_session_token(token: str, max_age: int = 86400 * 7) -> Optional[int]:
    try:
        data = serializer.loads(token, max_age=max_age)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None

def get_user_by_username(username: str) -> Optional[User]:
    with Session(engine) as session:
        stmt = select(User).where(User.username == username)
        return session.exec(stmt).first()

def get_user_by_email(email: str) -> Optional[User]:
    with Session(engine) as session:
        stmt = select(User).where(User.email == email)
        return session.exec(stmt).first()

def get_user_by_id(user_id: int) -> Optional[User]:
    with Session(engine) as session:
        return session.get(User, user_id)

def create_user(username: str, email: str, password: str) -> User:
    with Session(engine) as session:
        password_hash = hash_password(password)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

def authenticate_user(username: str, password: str) -> Optional[User]:
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
