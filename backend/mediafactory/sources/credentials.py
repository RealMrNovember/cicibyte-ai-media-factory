"""Source credentials (e.g. the Reddit API app), stored encrypted in system_settings."""

from sqlalchemy.orm import Session

from mediafactory.core.crypto import SecretDecryptError, decrypt, encrypt
from mediafactory.db.models import SystemSetting

REDDIT_KEY = "credentials.reddit"


def get_reddit_credentials(session: Session) -> dict | None:
    row = session.get(SystemSetting, REDDIT_KEY)
    value = row.value if row else None
    if not isinstance(value, dict) or not value.get("client_id") or not value.get("client_secret_enc"):
        return None
    try:
        secret = decrypt(value["client_secret_enc"])
    except SecretDecryptError:
        return None
    return {"client_id": value["client_id"], "client_secret": secret}


def set_reddit_credentials(session: Session, client_id: str, client_secret: str) -> None:
    value = {"client_id": client_id, "client_secret_enc": encrypt(client_secret)}
    row = session.get(SystemSetting, REDDIT_KEY)
    if row is None:
        session.add(SystemSetting(key=REDDIT_KEY, value=value))
    else:
        row.value = value
    session.flush()


def delete_reddit_credentials(session: Session) -> None:
    row = session.get(SystemSetting, REDDIT_KEY)
    if row is not None:
        session.delete(row)
        session.flush()


def credentials_for(session: Session, adapter: str) -> dict | None:
    return get_reddit_credentials(session) if adapter == "reddit" else None
