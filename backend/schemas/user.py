from pydantic import BaseModel, EmailStr
from datetime import datetime


# ─────────────────────────────────────────────
# What the user sends when REGISTERING
# ─────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    email: EmailStr        # pydantic validates it is a proper email format
    password: str          # plain text — we will hash it before saving


# ─────────────────────────────────────────────
# What the user sends when LOGGING IN
# ─────────────────────────────────────────────
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ─────────────────────────────────────────────
# What we send BACK to the user (API response)
# Notice: no password field here — never send it back
# ─────────────────────────────────────────────
class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    created_at: datetime

    # This tells Pydantic to read data from a SQLAlchemy model object
    # instead of requiring a plain dictionary
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# The JWT token we send back after a successful login
# ─────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─────────────────────────────────────────────
# The data packed inside the JWT token
# ─────────────────────────────────────────────
class TokenData(BaseModel):
    user_id: int | None = None
