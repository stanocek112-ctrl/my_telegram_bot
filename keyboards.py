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
        [InlineKeyboardButton(text="📊 Статистика",
                              callback_data="adm_stats")],
        [InlineKeyboardButton(text="🛍 Управление услугами",
                              callback_data="adm_services")],
        [InlineKeyboardButton(text=tickets_label,
                              callback_data="adm_tickets")],
        [InlineKeyboardButton(text="💰 Балансы",
                              callback_data="adm_balances")],   # 👈
        [InlineKeyboardButton(text="🚫 Пользователи",
                              callback_data="adm_users")],
        [InlineKeyboardButton(text="📢 Рассылка",
                              callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="📋 Последние заказы",
                              callback_data="adm_orders")],
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
        [KeyboardButton(text="💰 Мой баланс"),
         KeyboardButton(text="📦 Мои покупки")],
        [KeyboardButton(text="📩 Написать в поддержку")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="🎛 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
# ---------- Тикеты ----------

def admin_tickets_kb(tickets: list):
    buttons = []
    for t in tickets:
        # Безопасное имя
        if t.get("username"):
            username = f"@{t['username']}"
        else:
            username = t.get("full_name") or f"ID{t['user_id']}"

        # Безопасное превью — защита от None и обрезка
        raw = t.get("message") or "(пусто)"
        preview = raw[:25].replace("\n", " ")
        if len(raw) > 25:
            preview += "..."

        # Обрезаем по 64 символа (лимит Telegram для кнопки)
        button_text = f"#{t['id']} • {username} • {preview}"[:64]

        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"adm_ticket_{t['id']}"
        )])
    buttons.append([InlineKeyboardButton(
        text="« Назад", callback_data="adm_back"
    )])
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
# ============================================================
# БАЛАНС
# ============================================================

def balance_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Пополнить",
                              callback_data="balance_topup")],
        [InlineKeyboardButton(text="📜 История",
                              callback_data="balance_history")],
    ])


def topup_amounts_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 USDT", callback_data="topup_5"),
         InlineKeyboardButton(text="10 USDT", callback_data="topup_10")],
        [InlineKeyboardButton(text="25 USDT", callback_data="topup_25"),
         InlineKeyboardButton(text="50 USDT", callback_data="topup_50")],
        [InlineKeyboardButton(text="✏️ Своя сумма",
                              callback_data="topup_custom")],
        [InlineKeyboardButton(text="« Назад",
                              callback_data="balance_back")],
    ])


def payment_choice_kb(service_key: str, balance: float, price: float):
    rows = []
    if balance >= price:
        rows.append([InlineKeyboardButton(
            text=f"💰 Оплатить с баланса ({balance:.2f} USDT)",
            callback_data=f"paybal_{service_key}"
        )])
    else:
        rows.append([InlineKeyboardButton(
            text=f"💰 Баланс: {balance:.2f} USDT (не хватает)",
            callback_data="balance_topup"
        )])
    rows.append([InlineKeyboardButton(
        text="💳 Оплатить криптой",
        callback_data=f"pay_{service_key}"
    )])
    rows.append([InlineKeyboardButton(
        text="« Назад", callback_data="back_to_services"
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_balances_kb(balances: list):
    buttons = []
    for b in balances:
        username = f"@{b['username']}" if b["username"] else b["full_name"]
        buttons.append([InlineKeyboardButton(
            text=f"{username} — {b['amount']:.2f} USDT",
            callback_data=f"adm_bal_{b['user_id']}"
        )])
    buttons.append([InlineKeyboardButton(
        text="« Назад", callback_data="adm_back"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_balance_view_kb(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Начислить",
                              callback_data=f"adm_bal_add_{user_id}")],
        [InlineKeyboardButton(text="➖ Списать",
                              callback_data=f"adm_bal_sub_{user_id}")],
        [InlineKeyboardButton(text="« К списку",
                              callback_data="adm_balances")],
    ])
def admin_balances_kb(balances: list):
    buttons = []
    for b in balances:
        username = f"@{b['username']}" if b["username"] else b["full_name"]
        buttons.append([InlineKeyboardButton(
            text=f"{username} — {b['amount']:.2f} USDT",
            callback_data=f"adm_bal_{b['user_id']}"
        )])
    buttons.append([InlineKeyboardButton(
        text="« Назад", callback_data="adm_back"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_balance_view_kb(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Начислить",
                              callback_data=f"adm_bal_add_{user_id}")],
        [InlineKeyboardButton(text="➖ Списать",
                              callback_data=f"adm_bal_sub_{user_id}")],
        [InlineKeyboardButton(text="« К списку",
                              callback_data="adm_balances")],
    ])


def admin_users_kb(users: list):
    buttons = []
    for u in users:
        username = f"@{u['username']}" if u["username"] else u["full_name"]
        mark = "🚫" if u["blocked"] else "✅"
        buttons.append([InlineKeyboardButton(
            text=f"{mark} {username} ({u['user_id']})",
            callback_data=f"adm_user_{u['user_id']}"
        )])
    buttons.append([InlineKeyboardButton(
        text="« Назад", callback_data="adm_back"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_user_view_kb(user_id: int, blocked: bool):
    rows = []
    if blocked:
        rows.append([InlineKeyboardButton(
            text="✅ Разблокировать",
            callback_data=f"adm_unblock_{user_id}"
        )])
    else:
        rows.append([InlineKeyboardButton(
            text="🚫 Заблокировать",
            callback_data=f"adm_block_{user_id}"
        )])
    rows.append([InlineKeyboardButton(
        text="« К списку", callback_data="adm_users"
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)
