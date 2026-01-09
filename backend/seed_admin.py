import datetime
import sqlite3
import uuid

from passlib.context import CryptContext

# Path based on env 'sqlite:///./data/project_data.db' and PWD '/code'
DB_FILE = "/code/data/project_data.db"

CTX = CryptContext(schemes=["bcrypt"], deprecated="auto")
PWD_HASH = CTX.hash("admin")
EMAIL = "admin@example.com"

def run():
    print(f"Connecting to SQLite: {DB_FILE}")
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # Check if admin exists (Quote table "user")
        c.execute('SELECT email FROM "user" WHERE email=?', (EMAIL,))
        if c.fetchone():
            print("Admin user already exists.")
            conn.close()
            return

        print("Creating Admin user...")
        uid = str(uuid.uuid4())
        now = datetime.datetime.now().isoformat()

        # Insert Admin
        # Assuming is_active/is_superuser are boolean (1/0 in SQLite)
        query = '''
        INSERT INTO "user" (id, email, hashed_password, role, is_active, created_at, full_name, is_superuser)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        c.execute(query, (uid, EMAIL, PWD_HASH, "admin", 1, now, "Super Admin", 1))

        conn.commit()
        print("Admin user created successfully!")
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run()
