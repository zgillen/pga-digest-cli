import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import AppConfig

PRIMARY_COLOR = "#1a5c38"
ACCENT_COLOR  = "#c9a84c"


def _markdown_to_html(md: str) -> str:
    md = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    md = re.sub(r"^### (.+)$", r'<h3>\1</h3>', md, flags=re.MULTILINE)
    md = re.sub(r"^## (.+)$",  r'<h2>\1</h2>', md, flags=re.MULTILINE)
    md = re.sub(r"^# (.+)$",   r'<h1>\1</h1>', md, flags=re.MULTILINE)
    md = re.sub(r"\*\*(.+?)\*\*", r'<strong>\1</strong>', md)
    md = re.sub(r"\*([^*\n]+?)\*", r'<em>\1</em>', md)
    md = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', md)
    md = re.sub(r"^---$", r'<hr>', md, flags=re.MULTILINE)
    def replace_list_block(m):
        items = re.findall(r"^[-*] (.+)$", m.group(0), re.MULTILINE)
        lis = "".join(f"<li>{i}</li>" for i in items)
        return f"<ul>{lis}</ul>"
    md = re.sub(r"(^[-*] .+$\n?)+", replace_list_block, md, flags=re.MULTILINE)
    lines = md.split("\n")
    out = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<"):
            out.append(stripped)
        else:
            out.append(f"<p>{stripped}</p>")
    return "\n".join(out)


def _apply_styles(html: str) -> str:
    html = re.sub(r"<h1(.*?)>",
        rf'<h1\1 style="color:{PRIMARY_COLOR};margin-top:20px;">', html)
    html = re.sub(r"<h2(.*?)>",
        rf'<h2\1 style="color:{PRIMARY_COLOR};border-bottom:2px solid {ACCENT_COLOR};padding-bottom:5px;margin-top:25px;">', html)
    html = re.sub(r"<h3(.*?)>",
        rf'<h3\1 style="color:{PRIMARY_COLOR};margin-top:15px;">', html)
    html = re.sub(r"<a ",
        f'<a style="color:{ACCENT_COLOR};text-decoration:underline;" ', html)
    html = re.sub(r"<ul>",
        '<ul style="padding-left:20px;line-height:1.8;">', html)
    return html


def _build_html(body_md: str) -> str:
    body_html = _apply_styles(_markdown_to_html(body_md))
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background-color:#f5f5f5;">
  <div style="max-width:600px;margin:0 auto;background-color:#ffffff;padding:0;">
    <div style="background-color:{PRIMARY_COLOR};color:#ffffff;padding:20px 30px;">
      <h1 style="margin:0;font-size:24px;color:#ffffff;">⛳ PGA Tour Digest</h1>
    </div>
    <div style="padding:20px 30px;color:#333333;line-height:1.6;font-size:16px;">
      {body_html}
    </div>
    <div style="background-color:#f0f0f0;padding:15px 30px;font-size:12px;color:#888888;">
      Sources: DataGolf API, RSS feeds. Narrated by Claude Sonnet.
    </div>
  </div>
</body>
</html>"""


def _build_text(body_md: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", body_md)
    text = re.sub(r"\*([^*\n]+?)\*", r"\1", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)
    text = re.sub(r"^#{1,3} ", "", text, flags=re.MULTILINE)
    return text.strip() + "\n\n---\nSources: DataGolf API, RSS feeds. Narrated by Claude Sonnet."


def send_email(config: AppConfig, subject: str, body_markdown: str) -> None:
    html = _build_html(body_markdown)
    text = _build_text(body_markdown)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = config.gmail_address
    msg["To"]      = ", ".join(config.email.recipients)
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html",  "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.gmail_address, config.gmail_app_password)
        server.sendmail(config.gmail_address, config.email.recipients, msg.as_string())

    print(f"Email sent to: {', '.join(config.email.recipients)}")
