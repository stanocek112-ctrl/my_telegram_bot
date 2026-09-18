from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

import database as db
from services import PAYMENT_ASSET
from keyboards import (
    admin_main_kb, admin_services_kb, admin_service_edit_kb,
    admin_back_kb, cancel_kb,
    admin_tickets_kb, admin_ticket_view_kb,
)
router = Router()


# ---------- FSM ----------

class AdminSG(StatesGroup):
    edit_price = State()
    edit_name = State()
    edit_content = State()
    add_key = State()
    add_name = State()
    add_desc = State()
    add_price = State()
    add_emoji = State()
    add_dtype = State()
    add_content = State()
    broadcast_text = State()
    ticket_reply = State()


def is_admin(user_id: int, admin_ids: list) -> bool:
    return user_id in admin_ids


# ---------- Вход в панель ----------

@router.message(Command("admin"))
@router.message(F.text == "🎛 Админ-панель")
async def admin_panel(message: Message, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    cnt = await db.count_open_tickets()
    await message.answer(
        "🎛 <b>Админ-панель</b>\n\nВыбери действие:",
        reply_markup=admin_main_kb(cnt)
    )

@router.callback_query(F.data == "adm_back")
async def adm_back(cb: CallbackQuery, state: FSMContext, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    await state.clear()
    cnt = await db.count_open_tickets()
    await cb.message.edit_text(
        "🎛 <b>Админ-панель</b>\n\nВыбери действие:",
        reply_markup=admin_main_kb(cnt)
    )


# ---------- Статистика ----------

@router.callback_query(F.data == "adm_stats")
async def adm_stats(cb: CallbackQuery, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    stats = await db.get_stats()
    users = await db.count_users()
    await cb.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{users}</b>\n"
        f"🧾 Оплаченных заказов: <b>{stats['orders']}</b>\n"
        f"💰 Общая выручка: <b>{stats['revenue']:.2f} {PAYMENT_ASSET}</b>",
        reply_markup=admin_back_kb()
    )


# ---------- Список услуг ----------

@router.callback_query(F.data == "adm_services")
async def adm_services(cb: CallbackQuery, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    services = await db.get_all_services()
    await cb.message.edit_text(
        "🛍 <b>Управление услугами</b>\n\nНажми на услугу для редактирования:",
        reply_markup=admin_services_kb(services)
    )


# ---------- Редактирование одной услуги ----------

@router.callback_query(F.data.startswith("adm_svc_"))
async def adm_svc_view(cb: CallbackQuery, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    key = cb.data.replace("adm_svc_", "")
    s = await db.get_service(key)
    if not s:
        await cb.answer("Не найдено", show_alert=True)
        return

    content_preview = (s["delivery_content"] or "")[:80]
    text = (
        f"<b>{s['emoji']} {s['name']}</b>\n\n"
        f"🔑 Ключ: <code>{s['key']}</code>\n"
        f"📝 {s['description']}\n"
        f"💰 Цена: <b>{s['price_usdt']} {PAYMENT_ASSET}</b>\n"
        f"📦 Тип выдачи: <code>{s['delivery_type']}</code>\n"
        f"📄 Выдача: <i>{content_preview}</i>"
    )
    await cb.message.edit_text(text, reply_markup=admin_service_edit_kb(key))


# ---------- Изменить цену ----------

@router.callback_query(F.data.startswith("adm_edit_price_"))
async def adm_edit_price_start(cb: CallbackQuery, state: FSMContext, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    key = cb.data.replace("adm_edit_price_", "")
    await state.update_data(key=key)
    await state.set_state(AdminSG.edit_price)
    await cb.message.edit_text("💰 Введите новую цену (число):", reply_markup=cancel_kb())


@router.message(AdminSG.edit_price)
async def adm_edit_price_save(message: Message, state: FSMContext, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введите число, например: 15.5")
        return
    data = await state.get_data()
    await db.update_service_price(data["key"], price)
    await state.clear()
    await message.answer(f"✅ Цена обновлена: {price} {PAYMENT_ASSET}",
                         reply_markup=admin_back_kb())


# ---------- Изменить название ----------

@router.callback_query(F.data.startswith("adm_edit_name_"))
async def adm_edit_name_start(cb: CallbackQuery, state: FSMContext, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    key = cb.data.replace("adm_edit_name_", "")
    await state.update_data(key=key)
    await state.set_state(AdminSG.edit_name)
    await cb.message.edit_text("📝 Введите новое название:", reply_markup=cancel_kb())


@router.message(AdminSG.edit_name)
async def adm_edit_name_save(message: Message, state: FSMContext, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    data = await state.get_data()
    await db.update_service_name(data["key"], message.text)
    await state.clear()
    await message.answer("✅ Название обновлено", reply_markup=admin_back_kb())


# ---------- Изменить выдачу ----------

@router.callback_query(F.data.startswith("adm_edit_content_"))
async def adm_edit_content_start(cb: CallbackQuery, state: FSMContext, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    key = cb.data.replace("adm_edit_content_", "")
    await state.update_data(key=key)
    await state.set_state(AdminSG.edit_content)
    await cb.message.edit_text(
        "📦 Отправьте:\n"
        "• Текст — что выдать пользователю\n"
        "• Или ссылку (http...)\n"
        "• Или файл (прикрепите документ — я сохраню file_id)",
        reply_markup=cancel_kb()
    )


@router.message(AdminSG.edit_content, F.document)
async def adm_edit_content_file(message: Message, state: FSMContext, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    data = await state.get_data()
    file_id = message.document.file_id
    await db.update_service_content(data["key"], file_id)
    # Меняем тип на file
    async with __import__("aiosqlite").connect("shop.db") as con:
        await con.execute("UPDATE services SET delivery_type='file' WHERE key=?",
                          (data["key"],))
        await con.commit()
    await state.clear()
    await message.answer("✅ Файл сохранён и будет выдаваться автоматически",
                         reply_markup=admin_back_kb())


@router.message(AdminSG.edit_content)
async def adm_edit_content_text(message: Message, state: FSMContext, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    data = await state.get_data()
    content = message.text
    dtype = "link" if content.startswith("http") else "text"
    await db.update_service_content(data["key"], content)
    async with __import__("aiosqlite").connect("shop.db") as con:
        await con.execute("UPDATE services SET delivery_type=? WHERE key=?",
                          (dtype, data["key"]))
        await con.commit()
    await state.clear()
    await message.answer(f"✅ Выдача обновлена (тип: {dtype})",
                         reply_markup=admin_back_kb())


# ---------- Удаление ----------

@router.callback_query(F.data.startswith("adm_del_"))
async def adm_delete(cb: CallbackQuery, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    key = cb.data.replace("adm_del_", "")
    await db.delete_service(key)
    services = await db.get_all_services()
    await cb.message.edit_text("🗑 Услуга удалена.\n\n🛍 Список услуг:",
                               reply_markup=admin_services_kb(services))


# ---------- Добавление услуги ----------

@router.callback_query(F.data == "adm_add_svc")
async def adm_add_start(cb: CallbackQuery, state: FSMContext, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    await state.set_state(AdminSG.add_key)
    await cb.message.edit_text(
        "➕ <b>Добавление услуги</b>\n\n"
        "Шаг 1/6 — введите <b>ключ</b> (латиница, без пробелов, уникальный):\n"
        "Например: <code>vip_support</code>",
        reply_markup=cancel_kb()
    )


@router.message(AdminSG.add_key)
async def adm_add_key(message: Message, state: FSMContext, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    key = message.text.strip().lower().replace(" ", "_")
    if await db.get_service(key):
        await message.answer("Такой ключ уже есть. Введите другой.")
        return
    await state.update_data(key=key)
    await state.set_state(AdminSG.add_name)
    await message.answer("Шаг 2/6 — введите <b>название</b> услуги:")


@router.message(AdminSG.add_name)
async def adm_add_name(message: Message, state: FSMContext, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    await state.update_data(name=message.text)
    await state.set_state(AdminSG.add_desc)
    await message.answer("Шаг 3/6 — введите <b>описание</b>:")


@router.message(AdminSG.add_desc)
async def adm_add_desc(message: Message, state: FSMContext, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    await state.update_data(description=message.text)
    await state.set_state(AdminSG.add_price)
    await message.answer("Шаг 4/6 — введите <b>цену</b> в USDT (число):")


@router.message(AdminSG.add_price)
async def adm_add_price(message: Message, state: FSMContext, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введите число.")
        return
    await state.update_data(price=price)
    await state.set_state(AdminSG.add_emoji)
    await message.answer("Шаг 5/6 — пришлите <b>эмодзи</b> (один символ):")


@router.message(AdminSG.add_emoji)
async def adm_add_emoji(message: Message, state: FSMContext, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    await state.update_data(emoji=message.text.strip()[:4])
    await state.set_state(AdminSG.add_content)
    await message.answer(
        "Шаг 6/6 — что <b>выдавать</b> после оплаты?\n\n"
        "• Отправьте текст/ссылку\n"
        "• Или прикрепите файл (я сохраню автоматически)"
    )


@router.message(AdminSG.add_content, F.document)
async def adm_add_content_file(message: Message, state: FSMContext, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    d = await state.get_data()
    await db.add_service(d["key"], d["name"], d["description"], d["price"],
                         d["emoji"], "file", message.document.file_id)
    await state.clear()
    await message.answer("✅ Услуга создана с файловой выдачей!",
                         reply_markup=admin_back_kb())


@router.message(AdminSG.add_content)
async def adm_add_content_text(message: Message, state: FSMContext, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    d = await state.get_data()
    content = message.text
    dtype = "link" if content.startswith("http") else "text"
    await db.add_service(d["key"], d["name"], d["description"], d["price"],
                         d["emoji"], dtype, content)
    await state.clear()
    await message.answer("✅ Услуга создана!", reply_markup=admin_back_kb())


# ---------- Рассылка ----------

@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast_start(cb: CallbackQuery, state: FSMContext, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    await state.set_state(AdminSG.broadcast_text)
    await cb.message.edit_text(
        "📢 <b>Рассылка</b>\n\nПришлите сообщение — оно уйдёт всем пользователям.\n"
        "Поддерживается HTML (<b>жирный</b>, <i>курсив</i>, <a href='#'>ссылка</a>).",
        reply_markup=cancel_kb()
    )


@router.message(AdminSG.broadcast_text)
async def adm_broadcast_send(message: Message, state: FSMContext, bot: Bot, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    await state.clear()
    users = await db.get_all_users()
    ok, fail = 0, 0
    status = await message.answer(f"⏳ Отправляю {len(users)} пользователям...")
    for uid in users:
        try:
            await bot.send_message(uid, message.html_text)
            ok += 1
        except Exception:
            fail += 1
    await status.edit_text(f"✅ Рассылка завершена.\n\nДоставлено: {ok}\nОшибок: {fail}")


# ---------- Последние заказы ----------

@router.callback_query(F.data == "adm_orders")
async def adm_orders(cb: CallbackQuery, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    import aiosqlite
    async with aiosqlite.connect("shop.db") as con:
        con.row_factory = aiosqlite.Row
        async with con.execute(
            "SELECT * FROM orders WHERE status='paid' ORDER BY paid_at DESC LIMIT 15"
        ) as cur:
            rows = [dict(r) async for r in cur]

    if not rows:
        await cb.message.edit_text("Пока нет оплаченных заказов.",
                                   reply_markup=admin_back_kb())
        return

    text = "📋 <b>Последние оплаченные заказы:</b>\n\n"
    for r in rows:
        text += (
            f"🧾 <code>{r['payload']}</code>\n"
            f"👤 <code>{r['user_id']}</code> • 📦 {r['service_name']}\n"
            f"💵 {r['amount']} {PAYMENT_ASSET}\n"
            f"📅 {r['paid_at'][:16]}\n\n"
        )
    await cb.message.edit_text(text, reply_markup=admin_back_kb())
    # ============================================================
# ОБРАЩЕНИЯ (ТИКЕТЫ)
# ============================================================

@router.callback_query(F.data == "adm_tickets")
async def adm_tickets_list(cb: CallbackQuery, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    tickets = await db.get_open_tickets()
    if not tickets:
        await cb.message.edit_text(
            "📩 Открытых обращений нет.",
            reply_markup=admin_back_kb()
        )
        return
    await cb.message.edit_text(
        f"📩 <b>Открытые обращения ({len(tickets)}):</b>\n\n"
        "Нажмите на обращение, чтобы открыть:",
        reply_markup=admin_tickets_kb(tickets)
    )


@router.callback_query(F.data.startswith("adm_ticket_"))
async def adm_ticket_view(cb: CallbackQuery, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    ticket_id = int(cb.data.replace("adm_ticket_", ""))
    t = await db.get_ticket(ticket_id)
    if not t:
        await cb.answer("Обращение не найдено", show_alert=True)
        return

    status = "🟢 Открыто" if t["status"] == "open" else "🔒 Закрыто"
    username = f"@{t['username']}" if t["username"] else "—"
    text = (
        f"📩 <b>Обращение #{t['id']}</b>\n"
        f"Статус: {status}\n\n"
        f"👤 {t['full_name']}\n"
        f"🔗 {username}\n"
        f"🆔 <code>{t['user_id']}</code>\n"
        f"📅 {t['created_at'][:16]}\n\n"
        f"💬 <b>Сообщение:</b>\n{t['message']}"
    )
    await cb.message.edit_text(
        text,
        reply_markup=admin_ticket_view_kb(ticket_id, t["status"] == "open")
    )


@router.callback_query(F.data.startswith("adm_reply_"))
async def adm_ticket_reply_start(cb: CallbackQuery, state: FSMContext, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    ticket_id = int(cb.data.replace("adm_reply_", ""))
    await state.update_data(ticket_id=ticket_id)
    await state.set_state(AdminSG.ticket_reply)
    await cb.message.edit_text(
        f"✍️ <b>Ответ на обращение #{ticket_id}</b>\n\n"
        "Напишите текст ответа. Он будет отправлен пользователю "
        "от лица бота.",
        reply_markup=cancel_kb()
    )


@router.message(AdminSG.ticket_reply)
async def adm_ticket_reply_send(message: Message, state: FSMContext,
                                 bot: Bot, admin_ids: list):
    if not is_admin(message.from_user.id, admin_ids):
        return
    data = await state.get_data()
    ticket_id = data["ticket_id"]
    t = await db.get_ticket(ticket_id)
    if not t:
        await state.clear()
        await message.answer("Обращение не найдено.", reply_markup=admin_back_kb())
        return

    # Сохраняем в историю
    await db.add_ticket_message(ticket_id, from_admin=True, text=message.text)

    # Отправляем пользователю
    try:
        await bot.send_message(
            t["user_id"],
            f"📩 <b>Ответ по обращению #{ticket_id}</b>\n\n"
            f"{message.text}\n\n"
            f"<i>Это сообщение от администратора. "
            f"Если нужно — ответьте, создав новое обращение.</i>"
        )
        await message.answer(
            f"✅ Ответ отправлен пользователю {t['full_name']}.",
            reply_markup=admin_back_kb()
        )
    except Exception as e:
        await message.answer(
            f"❌ Не удалось отправить: {e}\n"
            "Возможно, пользователь заблокировал бота.",
            reply_markup=admin_back_kb()
        )

    await state.clear()


@router.callback_query(F.data.startswith("adm_close_"))
async def adm_ticket_close(cb: CallbackQuery, bot: Bot, admin_ids: list):
    if not is_admin(cb.from_user.id, admin_ids):
        return
    ticket_id = int(cb.data.replace("adm_close_", ""))
    t = await db.get_ticket(ticket_id)
    if not t:
        await cb.answer("Не найдено", show_alert=True)
        return

    await db.close_ticket(ticket_id)

    # Уведомляем пользователя
    try:
        await bot.send_message(
            t["user_id"],
            f"🔒 <b>Обращение #{ticket_id} закрыто.</b>\n\n"
            "Если появятся новые вопросы — создайте новое обращение."
        )
    except Exception:
        pass

    await cb.answer("Обращение закрыто", show_alert=True)

    # Обновляем список открытых
    tickets = await db.get_open_tickets()
    if not tickets:
        await cb.message.edit_text(
            "📩 Открытых обращений нет.",
            reply_markup=admin_back_kb()
        )
    else:
        await cb.message.edit_text(
            f"📩 <b>Открытые обращения ({len(tickets)}):</b>",
            reply_markup=admin_tickets_kb(tickets)
        )