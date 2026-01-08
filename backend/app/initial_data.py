import asyncio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.db import get_session, engine
from app.models.user import User, UserRole, UserCreate
from app.core.config import settings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

async def init_db():
    # In dev, ensure tables exist
    from sqlmodel import SQLModel
    
    # Import all models to ensure they are registered in metadata
    from app.models import User, Course, Room, Announcement, Message, AgentConfig
    
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    import os
    print(f"DEBUG: os.environ.get('FIRST_SUPERUSER') is '{os.environ.get('FIRST_SUPERUSER')}'")
    async with AsyncSession(engine) as session:
        print(f"DEBUG: settings.FIRST_SUPERUSER is '{settings.FIRST_SUPERUSER}'")
        query = select(User).where(User.email == settings.FIRST_SUPERUSER)
        result = await session.exec(query)
        user = result.first()
        
        if not user:
            print(f"Creating superuser {settings.FIRST_SUPERUSER}")
            user_in = UserCreate(
                email=settings.FIRST_SUPERUSER,
                username="admin", # Allow login with "admin"
                full_name="Initial Admin",
                role=UserRole.super_admin,
            )
            user = User.model_validate(user_in) # replaced from_orm
            user.hashed_password = get_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
            session.add(user)
            await session.commit()
        else:
            print(f"Superuser {settings.FIRST_SUPERUSER} already exists. Updating password and ensuring username...")
            user.hashed_password = get_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
            if not user.username:
                user.username = "admin"
            user.role = UserRole.super_admin
            session.add(user)
            await session.commit()
            print("Superuser updated.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
