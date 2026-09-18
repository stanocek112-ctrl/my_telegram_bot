from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)


def services_kb(services: list, asset: str = "USDT"):
    buttons = []
    for s in services:
        buttons.append([InlineKeyboardButton(
            text=f"{s['emoji']} {s['name']} — {s['price_usdt']} {asset}",
            callback_data=f"buy_{s['key']}"
        )])
    buttons.append([InlineKeyboardButton(text="📦 Мои покупки", callback_data="my_orders")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад", callback_data="back_to_services")]
    ])


def admin_main_kb(open_tickets: int = 0):
    tickets_label = f"📩 Обращения ({open_tickets})" if open_tickets else "📩 Обращения"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats")],
        [InlineKeyboardButton(text="🛍 Управление услугами", callback_data="adm_services")],
        [InlineKeyboardButton(text=tickets_label, callback_data="adm_tickets")],  # 👈 НОВАЯ
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="📋 Последние заказы", callback_data="adm_orders")],
    ])


def admin_services_kb(services: list):
    buttons = [[InlineKeyboardButton(
        text=f"{s['emoji']} {s['name']} ({s['price_usdt']})",
        callback_data=f"adm_svc_{s['key']}"
    )] for s in services]
    buttons.append([InlineKeyboardButton(text="➕ Добавить услугу", callback_data="adm_add_svc")])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="adm_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_service_edit_kb(key: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"adm_edit_price_{key}")],
        [InlineKeyboardButton(text="📝 Изменить название", callback_data=f"adm_edit_name_{key}")],
        [InlineKeyboardButton(text="📦 Изменить выдачу", callback_data=f"adm_edit_content_{key}")],
        [InlineKeyboardButton(text="🗑 Удалить услугу", callback_data=f"adm_del_{key}")],
        [InlineKeyboardButton(text="« Назад", callback_data="adm_services")],
    ])


def admin_back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« В админ-панель", callback_data="adm_back")]
    ])


def cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_back")]
    ])


def main_menu_kb(is_admin: bool = False):
    rows = [
        [KeyboardButton(text="🛍 Каталог услуг")],
        [KeyboardButton(text="📦 Мои покупки"), KeyboardButton(text="🆘 Помощь")],
        [KeyboardButton(text="📩 Написать в поддержку")],   # 👈 НОВАЯ КНОПКА
    ]
    if is_admin:
        rows.append([KeyboardButton(text="🎛 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
# ---------- Тикеты ----------

def admin_tickets_kb(tickets: list):
    buttons = []
    for t in tickets:
        username = f"@{t['username']}" if t["username"] else t["full_name"]
        preview = t["message"][:30] + ("..." if len(t["message"]) > 30 else "")
        buttons.append([InlineKeyboardButton(
            text=f"#{t['id']} • {username} • {preview}",
            callback_data=f"adm_ticket_{t['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="adm_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_ticket_view_kb(ticket_id: int, is_open: bool):
    rows = [
        [InlineKeyboardButton(
            text="✍️ Ответить",
            callback_data=f"adm_reply_{ticket_id}"
        )],
    ]
    if is_open:
        rows.append([InlineKeyboardButton(
            text="🔒 Закрыть обращение",
            callback_data=f"adm_close_{ticket_id}"
        )])
    rows.append([InlineKeyboardButton(text="« К списку", callback_data="adm_tickets")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def user_tickets_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать обращение", callback_data="new_ticket")],
        [InlineKeyboardButton(text="📂 Мои обращения", callback_data="my_tickets")],
    ])


