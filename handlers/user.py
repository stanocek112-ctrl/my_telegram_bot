import logging
import asyncio
import random
from datetime import datetime

from generators import generate_phone, generate_code

from aiogram import Router, F, Bot, BaseMiddleware
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    TelegramObject,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiocryptopay import AioCryptoPay
from aiocryptopay.const import InvoiceStatus
from typing import Callable, Dict, Any, Awaitable

import database as db
from services import PAYMENT_ASSET
from keyboards import services_kb, back_kb, main_menu_kb, user_tickets_kb
from generators import generate_phone, generate_code

router = Router()
# ============================================================
# FSM-СОСТОЯНИЯ
# ============================================================

from aiogram.fsm.state import State, StatesGroup


class TicketForm(StatesGroup):
    message = State()


class CodeFlow(StatesGroup):
    waiting_code = State()


# если у вас есть ещё какие-то FSM — добавьте их здесь тоже

async def deliver_order(bot: Bot, user_id: int, order: dict, service: dict):
    """Выдаёт товар пользователю в зависимости от типа."""
    dtype = service.get("delivery_type", "text")
    content = service.get("delivery_content", "")

    header = (
        f"🎉 <b>Ваш заказ оплачен!</b>\n\n"
        f"📦 Услуга: <b>{order['service_name']}</b>\n"
        f"💵 Сумма: {order['amount']} {PAYMENT_ASSET}\n"
        f"🧾 Заказ №: <code>{order['id']}</code>\n\n"
    )

    if dtype == "text":
        await bot.send_message(user_id, header + f"<b>Ваш товар:</b>\n\n{content}")

    elif dtype == "link":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Получить доступ", url=content)]
        ])
        await bot.send_message(user_id,
                               header + "Нажмите кнопку ниже:",
                               reply_markup=kb)

    elif dtype == "file":
        try:
            await bot.send_document(user_id, document=content, caption=header)
        except Exception as e:
            logging.error(f"Ошибка отправки файла: {e}")
            await bot.send_message(user_id,
                                   header + "⚠️ Ошибка выдачи файла.")

    # 👇 НОВЫЙ ТИП — номер телефона
    elif dtype == "phone":
        phone = generate_phone()
        text = (
            header +
            f"📱 <b>Ваш номер:</b> <code>{phone}</code>\n\n"
            f"⏱ <b>Время на активацию: 10 минут</b>\n\n"
            "Нажмите кнопку ниже, когда отправите код на номер."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📨 Отправил код",
                callback_data=f"sent_{order['id']}"
            )],
        ])
        await bot.send_message(user_id, text, reply_markup=kb)
        
@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, admin_ids: list):
    await db.add_user(message.from_user.id, message.from_user.username,
                      message.from_user.full_name)
    is_admin = message.from_user.id in admin_ids
    await message.answer(
        f"👋 Привет, <b>{message.from_user.full_name}</b>!\n\n"
        "🛍 Здесь ты можешь купить услуги с оплатой в криптовалюте.\n"
        "Выбери из каталога 👇",
        reply_markup=main_menu_kb(is_admin)
    )


@router.message(F.text == "🛍 Каталог услуг")
@router.message(Command("catalog"))
async def show_catalog(message: Message):
    services = await db.get_all_services()
    if not services:
        await message.answer("Пока нет доступных услуг.")
        return
    await message.answer(
        "📋 <b>Каталог услуг:</b>\n\nВыбери нужную:",
        reply_markup=services_kb(services, PAYMENT_ASSET)
    )


@router.callback_query(F.data == "back_to_services")
async def back_to_services(cb: CallbackQuery):
    services = await db.get_all_services()
    await cb.message.edit_text(
        "📋 <b>Каталог услуг:</b>\n\nВыбери нужную:",
        reply_markup=services_kb(services, PAYMENT_ASSET)
    )


@router.callback_query(F.data.startswith("buy_"))
async def buy_service(cb: CallbackQuery):
    key = cb.data.replace("buy_", "")
    service = await db.get_service(key)
    if not service:
        await cb.answer("Услуга не найдена", show_alert=True)
        return

    text = (
        f"<b>{service['emoji']} {service['name']}</b>\n\n"
        f"📝 {service['description']}\n\n"
        f"💰 Цена: <b>{service['price_usdt']} {PAYMENT_ASSET}</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплатить", callback_data=f"pay_{key}")],
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_services")],
    ])
    await cb.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data.startswith("pay_"))
