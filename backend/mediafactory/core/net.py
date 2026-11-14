"""SSRF-safe HTTP fetcher for source content.

Every hop (including redirects) is resolved and every resolved address must be public, unless the host is
explicitly allow-listed. Bodies are size-capped, requests to the same host are spaced out, robots.txt is
honoured on request. Known limitation: the address is checked before httpx connects, so a hostile DNS
server could still rebind between check and connect (DNS rebinding); allow-list sensitive deployments.
"""

import ipaddress
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from mediafactory import __version__

USER_AGENT = f"CiciByteMediaFactory/{__version__} (+https://cicibyte.com)"
REDIRECT_CODES = {301, 302, 303, 307, 308}
ROBOTS_TTL_S = 24 * 3600
ROBOTS_ERROR_TTL_S = 5 * 60
ROBOTS_CACHE_MAX = 1000


class FetchError(Exception):
    def __init__(self, message: str, *, status: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class BlockedAddress(FetchError):
    def __init__(self, message: str):
        super().__init__(message, retryable=False)


@dataclass
class FetchedResponse:
    url: str
    status: int
    headers: dict[str, str]
    content: bytes
    request_headers: dict[str, str] = field(default_factory=dict)

    @property
    def text(self) -> str:
        charset = "utf-8"
        ctype = self.headers.get("content-type", "")
        if "charset=" in ctype:
            charset = ctype.split("charset=", 1)[1].split(";")[0].strip() or "utf-8"
        try:
            return self.content.decode(charset, errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")


def is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


class SafeFetcher:
    def __init__(
        self,
        *,
        allowlist: list[str] | tuple[str, ...] = (),
        min_interval_s: float = 2.0,
        max_bytes: int = 5_000_000,
        timeout_s: float = 20,
        max_redirects: int = 5,
        resolver: Callable = socket.getaddrinfo,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        transport: httpx.BaseTransport | None = None,
        user_agent: str = USER_AGENT,
        throttle=None,
    ):
        self.allowlist = {h.lower() for h in allowlist}
        self.min_interval_s = min_interval_s
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self.user_agent = user_agent
        self._resolver, self._sleep, self._clock = resolver, sleep, clock
        if throttle is None:
            from mediafactory.core.throttle import MemoryHostThrottle

            throttle = MemoryHostThrottle(default_interval_s=min_interval_s, sleep=sleep, clock=clock)
        self.throttle = throttle
        self._robots: dict[str, tuple[RobotFileParser | None, float]] = {}
        self._lock = threading.Lock()
        self._client = httpx.Client(timeout=httpx.Timeout(timeout_s), follow_redirects=False, transport=transport)

    def close(self) -> None:
        self._client.close()

    # -- checks ---------------------------------------------------------------------------------------
    def _check_url(self, url: str) -> tuple[str, str]:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https"):
            raise FetchError(f"unsupported URL scheme: {parts.scheme or '(none)'}")
        host = (parts.hostname or "").lower()
        if not host:
            raise FetchError("URL has no host")
        if host in self.allowlist:
            return host, parts.scheme
        port = parts.port or (443 if parts.scheme == "https" else 80)
        try:
            ipaddress.ip_address(host)
            addresses = [host]
        except ValueError:
            try:
                addresses = [info[4][0] for info in self._resolver(host, port, type=socket.SOCK_STREAM)]
            except (socket.gaierror, OSError) as exc:
                raise FetchError(f"cannot resolve {host}: {exc}", retryable=True) from None
        bad = [a for a in addresses if not is_public_ip(a)]
        if not addresses or bad:
            raise BlockedAddress(f"refusing to fetch {host}: resolves to non-public address {', '.join(bad) or '-'}")
        return host, parts.scheme

    def _throttle(self, host: str) -> None:
        self.throttle.acquire(host)  # waits for spacing; raises FetchError(429) while the host cools down

    # -- fetching -------------------------------------------------------------------------------------
    def _fetch(
        self, url: str, headers: dict | None, *, raise_for_status: bool, method: str = "GET", data: dict | None = None
    ) -> FetchedResponse:
        request_headers = {"User-Agent": self.user_agent, **(headers or {})}
        current = url
        for _ in range(self.max_redirects + 1):
            host, _scheme = self._check_url(current)
            self._throttle(host)
            try:
                with self._client.stream(method, current, headers=request_headers, data=data) as response:
                    if response.status_code in REDIRECT_CODES and response.headers.get("location"):
                        if method != "GET":
                            raise FetchError(f"unexpected redirect on {method} to {host}")
                        current = urljoin(current, response.headers["location"])
                        continue
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > self.max_bytes:
                            raise FetchError(f"response too large (> {self.max_bytes} bytes)")
                        chunks.append(chunk)
                    result = FetchedResponse(
                        url=current,
                        status=response.status_code,
                        headers={k.lower(): v for k, v in response.headers.items()},
                        content=b"".join(chunks),
                        request_headers={k.lower(): v for k, v in response.request.headers.items()},
                    )
            except httpx.TimeoutException as exc:
                raise FetchError(f"timeout fetching {host}: {exc}", retryable=True) from None
            except httpx.HTTPError as exc:
                raise FetchError(f"{type(exc).__name__} fetching {host}: {exc}", retryable=True) from None
            if result.status == 429:
                from mediafactory.core.throttle import parse_retry_after

                self.throttle.penalize(host, parse_retry_after(result.headers.get("retry-after")))
            if raise_for_status and result.status >= 400:
                raise FetchError(
                    f"HTTP {result.status} from {host}",
                    status=result.status,
                    retryable=result.status == 429 or result.status >= 500,
                )
            return result
        raise FetchError(f"too many redirects (> {self.max_redirects})")

    def get(self, url: str, *, headers: dict | None = None) -> FetchedResponse:
        return self._fetch(url, headers, raise_for_status=True)

    def post(self, url: str, *, data: dict, headers: dict | None = None) -> FetchedResponse:
        """Form POST with the same address, size and rate checks; redirects are not followed."""
        return self._fetch(url, headers, raise_for_status=True, method="POST", data=data)

    def robots_allowed(self, url: str) -> bool:
        self._check_url(url)  # a blocked address is reported as such, not as a robots.txt refusal
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        cached = self._robots.get(origin)
        if cached is None or cached[1] <= self._clock():
            parser: RobotFileParser | None = RobotFileParser()
            ttl = ROBOTS_TTL_S
            try:
                r = self._fetch(origin + "/robots.txt", None, raise_for_status=False)
                if r.status >= 500:
                    parser, ttl = None, ROBOTS_ERROR_TTL_S  # server trouble: be conservative, retry soon
                elif r.status >= 400:
                    parser.parse([])  # no robots.txt: everything allowed
                else:
                    parser.parse(r.text.splitlines())
            except FetchError:
                parser, ttl = None, ROBOTS_ERROR_TTL_S
            if len(self._robots) > ROBOTS_CACHE_MAX:
                self._robots.clear()
            cached = (parser, self._clock() + ttl)
            self._robots[origin] = cached
        parser = cached[0]
        return bool(parser and parser.can_fetch(self.user_agent, url))
