from app.db.database import get_pg_pool, get_sqlite_db

async def init_databases():
    # PostgreSQL tables
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                avatar TEXT,
                balance BIGINT DEFAULT 100,
                bank_balance BIGINT DEFAULT 0,
                last_daily TIMESTAMP
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bank_deposits (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(id),
                amount BIGINT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        # и другие таблицы, которые были в main.py...
        # все CREATE TABLE IF NOT EXISTS из исходного main.py для Postgres
    # SQLite tables
    sqlite = await get_sqlite_db()
    await sqlite.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            bio TEXT,
            status TEXT
        );
    """)
    # все остальные SQLite-таблицы из main.py...