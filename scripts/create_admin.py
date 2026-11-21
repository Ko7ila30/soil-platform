"""Creates (or resets) the admin account from ADMIN_EMAIL / ADMIN_PASSWORD in .env"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from db import get_connection

load_dotenv()
email, pw = os.getenv("ADMIN_EMAIL"), os.getenv("ADMIN_PASSWORD")
if not email or not pw or len(pw) < 8:
    sys.exit("Set ADMIN_EMAIL and ADMIN_PASSWORD (8+ characters) in .env")
conn = get_connection()
try:
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'admin')
                       ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash, role = 'admin'""",
                    (email.lower(), generate_password_hash(pw)))
    conn.commit()
    print("Admin ready:", email.lower())
finally:
    conn.close()