async def create_invoice(cb: CallbackQuery, bot: Bot, crypto: AioCryptoPay):
    key = cb.data.replace("pay_", "")
    service = await db.get_service(key)
    if not service:
        await cb.answer("Услуга не найдена", show_alert=True)
        return

    await cb.answer("Создаю счёт...")

    payload = f"u{cb.from_user.id}_{int(datetime.now().timestamp())}"

    try:
        invoice = await crypto.create_invoice(
            asset=PAYMENT_ASSET,
            amount=service["price_usdt"],
            description=f"Оплата: {service['name']}",
            payload=payload,
            expires_in=3600,
        )
    except Exception as e:
        logging.error(f"Ошибка CryptoPay: {e}")
        await cb.message.edit_text("❌ Не удалось создать счёт.", reply_markup=back_kb())
        return

    await db.create_order(
        cb.from_user.id, key, service["name"], service["price_usdt"],
        payload, invoice.invoice_id
    )

    text = (
        f"🧾 <b>Счёт создан!</b>\n\n"
        f"Услуга: <b>{service['name']}</b>\n"
        f"Сумма: <b>{service['price_usdt']} {PAYMENT_ASSET}</b>\n"
        f"Заказ №: <code>{payload}</code>\n\n"
        "Нажми кнопку ниже и оплати. После оплаты нажми «Проверить»."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", url=invoice.bot_invoice_url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_{payload}")],
    ])
    await cb.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data.startswith("check_"))
async def check_payment(cb: CallbackQuery, bot: Bot, crypto: AioCryptoPay, admin_ids: list):
    payload = cb.data.replace("check_", "")
    order = await db.get_order_by_payload(payload)

    if not order:
        await cb.answer("Заказ не найден", show_alert=True)
        return

    if order["status"] == "paid":
        await cb.answer("Уже оплачено ✅", show_alert=True)
        return

    await cb.answer("Проверяю...")

    try:
        invoices = await crypto.get_invoices(invoice_ids=order["invoice_id"])
        inv = invoices[0] if invoices else None
    except Exception as e:
        logging.error(f"CryptoPay check: {e}")
        await cb.answer("Ошибка проверки", show_alert=True)
        return

    if not inv:
        await cb.answer("Счёт не найден", show_alert=True)
        return

    if inv.status == InvoiceStatus.PAID:
        await db.mark_paid(payload)
        service = await db.get_service(order["service_key"])
        order_dict = dict(order)
        order_dict["amount"] = order["amount"]

        # Выдаём товар
        await deliver_order(bot, order["user_id"], order_dict, service)

        # Правим сообщение
        await cb.message.edit_text(
            "✅ <b>Оплата получена!</b>\n\n"
            "Товар выдан — проверь сообщение ниже 👇",
            reply_markup=back_kb()
        )

        # Уведомляем админов
        for aid in admin_ids:
            try:
                await bot.send_message(
                    aid,
                    f"💰 <b>НОВАЯ ОПЛАТА</b>\n\n"
                    f"👤 {cb.from_user.full_name} (<code>{cb.from_user.id}</code>)\n"
                    f"📦 {order['service_name']}\n"
                    f"💵 {order['amount']} {PAYMENT_ASSET}\n"
                    f"🧾 <code>{payload}</code>"
                )
            except Exception:
                pass
    else:
        await cb.answer("⏳ Оплата ещё не поступила. Подожди немного.", show_alert=True)


@router.message(F.text == "📦 Мои покупки")
@router.callback_query(F.data == "my_orders")
async def my_orders(event, bot: Bot):
    if isinstance(event, CallbackQuery):
        msg = event.message
        user_id = event.from_user.id
        await event.answer()
    else:
        msg = event
        user_id = event.from_user.id

    orders = await db.get_user_orders(user_id)
    if not orders:
        await msg.answer("У вас пока нет покупок.")
        return

    text = "📦 <b>Ваши покупки:</b>\n\n"
    for o in orders:
        text += (
            f"• <b>{o['service_name']}</b>\n"
            f"  💵 {o['amount']} {PAYMENT_ASSET}\n"
            f"  🧾 <code>{o['payload']}</code>\n"
            f"  📅 {o['paid_at'][:16] if o['paid_at'] else '-'}\n\n"
        )
    await msg.answer(text)


@router.message(F.text == "🆘 Помощь")
@router.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "📖 <b>Помощь</b>\n\n"
        "/start — главное меню\n"
        "/catalog — каталог услуг\n"
        "🛍 Каталог услуг — кнопка снизу\n"
        "📦 Мои покупки — история заказов\n\n"
        "Оплата — через @CryptoBot в криптовалюте.\n"
        "Если оплатил, но товар не пришёл — нажми «Проверить оплату» ещё раз "
        "или напиши администратору."
    )
    # ---------- Обращения в поддержку ----------

# ---------- Обращения в поддержку ----------

@router.message(F.text == "📩 Написать в поддержку")
async def support_start(message: Message):
    await message.answer(
        "📩 <b>Поддержка</b>\n\n"
        "Создайте обращение — администратор ответит вам лично.\n\n"
        "Что хотите сделать?",
        reply_markup=user_tickets_kb()
    )


