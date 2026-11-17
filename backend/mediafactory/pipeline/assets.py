"""Fetch the voice and caption models before the first video (Easy Setup), with progress.

Each model is also downloaded on first use anyway, so skipping this (no internet) only delays it.
"""

import threading
from collections.abc import Callable
from pathlib import Path

Step = tuple[str, Callable[[Path], object]]


def default_steps() -> list[Step]:
    from mediafactory.pipeline import align, tts

    return [("voice-en", lambda m: tts.ensure_voice("en", m)), ("voice-tr", lambda m: tts.ensure_voice("tr", m)),
            ("captions", align._model)]  # fmt: skip


class Downloader:
    def __init__(self, data_dir: Path, *, steps: list[Step] | None = None):
        self.models = Path(data_dir) / "models"
        self.steps = steps
        self.lock = threading.Lock()
        self.thread: threading.Thread | None = None
        self._state = {"state": "idle", "done": 0, "total": 0, "current": None, "error": None}

    def status(self) -> dict:
        with self.lock:
            return dict(self._state)

    def _set(self, **kw) -> None:
        with self.lock:
            self._state.update(kw)

    def run(self) -> None:
        steps = self.steps if self.steps is not None else default_steps()
        self.models.mkdir(parents=True, exist_ok=True)
        self._set(state="running", done=0, total=len(steps), current=None, error=None)
        for i, (name, fn) in enumerate(steps):
            self._set(current=name)
            try:
                fn(self.models)
            except Exception as exc:  # noqa: BLE001 - shown to the user; they can retry or skip
                self._set(state="failed", error=f"{name}: {exc}"[:300], current=None)
                return
            self._set(done=i + 1)
        self._set(state="done", current=None)

    def start(self) -> bool:
        """Run in the background; False when a run is already going."""
        with self.lock:
            if self.thread is not None and self.thread.is_alive():
                return False
            self.thread = threading.Thread(target=self.run, name="setup-assets", daemon=True)
            self._state["state"] = "running"
        self.thread.start()
        return True


_shared: Downloader | None = None


def shared(data_dir: Path) -> Downloader:
    global _shared
    if _shared is None:
        _shared = Downloader(data_dir)
    return _shared
