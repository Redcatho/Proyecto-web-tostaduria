import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(recipient: str | None, subject: str, html_body: str) -> bool:
    config = current_app.config
    if not recipient or not all((config.get("MAIL_SERVER"), config.get("MAIL_DEFAULT_SENDER"))):
        return False
    message = EmailMessage()
    message["Subject"] = subject; message["From"] = config["MAIL_DEFAULT_SENDER"]; message["To"] = recipient
    message.set_content("Consulta este mensaje en un cliente compatible con HTML.")
    message.add_alternative(html_body, subtype="html")
    try:
        with smtplib.SMTP(config["MAIL_SERVER"], config["MAIL_PORT"], timeout=10) as server:
            if config["MAIL_USE_TLS"]: server.starttls()
            if config.get("MAIL_USERNAME"): server.login(config["MAIL_USERNAME"], config.get("MAIL_PASSWORD") or "")
            server.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        current_app.logger.exception("Unable to send transactional email")
        return False
