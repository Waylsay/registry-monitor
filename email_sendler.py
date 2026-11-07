from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage
load_dotenv()
def send_email(subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = const.EMAIL_SENDER
    msg["To"] = const.EMAIL_RECEIVER
    msg.set_content(body)

    with smtplib.SMTP_SSL(const.SMTP_SERVER, const.SMTP_PORT, timeout=30) as smtp:
        smtp.login(const.EMAIL_SENDER, const.EMAIL_PASSWORD)
        smtp.send_message(msg)