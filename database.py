import sqlite3

conn = sqlite3.connect("data.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    referred_by INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS rdps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rdp TEXT,
    assigned INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS redeem (
    code TEXT PRIMARY KEY,
    used INTEGER DEFAULT 0
)
""")

conn.commit()
