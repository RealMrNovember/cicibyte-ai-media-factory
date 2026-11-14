from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from urllib.parse import urljoin, urlsplit

from mediafactory.core.net import FetchError, SafeFetcher
from mediafactory.sources.feeds import FeedError


@dataclass
class RawItem:
    external_id: str
    url: str | None
    title: str
    text: str
    author: str | None = None
    published_at: datetime | None = None
    language: str | None = None
    meta: dict = field(default_factory=dict)


class AdapterError(Exception):
    def __init__(self, message: str, *, retryable: bool):
        super().__init__(message)
        self.retryable = retryable


@dataclass
class FetchContext:
    fetcher: SafeFetcher
    credentials: dict | None = None


class Adapter(Protocol):
    key: str

    def validate(self, params: dict) -> dict: ...

    def fetch(self, params: dict, ctx: FetchContext) -> list[RawItem]: ...


ADAPTER_REGISTRY: dict[str, Adapter] = {}


def register(cls: Callable[[], Adapter]) -> Callable[[], Adapter]:
    instance = cls()
    ADAPTER_REGISTRY[instance.key] = instance
    return cls


def get_adapter(key: str) -> Adapter:
    try:
        return ADAPTER_REGISTRY[key]
    except KeyError:
        raise ValueError(f"unknown source adapter '{key}'; available: {', '.join(sorted(ADAPTER_REGISTRY))}") from None


@contextmanager
def translate_errors() -> Iterator[None]:
    """Turn fetch/parse failures into AdapterError with the right retry hint."""
    try:
        yield
    except FetchError as exc:
        raise AdapterError(str(exc), retryable=exc.retryable) from None
    except FeedError as exc:
        raise AdapterError(str(exc), retryable=False) from None


def resolve_link(base_url: str, link: str | None) -> str | None:
    """Absolute http(s) URL for a feed link (relative links resolved against the feed), else None."""
    if not link:
        return None
    absolute = urljoin(base_url, link.strip())
    parts = urlsplit(absolute)
    if parts.scheme not in ("http", "https") or not parts.hostname or len(absolute) > 2000:
        return None
    return absolute


def require_entries(entries: list) -> list:
    if not entries:
        raise AdapterError("feed returned no entries", retryable=True)
    return entries


# --- validation helpers ----------------------------------------------------------------------------------
def http_url(value: object, name: str = "url") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' is required")
    parts = urlsplit(value.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError(f"'{name}' must be an http(s) URL")
    return value.strip()


def int_in(params: dict, name: str, default: int, lo: int, hi: int) -> int:
    value = params.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
        raise ValueError(f"'{name}' must be an integer between {lo} and {hi}")
    return value


def choice(params: dict, name: str, default: str, options: tuple[str, ...]) -> str:
    value = params.get(name, default)
    if value not in options:
        raise ValueError(f"'{name}' must be one of: {', '.join(options)}")
    return value


def boolean(params: dict, name: str, default: bool) -> bool:
    value = params.get(name, default)
    if not isinstance(value, bool):
        raise ValueError(f"'{name}' must be true or false")
    return value
