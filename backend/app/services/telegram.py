import requests
from flask import current_app


def send_telegram(message: str) -> bool:
    token, chat_id = current_app.config.get("TELEGRAM_BOT_TOKEN"), current_app.config.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id: return False
    try:
        response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": message}, timeout=8)
        response.raise_for_status(); return True
    except requests.RequestException:
        current_app.logger.exception("Unable to send Telegram notification")
        return False
