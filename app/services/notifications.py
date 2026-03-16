import smtplib
from email.message import EmailMessage

from app.core.config import settings


class NotificationService:
    def send_email(self, to_email: str, subject: str, body: str) -> None:
        if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password or not settings.smtp_from:
            return

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)


notification_service = NotificationService()

