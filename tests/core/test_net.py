import socket

import httpx
import pytest

from mediafactory.core.net import BlockedAddress, FetchError, SafeFetcher, is_public_ip

PUBLIC = "93.184.216.34"


def resolver_for(mapping):
    def resolve(host, port, *args, **kwargs):
        ip = mapping.get(host, PUBLIC)
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (ip, port or 0))]

    return resolve


def fetcher(handler, mapping=None, **kw):
    return SafeFetcher(
        transport=httpx.MockTransport(handler),
        resolver=resolver_for(mapping or {}),
        sleep=kw.pop("sleep", lambda s: None),
        **kw,
    )


def ok_handler(request):
    return httpx.Response(200, text="hello")


def test_public_ip_rules():
    assert is_public_ip(PUBLIC)
    for ip in ("127.0.0.1", "10.1.2.3", "172.16.0.1", "192.168.1.1", "169.254.169.254", "100.64.0.1", "0.0.0.0",
               "::1", "fd00::1", "fe80::1", "::ffff:127.0.0.1", "224.0.0.1"):  # fmt: skip
        assert not is_public_ip(ip), ip


def test_fetches_public_url():
    r = fetcher(ok_handler).get("https://example.com/a")
    assert r.status == 200 and r.text == "hello"
    assert "CiciByteMediaFactory" in r.request_headers["user-agent"]


def test_blocks_loopback_literal():
    with pytest.raises(BlockedAddress):
        fetcher(ok_handler).get("http://127.0.0.1:8080/")


def test_blocks_hostname_resolving_to_private():
    with pytest.raises(BlockedAddress):
        fetcher(ok_handler, {"intranet.example": "10.0.0.5"}).get("http://intranet.example/")


def test_blocks_redirect_to_metadata_ip():
    def handler(request):
        if request.url.host == "example.com":
            return httpx.Response(302, headers={"Location": "http://169.254.169.254/latest/meta-data"})
        return httpx.Response(200, text="secret")

    with pytest.raises(BlockedAddress):
        fetcher(handler).get("https://example.com/r")


def test_blocks_ipv6_ula_and_mapped():
    f = fetcher(ok_handler, {"v6.example": "fd00::1"})
    with pytest.raises(BlockedAddress):
        f.get("http://v6.example/")
    with pytest.raises(BlockedAddress):
        f.get("http://[::ffff:127.0.0.1]/")


def test_allowlist_permits_private_host():
    r = fetcher(ok_handler, {"llm.lan": "10.20.0.2"}, allowlist=["llm.lan"]).get("http://llm.lan/x")
    assert r.status == 200


def test_too_many_redirects():
    def handler(request):
        return httpx.Response(302, headers={"Location": f"https://example.com/{len(str(request.url))}"})

    with pytest.raises(FetchError):
        fetcher(handler).get("https://example.com/start")


def test_rejects_oversized_body():
    big = b"x" * 6_000_000
    with pytest.raises(FetchError, match="too large"):
        fetcher(lambda r: httpx.Response(200, content=big)).get("https://example.com/big")


def test_rate_limits_same_host():
    now = {"t": 100.0}
    slept = []

    def sleep(s):
        slept.append(s)
        now["t"] += s

    f = fetcher(ok_handler, sleep=sleep, clock=lambda: now["t"])
    f.get("https://example.com/1")
    f.get("https://example.com/2")
    f.get("https://other.example/1")
    assert len(slept) == 1 and slept[0] == pytest.approx(2.0)


def test_429_and_5xx_retryable():
    for code, retry in ((429, True), (503, True), (404, False)):
        with pytest.raises(FetchError) as e:
            fetcher(lambda r, c=code: httpx.Response(c, text="x")).get("https://example.com/")
        assert e.value.retryable is retry and e.value.status == code


def test_robots_disallow_respected():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
        return httpx.Response(200, text="page")

    f = fetcher(handler)
    assert f.robots_allowed("https://example.com/public") is True
    assert f.robots_allowed("https://example.com/private/x") is False


def test_robots_missing_allows():
    f = fetcher(lambda r: httpx.Response(404) if r.url.path == "/robots.txt" else httpx.Response(200))
    assert f.robots_allowed("https://example.com/a") is True


def test_robots_server_error_disallows():
    f = fetcher(lambda r: httpx.Response(503) if r.url.path == "/robots.txt" else httpx.Response(200))
    assert f.robots_allowed("https://example.com/a") is False


def test_non_http_scheme_rejected():
    for url in ("file:///etc/passwd", "ftp://example.com/x", "gopher://example.com"):
        with pytest.raises(FetchError):
            fetcher(ok_handler).get(url)
