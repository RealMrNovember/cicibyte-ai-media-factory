"""Reject oversized request bodies before any parsing or authentication happens."""

import json

MAX_BODY_BYTES = 12 * 1024 * 1024  # a 10 MB upload plus multipart overhead
# Paths that legitimately take big uploads (background video clips).
LARGE_UPLOADS = {"/api/backgrounds": 2 * 1024 * 1024 * 1024}


class BodyTooLarge(Exception):
    pass


class MaxBodySizeMiddleware:
    def __init__(self, app, max_bytes: int = MAX_BODY_BYTES, large: dict[str, int] | None = None):
        self.app = app
        self.max_bytes = max_bytes
        self.large = LARGE_UPLOADS if large is None else large

    async def _reject(self, send, limit: int) -> None:
        body = json.dumps({"detail": f"request body is larger than {limit // (1024 * 1024)} MB"}).encode()
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})  # fmt: skip
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        limit = next((v for k, v in self.large.items() if path == k or path.startswith(k + "/")), self.max_bytes)
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    if int(value) > limit:
                        return await self._reject(send, limit)
                except ValueError:
                    return await self._reject(send, limit)
        received = 0
        started = False

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:  # chunked upload without Content-Length
                    raise BodyTooLarge()
            return message

        async def tracking_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except BodyTooLarge:
            if not started:
                await self._reject(send, limit)
