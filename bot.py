import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiocryptopay import AioCryptoPay
from aiocryptopay.const import Networks
from dotenv import load_dotenv

import database as db
from services import SERVICES
from handlers import user, admin

# Загружаем .env из папки рядом с bot.py (гарантированно)
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Отладка
print("=" * 60)
print("BOT_TOKEN    :", "OK" if BOT_TOKEN else "❌ ПУСТО")
print("CRYPTO_TOKEN :", "OK" if CRYPTO_TOKEN else "❌ ПУСТО")
print("ADMIN_IDS    :", ADMIN_IDS)
print("=" * 60)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


async def main():
    # 1. База
    await db.init_db()
    await db.sync_services(SERVICES)

    # 2. Бот и CryptoPay
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    crypto = AioCryptoPay(token=CRYPTO_TOKEN, network=Networks.MAIN_NET)

    # 3. Диспетчер
    dp = Dispatcher(storage=MemoryStorage())

    # 4. Прокидываем зависимости
    dp["crypto"] = crypto
    dp["admin_ids"] = ADMIN_IDS

    # 5. Роутеры
    dp.include_router(admin.router)
    dp.include_router(user.router)

    print("✅ Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        await crypto.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⛔ Остановлен")