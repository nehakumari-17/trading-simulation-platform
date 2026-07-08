from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import settings
from backend.database import get_db

# ─────────────────────────────────────────────
# Password Hashing
# passlib handles turning plain text → hashed string and back
# We use bcrypt which is the industry standard for password hashing
# ─────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Converts a plain text password into a secure hash for storage."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks if a plain password matches the stored hash. Returns True/False."""
    return pwd_context.verify(plain_password, hashed_password)


# ─────────────────────────────────────────────
# JWT Token
# JWT = JSON Web Token
# It is a small encoded string we give the user after login
# The user sends it back with every request to prove they are logged in
# ─────────────────────────────────────────────

def create_access_token(user_id: int) -> str:
    """
    Creates a JWT token containing the user's ID.
    The token expires after the time set in config.py.
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),   # "sub" = subject (who the token belongs to)
        "exp": expire           # expiry time
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


# ─────────────────────────────────────────────
# OAuth2 scheme
# This tells FastAPI to look for the token in the
# "Authorization: Bearer <token>" header of incoming requests
# ─────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    FastAPI dependency — decodes the JWT token and returns the logged-in user.
    Any route that needs authentication uses: Depends(get_current_user)
    If the token is missing, expired, or invalid, it returns a 401 error.
    """
    # Import here to avoid circular imports
    from backend.models import User

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode the token using our secret key
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    # Fetch the user from the database
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_error

    return user
