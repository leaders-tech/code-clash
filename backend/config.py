"""Load backend settings from .env and keep them in one Settings object.

Edit this file when env variables, ports, cookie names, or dev/prod defaults change.
Do not copy this file. Change it when the app configuration model changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_COOKIE_SECRET = "change-this-secret"


@dataclass(slots=True)
class Settings:
    mode: str
    host: str
    port: int
    db_path: Path
    cookie_secret: str
    frontend_origin: str
    admin_username: str = "admin"
    admin_password: str = "admin"
    bot_runner_mode: str = "docker"
    bot_runner_url: str = "http://bot-runner:8090"
    bot_runner_image: str = "code-clash-runner:local"
    bot_runner_container_name: str = "code-clash-bot-runner"
    access_cookie_name: str = "template_access"
    refresh_cookie_name: str = "template_refresh"
    access_ttl_seconds: int = 2 * 60 * 60
    refresh_ttl_seconds: int = 60 * 24 * 60 * 60

    @property
    def secure_cookies(self) -> bool:
        return self.mode == "prod"

    @property
    def allowed_origins(self) -> set[str]:
        origins = {self.frontend_origin.rstrip("/")}
        if self.mode != "prod":
            origins.add(f"http://{self.host}:{self.port}")
            parsed = urlsplit(self.frontend_origin)
            if parsed.hostname == "127.0.0.1":
                origins.add(urlunsplit((parsed.scheme, f"localhost:{parsed.port}", parsed.path, parsed.query, parsed.fragment)).rstrip("/"))
            if parsed.hostname == "localhost":
                origins.add(urlunsplit((parsed.scheme, f"127.0.0.1:{parsed.port}", parsed.path, parsed.query, parsed.fragment)).rstrip("/"))
        return origins

    @property
    def migrations_path(self) -> Path:
        return ROOT_DIR / "backend" / "migrations"


def load_settings() -> Settings:
    load_dotenv(ROOT_DIR / ".env")
    mode = os.getenv("APP_MODE", "dev").strip().lower()
    host = os.getenv("APP_HOST", "localhost").strip()
    port = int(os.getenv("APP_PORT", "3101"))
    db_path = Path(os.getenv("DB_PATH", "./dev.sqlite3")).expanduser()
    if not db_path.is_absolute():
        db_path = ROOT_DIR / db_path
    cookie_secret = os.getenv("COOKIE_SECRET", DEFAULT_COOKIE_SECRET)
    frontend_public_host = os.getenv("FRONTEND_PUBLIC_HOST", "localhost").strip()
    frontend_port = os.getenv("FRONTEND_PORT", "5101").strip()
    frontend_origin = os.getenv("FRONTEND_ORIGIN", f"http://{frontend_public_host}:{frontend_port}").rstrip("/")
    settings = Settings(
        mode=mode,
        host=host,
        port=port,
        db_path=db_path,
        cookie_secret=cookie_secret,
        frontend_origin=frontend_origin,
        admin_username=os.getenv("ADMIN_USERNAME", "admin").strip(),
        admin_password=os.getenv("ADMIN_PASSWORD", "admin" if mode == "dev" else ""),
        bot_runner_mode=os.getenv("BOT_RUNNER_MODE", "docker").strip().lower(),
        bot_runner_url=os.getenv("BOT_RUNNER_URL", "http://bot-runner:8090").strip().rstrip("/"),
        bot_runner_image=os.getenv("BOT_RUNNER_IMAGE", "code-clash-runner:local").strip(),
        bot_runner_container_name=os.getenv("BOT_RUNNER_CONTAINER_NAME", "code-clash-bot-runner").strip(),
    )
    validate_settings(settings)
    return settings


def validate_settings(settings: Settings) -> None:
    if settings.mode == "prod" and settings.cookie_secret == DEFAULT_COOKIE_SECRET:
        raise ValueError("Refusing to start in prod with the default COOKIE_SECRET. Set a real secret in .env or your deploy env.")
    if settings.mode == "prod" and (not settings.admin_username or not settings.admin_password):
        raise ValueError("Refusing to start in prod without ADMIN_USERNAME and ADMIN_PASSWORD.")
    if not settings.admin_username:
        raise ValueError("ADMIN_USERNAME is required.")
    if settings.bot_runner_mode not in {"docker", "service"}:
        raise ValueError("BOT_RUNNER_MODE must be docker or service.")
    if settings.bot_runner_mode == "service" and not settings.bot_runner_url:
        raise ValueError("BOT_RUNNER_URL is required when BOT_RUNNER_MODE=service.")
