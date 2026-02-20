import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def clean():
    engine = create_async_engine(settings.async_database_url)
    async with engine.begin() as conn:
        print("Dropping schema public cascade...")
        await conn.execute(text('DROP SCHEMA public CASCADE;'))
        print("Creating schema public...")
        await conn.execute(text('CREATE SCHEMA public;'))
    await engine.dispose()
    print("Cleaned.")

if __name__ == "__main__":
    asyncio.run(clean())
