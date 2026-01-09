import asyncio
import sys
from sqlalchemy.orm import sessionmaker
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.db import engine
from app.models.agent_config import AgentConfig
from app.core.security import encrypt_api_key, decrypt_api_key

async def migrate_keys():
    print("Starting Key Encryption Migration...")
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        try:
            query = select(AgentConfig)
            result = await session.exec(query)
            configs = result.all()
            
            count = 0
            for config in configs:
                if config.encrypted_api_key:
                    # 1. Try to decrypt (if fails, it returns original plain text)
                    plain = decrypt_api_key(config.encrypted_api_key)
                    
                    # 2. Encrypt it (generating new cipher)
                    cipher = encrypt_api_key(plain)
                    
                    # 3. Update if different (Fernet always different, but logical check)
                    if config.encrypted_api_key != cipher:
                        config.encrypted_api_key = cipher
                        session.add(config)
                        count += 1
            
            await session.commit()
            print(f"Migration Complete. Encrypted {count} keys.")
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate_keys())
