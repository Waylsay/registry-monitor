import requests
from dotenv import load_dotenv
load_dotenv()
TELEGRAM_URL = f"https://api.telegram.org/bot{const.TELEGRAM_BOT_TOKEN}/sendMessage"

def send_telegram(message):
    response = requests.post(
        TELEGRAM_URL,
        json={
            "chat_id": const.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        },
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(f"Ошибка Telegram: {result}")