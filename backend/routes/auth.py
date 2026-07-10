from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import User, Portfolio
from backend.schemas.user import UserCreate, UserLogin, UserOut, Token
from backend.utils.security import hash_password, verify_password, create_access_token, get_current_user
from backend.config import settings

router = APIRouter()


# REGISTER
# POST /api/auth/register
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Accepts: username, email, password
    Returns: the newly created user (no password)
    """

    # Check if email is already taken
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # Check if username is already taken
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This username is already taken."
        )

    # Hash the password — never store plain text
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(new_user)
    await db.flush()  # gives us new_user.id before the final commit

    # Create a portfolio for this user with the starting balance from config
    new_portfolio = Portfolio(
        user_id=new_user.id,
        cash_balance=settings.initial_balance,
        total_value=settings.initial_balance,
    )
    db.add(new_portfolio)

    # get_db() commits everything at the end automatically
    return new_user


# LOGIN
#POST /api/auth/login
@router.post("/login", response_model=Token)
 async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Accepts: email, password
    Returns: JWT access token
    """

       # Find user by email
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()

     # If user not found or password doesn't matches
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # If account has been deactivated
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated."
        )

    # Create and return the JWT token
    token = create_access_token(user_id=user.id)
    return Token(access_token=token)


 # GET /api/auth/me
   # Returns the currently logged-in user's profile

@router.get("/me", response_model=UserOut)
 async def get_me(current_user: User = Depends(get_current_user)):
    """
    Protected route — any request here must include the JWT token.
    FastAPI automatically calls get_current_user to verify the token.
    Returns the logged-in user's profile.
    """
      return current_user
 