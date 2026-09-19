"""
Модуль резервного копирования БД в Telegram.
"""
import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

import database as db

BACKUP_INTERVAL = 3600   # 1 час в секундах (можно 1800 = 30 мин)
DB_FILE = db.DB_PATH


async def send_backup(bot: Bot, admin_id: int):
    """Отправляет shop.db админу в Telegram и сохраняет file_id."""
    if not os.path.exists(DB_FILE):
        logging.warning(f"[BACKUP] Файл {DB_FILE} не найден, пропускаю")
        return

    try:
        file = FSInputFile(DB_FILE, filename="shop.db")
        msg = await bot.send_document(
            admin_id,
            file,
            caption=f"🗄 Резервная копия БД\n📅 {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        # Сохраняем file_id — по нему сможем скачать при восстановлении
        await db.save_backup_meta(msg.document.file_id, msg.message_id)
        logging.info(f"[BACKUP] Отправлен, file_id={msg.document.file_id[:20]}...")
    except Exception as e:
        logging.error(f"[BACKUP] Ошибка отправки: {e}")


async def restore_backup(bot: Bot, admin_id: int) -> bool:
    """
    Пытается восстановить БД из последнего бэкапа в Telegram.
    Возвращает True если восстановил, False если нечего восстанавливать.
    """
    # Если файл уже есть (например, в Volume) — ничего не делаем
    if os.path.exists(DB_FILE) and os.path.getsize(DB_FILE) > 0:
        logging.info(f"[BACKUP] БД на месте, восстановление не нужно")
        return False

    meta = await db.get_backup_meta()
    if not meta or not meta.get("file_id"):
        logging.info("[BACKUP] Бэкапа нет — создаём БД с нуля")
        return False

    try:
        file = await bot.get_file(meta["file_id"])
        # Скачиваем во временную папку
        tmp = f"/tmp/shop_restore.db" if os.name != "nt" else "shop_restore.db"
        await bot.download_file(file.file_path, tmp)

        # Заменяем старую БД
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        os.rename(tmp, DB_FILE)

        logging.info(f"[BACKUP] ✅ БД восстановлена из Telegram")
        return True
    except Exception as e:
        logging.error(f"[BACKUP] Ошибка восстановления: {e}")
        return False


async def backup_loop(bot: Bot, admin_id: int):
    """Фоновая задача — отправка бэкапа каждые BACKUP_INTERVAL секунд."""
    # Первый бэкап — через 5 минут после запуска
    await asyncio.sleep(300)
    await send_backup(bot, admin_id)

    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        await send_backup(bot, admin_id)
