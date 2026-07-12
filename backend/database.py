from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings


# Step 1: Create the engine
# The engine is the actual connection to the database.
# It reads the database URL from config.py.
# echo=settings.debug prints every SQL query when debug is True — handy during development.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)


# Step 2: Create a session factory
# A session is like a temporary workspace where you do DB operations
# (read, insert, update, delete).
# This factory creates a fresh session every time you call it.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Step 3: Create the Base class
# All database models (tables) in models.py will inherit from this.
# SQLAlchemy uses it to keep track of all tables and create them automatically.
class Base(DeclarativeBase):
    pass


# Step 4: The get_db dependency
# FastAPI calls this automatically whenever a route needs the database.
# It opens a session, gives it to the route, then closes it when done.
# If something goes wrong it rolls back all changes to keep the data safe.
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session           # hand the session to the route handler
            await session.commit()  # save changes if everything went fine
        except Exception:
            await session.rollback()  # undo changes if something went wrong
            raise
