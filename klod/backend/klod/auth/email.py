from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage


class EmailDeliveryError(RuntimeError):
    pass


def is_configured() -> bool:
    required = ("KLOD_SMTP_HOST", "KLOD_SMTP_FROM")
    return all(os.getenv(name, "").strip() for name in required)


def send_action_email(recipient: str, subject: str, text_body: str, html_body: str) -> None:
    if not is_configured():
        raise EmailDeliveryError("O envio de e-mails não está configurado no servidor.")

    host = os.environ["KLOD_SMTP_HOST"].strip()
    sender = os.environ["KLOD_SMTP_FROM"].strip()
    port = int(os.getenv("KLOD_SMTP_PORT", "587"))
    username = os.getenv("KLOD_SMTP_USERNAME", "").strip()
    password = os.getenv("KLOD_SMTP_PASSWORD", "")
    use_ssl = os.getenv("KLOD_SMTP_SSL", "false").lower() in {"1", "true", "yes"}
    use_starttls = os.getenv("KLOD_SMTP_STARTTLS", "true").lower() in {"1", "true", "yes"}

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context()) as server:
                if username:
                    server.login(username, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                if use_starttls:
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                if username:
                    server.login(username, password)
                server.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError) as error:
        raise EmailDeliveryError("Não foi possível enviar o e-mail. Verifique a configuração SMTP.") from error
