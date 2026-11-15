"""Optional "made with" line in YouTube descriptions and Instagram captions (off unless you turn it on)."""

from sqlalchemy.orm import Session

from mediafactory.db.models import SystemSetting

KEY = "publish_credit"
LINES = {
    "en": "Made with CiciByte AI Media Factory — cicibyte.com",
    "tr": "CiciByte AI Media Factory ile üretildi — cicibyte.com",
}


def enabled(db: Session) -> bool:
    row = db.get(SystemSetting, KEY)
    return bool(row and isinstance(row.value, dict) and row.value.get("enabled"))


def set_enabled(db: Session, on: bool) -> None:
    row = db.get(SystemSetting, KEY)
    if row is None:
        db.add(SystemSetting(key=KEY, value={"enabled": on}))
    else:
        row.value = {"enabled": on}


def line(db: Session, language: str | None) -> str | None:
    return LINES.get(language or "en", LINES["en"]) if enabled(db) else None
