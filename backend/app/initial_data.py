import asyncio

from passlib.context import CryptContext
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.db import engine
from app.models.user import UserCreate, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

async def init_db():
    # In dev, ensure tables exist
    from sqlmodel import SQLModel

    # Import all models to ensure they are registered in metadata
    from app.models import User

    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    import os
    print(f"DEBUG: os.environ.get('SUPER_ADMIN') is '{os.environ.get('SUPER_ADMIN')}'")
    async with AsyncSession(engine) as session:
        print(f"DEBUG: settings.SUPER_ADMIN is '{settings.SUPER_ADMIN}'")

        # Determine strict username
        # If SUPER_ADMIN looks like an email, default username to 'admin'.
        # If it's a simple string (like 'sadmin'), use that as username.
        target_username = "admin"
        if "@" not in settings.SUPER_ADMIN:
            target_username = settings.SUPER_ADMIN

        print(f"DEBUG: Target username is '{target_username}'")

        # Check for username conflict (someone else has this username)
        # We need to do this BEFORE creating the new user or updating the existing one
        user_conflict_query = select(User).where(User.username == target_username)
        result_conflict = await session.exec(user_conflict_query)
        conflicting_user = result_conflict.first()

        # Note: If conflicting_user is the SAME as the superuser we are about to check/create (by email), it's fine.
        # But we haven't fetched the superuser by email yet.

        query = select(User).where(User.email == settings.SUPER_ADMIN)
        result = await session.exec(query)
        user = result.first()

        if conflicting_user:
            # If the user occupying the name is NOT the one we are managing (or we are creating a new one)
            is_same_user = user and conflicting_user.id == user.id
            if not is_same_user:
                 import uuid
                 backup_username = f"{target_username}_old_{str(uuid.uuid4())[:8]}"
                 print(f"WARNING: Username '{target_username}' is taken by user {conflicting_user.email} (ID: {conflicting_user.id}). Renaming that user to '{backup_username}'.")
                 conflicting_user.username = backup_username
                 session.add(conflicting_user)
                 await session.commit()

        if not user:
            print(f"Creating superuser {settings.SUPER_ADMIN}")
            user_in = UserCreate(
                email=settings.SUPER_ADMIN,
                username=target_username,
                full_name="Initial Admin",
                role=UserRole.SUPER_ADMIN,
            )
            user = User.model_validate(user_in) # replaced from_orm
            user.hashed_password = get_password_hash(settings.SUPER_ADMIN_PASSWORD)
            session.add(user)
            await session.commit()
        else:
            print(f"Superuser {settings.SUPER_ADMIN} already exists. Updating password and ensuring username...")
            user.hashed_password = get_password_hash(settings.SUPER_ADMIN_PASSWORD)
            user.username = target_username
            user.role = UserRole.SUPER_ADMIN
            session.add(user)
            await session.commit()
            print("Superuser updated.")

if __name__ == "__main__":
    import asyncio
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    max_retries = 60
    retry_interval = 2

    for i in range(max_retries):
        try:
            asyncio.run(init_db())
            break
        except Exception as e:
            logger.warning(f"Database not ready yet, retrying... ({i+1}/{max_retries}) Error: {e}")
            import time
            time.sleep(retry_interval)
    else:
        logger.error("Could not connect to database after many retries.")
        exit(1)
