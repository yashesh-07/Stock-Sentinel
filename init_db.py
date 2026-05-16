# init_db.py
import sys
from app.database.session import engine
from app.database import models

def init_tables():
    print("[DB INIT] Connecting to PostgreSQL instance...")
    try:
        models.Base.metadata.create_all(bind=engine)
        print("[DB INIT] Success! All database tables generated seamlessly.")
    except Exception as e:
        print(f"[DB INIT] Fatal: Failed to generate tables. Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_tables()