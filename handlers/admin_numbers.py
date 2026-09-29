"""
Админ: управление складом номеров.
"""
import logging

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from config import ADMIN_IDS
from keyboards import (
    admin_back_kb,
    admin_numbers_kb,
    admin_number_service_kb,
    admin_number_cancel_kb,
    admin_number_clear_confirm_kb,
)

router = Router()


# ============================================================
# FSM
# ============================================================

class NumberSG(StatesGroup):
    adding_numbers = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ============================================================
# СПИСОК УСЛУГ
# ============================================================

@router.callback_query(F.data == "adm_numbers")
async def adm_numbers_list(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return
    await state.clear()
    await cb.answer()

    services = await db.get_services_with_stock()

    if not services:
        await cb.message.edit_text(
            "📱 <b>Склад номеров</b>\n\n"
            "Нет услуг. Сначала создайте услугу в «🛍 Управление услугами».",
            reply_markup=admin_back_kb()
        )
        return

    await cb.message.edit_text(
        "📱 <b>Склад номеров</b>\n\n"
        "Выберите услугу для управления номерами:",
        reply_markup=admin_numbers_kb(services)
    )


# ============================================================
# МЕНЮ УСЛУГИ
# ============================================================

@router.callback_query(F.data.startswith("adm_num_"))
async def adm_number_service(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return

    # Игнорируем вложенные action
    if (cb.data.startswith("adm_num_add_")
            or cb.data.startswith("adm_num_stats_")
            or cb.data.startswith("adm_num_clear_")):
        return

    key = cb.data.replace("adm_num_", "")
    service = await db.get_service(key)
    if not service:
        await cb.answer("Услуга не найдена", show_alert=True)
        return

    await cb.answer()
    await state.clear()

    free = await db.count_free_numbers(key)
    total = await db.count_total_numbers(key)
    used = total - free

    emoji = service.get("emoji") or "📦"

    await cb.message.edit_text(
        f"📱 <b>Склад номеров</b>\n\n"
        f"{emoji} Услуга: <b>{service['name']}</b>\n"
        f"🔑 Ключ: <code>{key}</code>\n\n"
        f"📊 Статистика:\n"
        f"• Свободных: <b>{free}</b>\n"
        f"• Использованных: <b>{used}</b>\n"
        f"• Всего: <b>{total}</b>",
        reply_markup=admin_number_service_kb(key)
    )


# ============================================================
# ДОБАВЛЕНИЕ НОМЕРОВ
# ============================================================

@router.callback_query(F.data.startswith("adm_num_add_"))
async def adm_num_add_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return

    key = cb.data.replace("adm_num_add_", "")
    service = await db.get_service(key)
    if not service:
        await cb.answer("Услуга не найдена", show_alert=True)
        return

    await cb.answer()
    await state.update_data(service_key=key)
    await state.set_state(NumberSG.adding_numbers)

    await cb.message.edit_text(
        f"➕ <b>Добавление номеров</b>\n\n"
        f"Услуга: <b>{service['name']}</b>\n\n"
        f"Отправьте номера — <b>каждый с новой строки</b>:\n\n"
        f"<code>+79123456789\n"
        f"+79987654321\n"
        f"+79001112233</code>\n\n"
        f"⚠️ Можно вставить сразу много номеров.\n"
        f"Дубликаты будут пропущены.",
        reply_markup=admin_number_cancel_kb(key)
    )


@router.message(NumberSG.adding_numbers)
async def adm_num_add_save(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    key = data.get("service_key")

    if not key:
        await state.clear()
        await message.answer(
            "❌ Услуга потеряна. Откройте заново.",
            reply_markup=admin_back_kb()
        )
        return

    # Парсим номера
    raw = message.text.strip()
    phones = [line.strip() for line in raw.split("\n") if line.strip()]

    if not phones:
        await message.answer("❌ Не найдено ни одного номера.")
        return

    # Нормализуем (оставляем только + и цифры)
    cleaned = []
    for p in phones:
        norm = "".join(ch for ch in p if ch.isdigit() or ch == "+")
        if len(norm) >= 10:
            cleaned.append(norm)

    if not cleaned:
        await message.answer(
            "❌ Номера не распознаны. Пример: <code>+79123456789</code>"
        )
        return

    # Добавляем в БД
    added = await db.add_numbers_bulk(key, cleaned)

    await state.clear()

    service = await db.get_service(key)
    name = service["name"] if service else key

    await message.answer(
        f"✅ <b>Номера добавлены</b>\n\n"
        f"Услуга: <b>{name}</b>\n"
        f"Принято: <b>{len(cleaned)}</b>\n"
        f"Добавлено новых: <b>{added}</b>\n"
        f"Пропущено дубликатов: <b>{len(cleaned) - added}</b>",
        reply_markup=admin_number_service_kb(key)
    )


# ============================================================
# СТАТИСТИКА
# ============================================================

@router.callback_query(F.data.startswith("adm_num_stats_"))
async def adm_num_stats(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return

    key = cb.data.replace("adm_num_stats_", "")
    service = await db.get_service(key)
    if not service:
        await cb.answer("Услуга не найдена", show_alert=True)
        return

    await cb.answer()

    free = await db.count_free_numbers(key)
    total = await db.count_total_numbers(key)
    used = total - free

    emoji = service.get("emoji") or "📦"

    await cb.message.edit_text(
        f"📊 <b>Статистика склада</b>\n\n"
        f"{emoji} Услуга: <b>{service['name']}</b>\n"
        f"🔑 Ключ: <code>{key}</code>\n\n"
        f"📈 <b>Детально:</b>\n"
        f"• 🟢 Свободных: <b>{free}</b>\n"
        f"• 🔴 Использованных: <b>{used}</b>\n"
        f"• 📦 Всего: <b>{total}</b>",
        reply_markup=admin_number_service_kb(key)
    )


# ============================================================
# ОЧИСТКА
# ============================================================

@router.callback_query(F.data.startswith("adm_num_clear_do_"))
async def adm_num_clear_do(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return

    key = cb.data.replace("adm_num_clear_do_", "")
    service = await db.get_service(key)
    if not service:
        await cb.answer("Услуга не найдена", show_alert=True)
        return

    count = await db.clear_all_numbers(key)
    await cb.answer(f"Удалено: {count}", show_alert=True)

    services = await db.get_services_with_stock()
    await cb.message.edit_text(
        f"🗑 <b>Склад очищен</b>\n\n"
        f"Удалено номеров: <b>{count}</b>\n\n"
        f"📱 <b>Склад номеров</b>\n"
        f"Выберите услугу:",
        reply_markup=admin_numbers_kb(services)
    )


@router.callback_query(F.data.startswith("adm_num_clear_"))
async def adm_num_clear_confirm(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return

    if cb.data.startswith("adm_num_clear_do_"):
        return

    key = cb.data.replace("adm_num_clear_", "")
    service = await db.get_service(key)
    if not service:
        await cb.answer("Услуга не найдена", show_alert=True)
        return

    await cb.answer()
    free = await db.count_free_numbers(key)
    used = await db.count_used_numbers(key)

    await cb.message.edit_text(
        f"⚠️ <b>Очистка склада</b>\n\n"
        f"Услуга: <b>{service['name']}</b>\n\n"
        f"Будет удалено:\n"
        f"• 🟢 Свободных: {free}\n"
        f"• 🔴 Использованных: {used}\n"
        f"• 📦 Всего: {free + used}\n\n"
        f"⚠️ <b>Действие необратимо!</b>\n"
        f"Подтвердите удаление:",
        reply_markup=admin_number_clear_confirm_kb(key)
    )
