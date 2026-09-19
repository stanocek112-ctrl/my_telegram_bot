import aiosqlite
from datetime import datetime

import aiosqlite
import os
from datetime import datetime

DB_PATH = "/data/shop.db" if os.path.isdir("/data") else "shop.db"


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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                from_admin INTEGER,
                text TEXT,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS balances (
                user_id INTEGER PRIMARY KEY,
                amount REAL DEFAULT 0,
                updated_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS balance_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                type TEXT,
                description TEXT,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS blocked_users (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                blocked_at TEXT
            )
        """)
                await db.execute("""
            CREATE TABLE IF NOT EXISTS backup_meta (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                file_id TEXT,
                message_id INTEGER,
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
        async with db.execute(
            "SELECT * FROM orders WHERE payload = ?", (payload,)
        ) as cur:
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
            return [dict(row) async for row in cur]


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM orders WHERE status='paid'"
        ) as cur:
            cnt, total = await cur.fetchone()
        return {"orders": cnt, "revenue": total}


# ---------- Услуги ----------

async def sync_services(services: dict):
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


# ---------- Тикеты ----------

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


# ---------- Баланс ----------

async def get_balance(user_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT amount FROM balances WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0.0


async def add_balance(user_id: int, amount: float,
                      tx_type: str = "deposit",
                      description: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT amount FROM balances WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()

        if row is None:
            await db.execute(
                "INSERT INTO balances (user_id, amount, updated_at) "
                "VALUES (?, ?, ?)",
                (user_id, amount, datetime.now().isoformat())
            )
        else:
            await db.execute(
                "UPDATE balances SET amount = amount + ?, updated_at = ? "
                "WHERE user_id=?",
                (amount, datetime.now().isoformat(), user_id)
            )

        await db.execute(
            "INSERT INTO balance_transactions "
            "(user_id, amount, type, description, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, tx_type, description,
             datetime.now().isoformat())
        )
        await db.commit()


async def get_transactions(user_id: int, limit: int = 15):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM balance_transactions "
            "WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ) as cur:
            return [dict(r) async for r in cur]


async def get_all_balances(limit: int = 50):
    """Возвращает ВСЕХ пользователей с их балансом (включая 0)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT u.user_id, "
            "COALESCE(b.amount, 0) as amount, "
            "u.username, u.full_name "
            "FROM users u "
            "LEFT JOIN balances b ON b.user_id = u.user_id "
            "ORDER BY u.created_at DESC LIMIT ?",
            (limit,)
        ) as cur:
            return [dict(r) async for r in cur]


# ---------- Блокировки ----------

async def block_user(user_id: int, reason: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO blocked_users "
            "(user_id, reason, blocked_at) VALUES (?, ?, ?)",
            (user_id, reason, datetime.now().isoformat())
        )
        await db.commit()


async def unblock_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM blocked_users WHERE user_id=?", (user_id,))
        await db.commit()


async def is_blocked(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM blocked_users WHERE user_id=?", (user_id,)
        ) as cur:
            return await cur.fetchone() is not None


async def get_all_users_with_status():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT u.user_id, u.username, u.full_name, "
            "CASE WHEN b.user_id IS NOT NULL THEN 1 ELSE 0 END as blocked "
            "FROM users u "
            "LEFT JOIN blocked_users b ON u.user_id = b.user_id "
            "ORDER BY u.created_at DESC LIMIT 50"
        ) as cur:
            return [dict(r) async for r in cur]
            # ============================================================
# BACKUP META
# ============================================================

async def save_backup_meta(file_id: str, message_id: int):
    """Сохраняет file_id последнего бэкапа."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO backup_meta (id, file_id, message_id, created_at) "
            "VALUES (1, ?, ?, ?)",
            (file_id, message_id, datetime.now().isoformat())
        )
        await db.commit()


async def get_backup_meta():
    """Возвращает последний бэкап (file_id, message_id) или None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM backup_meta WHERE id=1"
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None