@router.callback_query(F.data == "new_ticket")
async def new_ticket_start(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(TicketForm.message)
    await cb.message.edit_text(
        "📝 <b>Опишите ваш вопрос</b>\n\n"
        "Напишите текст обращения одним сообщением — "
        "администратор ответит вам лично.",
        reply_markup=None
    )


@router.message(TicketForm.message)
async def ticket_message_save(message: Message, state: FSMContext,
                               bot: Bot, admin_ids: list):
    ticket_id = await db.create_ticket(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        phone="",                          # пустая строка вместо номера
        message=message.text,
    )
    await state.clear()

    await message.answer(
        f"✅ <b>Обращение #{ticket_id} создано!</b>\n\n"
        "Администратор ответит вам в ближайшее время. "
        "Ответ придёт сюда, в этот чат.",
        reply_markup=main_menu_kb(message.from_user.id in admin_ids)
    )

    # Уведомляем админов
    username = f"@{message.from_user.username}" if message.from_user.username else "—"
    notif = (
        f"📩 <b>НОВОЕ ОБРАЩЕНИЕ #{ticket_id}</b>\n\n"
        f"👤 {message.from_user.full_name}\n"
        f"🔗 {username}\n"
        f"🆔 <code>{message.from_user.id}</code>\n\n"
        f"💬 {message.text[:300]}"
    )
    for aid in admin_ids:
        try:
            await bot.send_message(aid, notif)
        except Exception:
            pass

@router.callback_query(F.data == "my_tickets")
async def my_tickets(cb: CallbackQuery):
    await cb.answer()
    tickets = await db.get_user_tickets(cb.from_user.id)
    if not tickets:
        await cb.message.edit_text(
            "📂 У вас пока нет обращений.",
            reply_markup=user_tickets_kb()
        )
        return

    text = "📂 <b>Ваши обращения:</b>\n\n"
    for t in tickets:
        emoji = "🟢" if t["status"] == "open" else "🔒"
        text += (
            f"{emoji} <b>#{t['id']}</b> — {t['message'][:50]}\n"
            f"   📅 {t['created_at'][:16]}\n\n"
        )
    await cb.message.edit_text(text, reply_markup=user_tickets_kb())
    # ============================================================
# ============================================================
# ОТПРАВКА КОДА
# ============================================================

@router.callback_query(F.data.startswith("sent_"))
async def sent_code_handler(cb: CallbackQuery, bot: Bot):
    """Пользователь нажал '📨 Отправил код'."""
    order_id = cb.data.replace("sent_", "")
    await cb.answer()

    # Сообщение "Ожидаю код…"
    await cb.message.edit_text(
        "⏳ <b>Ожидаю код…</b>\n\n"
        "Код придёт в течение 5–10 секунд.",
        reply_markup=None
    )

    # Ждём 5–10 секунд
    delay = random.randint(5, 10)
    await asyncio.sleep(delay)

    # Отправляем новый код
    code = generate_code()
    await bot.send_message(
        cb.from_user.id,
        f"🔔 <b>Новый код!</b>\n\n"
        f"<code>{code}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔄 Повторный код",
                callback_data=f"resend_{order_id}"
            )],
            [InlineKeyboardButton(
                text="✅ Готово",
                callback_data=f"done_{order_id}"
            )],
        ])
    )


@router.callback_query(F.data.startswith("resend_"))
async def resend_code_handler(cb: CallbackQuery, bot: Bot):
    """Кнопка '🔄 Повторный код'."""
    order_id = cb.data.replace("resend_", "")
    await cb.answer("Отправляю новый код…")

    delay = random.randint(5, 10)
    await asyncio.sleep(delay)

    code = generate_code()
    await bot.send_message(
        cb.from_user.id,
        f"🔔 <b>Новый код!</b>\n\n"
        f"<code>{code}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🔄 Повторный код",
                callback_data=f"resend_{order_id}"
            )],
            [InlineKeyboardButton(
                text="✅ Готово",
                callback_data=f"done_{order_id}"
            )],
        ])
    )


@router.callback_query(F.data.startswith("done_"))
async def done_handler(cb: CallbackQuery, bot: Bot, admin_ids: list):
    """Кнопка '✅ Готово'."""
    order_id = cb.data.replace("done_", "")
    await cb.answer("Готово!")

    await cb.message.edit_text(
        "✅ <b>Спасибо!</b>\n\n"
        "Если возникнут вопросы — напишите в поддержку.",
        reply_markup=None
    )

    # Уведомляем админов
    for aid in admin_ids:
        try:
            await bot.send_message(
                aid,
                f"✅ Пользователь <code>{cb.from_user.id}</code> "
                f"подтвердил получение кода по заказу "
                f"<code>{order_id}</code>."
            )
        except Exception:
            pass