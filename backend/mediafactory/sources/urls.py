"""Canonical URLs so the same content reached through different links is stored once."""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING = re.compile(r"^(utm_.*|fbclid|gclid|mc_cid|mc_eid|ref|ref_src|share_id|igshid|si)$", re.IGNORECASE)
_REDDIT_HOSTS = {"reddit.com", "old.reddit.com", "new.reddit.com", "np.reddit.com", "m.reddit.com", "i.reddit.com"}
_REDDIT_POST = re.compile(r"^/r/([A-Za-z0-9_]+)/comments/([A-Za-z0-9]+)", re.IGNORECASE)


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host in _REDDIT_HOSTS:
        m = _REDDIT_POST.match(parts.path)
        if m:
            return f"https://reddit.com/r/{m.group(1).lower()}/comments/{m.group(2).lower()}"
        host = "reddit.com"
    netloc = host if parts.port in (None, 80, 443) else f"{host}:{parts.port}"
    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/") or "/"
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _TRACKING.match(k)))
    return urlunsplit((scheme, netloc, path, query, ""))
