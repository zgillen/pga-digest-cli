import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.toml"


@dataclass
class TourConfig:
    name: str = "PGA Tour"


@dataclass
class EmailConfig:
    recipients: list[str] = field(default_factory=list)
    subject: str = "PGA Daily — {date}"
    subject_offseason: str = "PGA Weekly — {date}"
    transport: str = "gmail_smtp"


@dataclass
class NarratorConfig:
    model: str = "claude-sonnet-4-6"
    temperature: float = 0.7


@dataclass
class FeedsConfig:
    urls: list[str] = field(default_factory=list)


@dataclass
class AppConfig:
    tour: TourConfig
    email: EmailConfig
    narrator: NarratorConfig
    feeds: FeedsConfig
    anthropic_api_key: str
    datagolf_api_key: str
    gmail_address: str
    gmail_app_password: str


def load_config() -> AppConfig:
    with open(CONFIG_PATH, "rb") as f:
        raw = tomllib.load(f)

    recipients_env = os.getenv("EMAIL_RECIPIENTS", "")
    recipients = (
        [r.strip() for r in recipients_env.split(",") if r.strip()]
        if recipients_env
        else raw.get("email", {}).get("recipients", [])
    )

    return AppConfig(
        tour=TourConfig(**raw.get("tour", {})),
        email=EmailConfig(
            recipients=recipients,
            subject=raw.get("email", {}).get("subject", "PGA Daily — {date}"),
            subject_offseason=raw.get("email", {}).get("subject_offseason", "PGA Weekly — {date}"),
            transport=raw.get("email", {}).get("transport", "gmail_smtp"),
        ),
        narrator=NarratorConfig(**raw.get("narrator", {})),
        feeds=FeedsConfig(urls=raw.get("feeds", {}).get("urls", [])),
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        datagolf_api_key=os.environ["DATAGOLF_API_KEY"],
        gmail_address=os.environ["GMAIL_ADDRESS"],
        gmail_app_password=os.environ["GMAIL_APP_PASSWORD"],
    )
