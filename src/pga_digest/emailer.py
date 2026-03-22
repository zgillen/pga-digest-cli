import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown

from .config import AppConfig


def send_email(config: AppConfig, subject: str, body_markdown: str) -> None:
    body_html = markdown.markdown(body_markdown)

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
