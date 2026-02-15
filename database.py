# database.py
import aiosqlite
import config

async def init_database(db: aiosqlite.Connection) -> None:
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_username TEXT NOT NULL,
            masked_username TEXT NOT NULL,
            embed_data TEXT NOT NULL,
            claimed_by INTEGER DEFAULT NULL,
            claimed_by_name TEXT DEFAULT NULL,
            claimed_at TEXT DEFAULT NULL,
            is_claimed INTEGER DEFAULT 0,
            is_staff_cut INTEGER DEFAULT 0,
            message_id INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS claim_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id INTEGER NOT NULL,
            account_username TEXT NOT NULL,
            claimed_by INTEGER NOT NULL,
            claimed_by_name TEXT NOT NULL,
            action TEXT NOT NULL,
            is_staff_cut INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (claim_id) REFERENCES claims(id)
        );

        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS user_overrides (
            user_id INTEGER PRIMARY KEY,
            cut_percentage INTEGER NOT NULL
        );
    """)
    
    await db.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('claim_counter', 0)")
    await db.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('global_percent', ?)", (config.DEFAULT_GLOBAL_PERCENT,))
    await db.commit()
