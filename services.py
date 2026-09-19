# ============================================================
# НАСТРОЙКА УСЛУГ — МЕНЯЙ ЗДЕСЬ НАЗВАНИЯ И ЦЕНЫ
# ============================================================

SERVICES = {
    "basic": {
        "name": " MAX ",
        "description": "Получение номера для регистрации MAX",
        "price_usdt": 3.0,
        "emoji": "",
        "delivery_type": "phone" ,
        "delivery_content": "",
    },
    "standard": {
        "name": " VKонтакте",
        "description": "Получение номера для регистрации VK",
        "price_usdt": 0.5,
        "emoji": "",
        "delivery_type": "phone",       
        "delivery_content": "",
    },
    "premium": {
        "name": " Telegram",
        "description": "Получение номера для регистрации Telegram",
        "price_usdt": 0.7,
        "emoji": "",
        "delivery_type": "phone",      
        "delivery_content": "",
    },
    # Добавляй свои услуги сюда:
        "whatsapp": {
        "name": "WhatsApp",
        "description": "Получение номера для регистрации WhatsApp",
        "price_usdt": 1.0,
        "emoji": "",
        "delivery_type": "phone",      
        "delivery_content": "",
    },
}

# Валюта для оплаты (USDT, TON, BTC, ETH и др.)
PAYMENT_ASSET = "USDT"

# ============================================================