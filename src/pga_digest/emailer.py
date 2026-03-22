import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import AppConfig


def send_email(config: AppConfig, subject: str, body_markdown: str) -> None:
    body_html = f"<pre style='font-family: sans-serif; white-space: pre-wrap'>{body_markdown}</pre>"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.gmail_address
    msg["To"] = ", ".join(config.email.recipients)

    msg.attach(MIMEText(body_markdown, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.gmail_address, config.gmail_app_password)
        server.sendmail(
            config.gmail_address,
            config.email.recipients,
            msg.as_string(),
        )

    print(f"Email sent to: {', '.join(config.email.recipients)}")
