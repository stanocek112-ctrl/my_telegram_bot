"""
Админ: ввод кодов активации вручную.
"""
import logging
import os

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import (
    admin_back_kb,
    admin_code_orders_kb,
    admin_code_cancel_kb,
)

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

router = Router()


class CodeSG(StatesGroup):
    entering_code = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ============================================================
# СПИСОК ЗАКАЗОВ БЕЗ КОДА
# ============================================================

@router.callback_query(F.data == "adm_set_code")
async def adm_set_code_list(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return
    await state.clear()
    await cb.answer()

    orders = await db.get_orders_without_code(limit=15)

    if not orders:
        await cb.message.edit_text(
            "🔑 <b>Ввод кодов</b>\n\n"
            "Нет активных заказов без кода.",
            reply_markup=admin_back_kb()
        )
        return

    await cb.message.edit_text(
        f"🔑 <b>Ввод кодов</b>\n\n"
        f"Заказы без кода ({len(orders)}):\n"
        f"Нажмите на заказ, чтобы ввести код.",
        reply_markup=admin_code_orders_kb(orders)
    )


# ============================================================
# ВВОД КОДА ДЛЯ ЗАКАЗА
# ============================================================

@router.callback_query(F.data.startswith("adm_code_"))
async def adm_code_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return

    order_id = int(cb.data.replace("adm_code_", ""))
    order = await db.get_order(order_id)

    if not order:
        await cb.answer("Заказ не найден", show_alert=True)
        return

    await cb.answer()
    await state.update_data(order_id=order_id)
    await state.set_state(CodeSG.entering_code)

    phone = order.get("phone") or "—"
    user_id = order.get("user_id") or "—"

    await cb.message.edit_text(
        f"🔑 <b>Ввод кода</b>\n\n"
        f"🆔 Заказ: <code>{order_id}</code>\n"
        f"📱 Номер: <code>{phone}</code>\n"
        f"👤 Пользователь: <code>{user_id}</code>\n"
        f"📦 Услуга: <b>{order.get('service_name', '—')}</b>\n\n"
        f"✏️ Пришлите код активации одним сообщением:",
        reply_markup=admin_code_cancel_kb()
    )


@router.message(CodeSG.entering_code)
async def adm_code_save(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    code = message.text.strip()
    if not code:
        await message.answer("❌ Код не может быть пустым.")
        return

    data = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await state.clear()
        await message.answer("❌ Заказ потерян. Откройте заново.")
        return

    order = await db.get_order(order_id)
    if not order:
        await state.clear()
        await message.answer("❌ Заказ не найден.")
        return

    # Сохраняем код в БД
    await db.set_order_code(order_id, code)
    await state.clear()

    # Подтверждение админу
    await message.answer(
        f"✅ <b>Код сохранён</b>\n\n"
        f"🆔 Заказ: <code>{order_id}</code>\n"
        f"🔢 Код: <code>{code}</code>\n\n"
        f"Пользователю отправлено уведомление.",
        reply_markup=admin_back_kb()
    )

    # Уведомляем пользователя
    user_id = order.get("user_id")
    phone = order.get("phone") or "—"

    if user_id:
        try:
            await bot.send_message(
                user_id,
                f"🔔 <b>Код активации получен!</b>\n\n"
                f"📱 Номер: <code>{phone}</code>\n"
                f"🔑 Код: <code>{code}</code>\n"
                f"🆔 Заказ №: <code>{order_id}</code>\n\n"
                f"👇 Нажмите на код, чтобы скопировать.\n"
                f"<i>Если код не подошёл — обратитесь в поддержку.</i>"
            )
        except Exception as e:
            logging.warning(f"[CODE] Не отправили юзеру {user_id}: {e}")
