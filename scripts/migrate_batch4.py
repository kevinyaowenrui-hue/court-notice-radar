import sqlite3
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
DB_PATH = 'data/court_notices.db'

def migrate_batch4():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Update court_notices table
    c.execute("PRAGMA table_info(court_notices)")
    cols = [col[1] for col in c.fetchall()]
    print("Existing court_notices columns:", cols)

    if 'is_starred' not in cols:
        print("Adding column: is_starred to court_notices")
        c.execute("ALTER TABLE court_notices ADD COLUMN is_starred BOOLEAN DEFAULT 0")
        c.execute("CREATE INDEX IF NOT EXISTS idx_court_notices_starred ON court_notices(is_starred)")

    if 'user_notes' not in cols:
        print("Adding column: user_notes to court_notices")
        c.execute("ALTER TABLE court_notices ADD COLUMN user_notes TEXT DEFAULT ''")

    # 2. Create system_settings table if not exists
    c.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key VARCHAR(64) PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("system_settings table ensured.")

    conn.commit()
    conn.close()
    print("Batch 4 DB migration completed successfully.")

if __name__ == '__main__':
    migrate_batch4()
