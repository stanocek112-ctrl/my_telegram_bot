import aiosqlite
from datetime import datetime

DB_PATH = "shop.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                service_key TEXT,
                service_name TEXT,
                amount REAL,
                status TEXT DEFAULT 'pending',
                invoice_id INTEGER,
                payload TEXT UNIQUE,
                created_at TEXT,
                paid_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS services (
                key TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                price_usdt REAL,
                emoji TEXT,
                delivery_type TEXT,
                delivery_content TEXT
            )
        """)
        # 👇 НОВАЯ ТАБЛИЦА
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                message TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT,
                closed_at TEXT
            )
        """)
        # 👇 История сообщений внутри тикета
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                from_admin INTEGER,
                text TEXT,
                created_at TEXT
            )
        """)
        await db.commit()


# ---------- Пользователи ----------

async def add_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name, created_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, username or "", full_name, datetime.now().isoformat())
        )
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            return [row[0] async for row in cur]


async def count_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            return (await cur.fetchone())[0]


# ---------- Заказы ----------

async def create_order(user_id, service_key, service_name, amount, payload, invoice_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO orders (user_id, service_key, service_name, amount, payload, "
            "invoice_id, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
            (user_id, service_key, service_name, amount, payload, invoice_id,
             datetime.now().isoformat())
        )
        await db.commit()


async def get_order_by_payload(payload: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE payload = ?", (payload,)) as cur:
            return await cur.fetchone()


async def get_order_by_invoice(invoice_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE invoice_id = ?", (invoice_id,)
        ) as cur:
            return await cur.fetchone()


async def mark_paid(payload: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET status='paid', paid_at=? WHERE payload=?",
            (datetime.now().isoformat(), payload)
        )
        await db.commit()


async def get_user_orders(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE user_id=? AND status='paid' "
            "ORDER BY paid_at DESC LIMIT ?",
            (user_id, limit)
        ) as cur:
            return [row async for row in cur]


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM orders WHERE status='paid'"
        ) as cur:
            cnt, total = await cur.fetchone()
        return {"orders": cnt, "revenue": total}


# ---------- Услуги (синхронизация) ----------

async def sync_services(services: dict):
    """При старте заливаем услуги из services.py в БД (если их там нет)."""
    async with aiosqlite.connect(DB_PATH) as db:
        for key, s in services.items():
            await db.execute(
                "INSERT OR IGNORE INTO services "
                "(key, name, description, price_usdt, emoji, delivery_type, delivery_content) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (key, s["name"], s["description"], s["price_usdt"], s["emoji"],
                 s.get("delivery_type", "text"), s.get("delivery_content", ""))
            )
        await db.commit()


async def get_all_services():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM services") as cur:
            return [dict(row) async for row in cur]


async def get_service(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM services WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_service_price(key: str, new_price: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE services SET price_usdt=? WHERE key=?", (new_price, key))
        await db.commit()


async def update_service_content(key: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE services SET delivery_content=? WHERE key=?", (content, key)
        )
        await db.commit()


async def update_service_name(key: str, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE services SET name=? WHERE key=?", (name, key))
        await db.commit()


async def delete_service(key: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM services WHERE key=?", (key,))
        await db.commit()


async def add_service(key, name, description, price, emoji, d_type, d_content):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO services (key, name, description, price_usdt, emoji, "
            "delivery_type, delivery_content) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (key, name, description, price, emoji, d_type, d_content)
        )
        await db.commit()
        # ---------- Тикеты (обращения) ----------

async def create_ticket(user_id, username, full_name, phone, message):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO tickets (user_id, username, full_name, phone, message, "
            "status, created_at) VALUES (?, ?, ?, ?, ?, 'open', ?)",
            (user_id, username or "", full_name, phone, message,
             datetime.now().isoformat())
        )
        ticket_id = cur.lastrowid
        await db.execute(
            "INSERT INTO ticket_messages (ticket_id, from_admin, text, created_at) "
            "VALUES (?, 0, ?, ?)",
            (ticket_id, message, datetime.now().isoformat())
        )
        await db.commit()
        return ticket_id


async def get_open_tickets():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tickets WHERE status='open' ORDER BY created_at DESC"
        ) as cur:
            return [dict(r) async for r in cur]


async def get_ticket(ticket_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def add_ticket_message(ticket_id: int, from_admin: bool, text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ticket_messages (ticket_id, from_admin, text, created_at) "
            "VALUES (?, ?, ?, ?)",
            (ticket_id, 1 if from_admin else 0, text, datetime.now().isoformat())
        )
        await db.commit()


async def close_ticket(ticket_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tickets SET status='closed', closed_at=? WHERE id=?",
            (datetime.now().isoformat(), ticket_id)
        )
        await db.commit()


async def get_user_tickets(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tickets WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ) as cur:
            return [dict(r) async for r in cur]


async def count_open_tickets():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM tickets WHERE status='open'"
        ) as cur:
            return (await cur.fetchone())[0]