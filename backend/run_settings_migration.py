from pathlib import Path
import os
import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise SystemExit("DATABASE_URL is missing from backend/.env")

sql_path = ROOT / "001_settings.sql"
sql = sql_path.read_text(encoding="utf-8")

conn = psycopg2.connect(database_url, connect_timeout=10)
try:
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    print("FlowSense settings migration completed successfully.")
    print("Created/updated: flowsense_settings, user_settings, users.role/phone/job_title/department")
finally:
    conn.close()
