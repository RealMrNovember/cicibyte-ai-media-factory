"""Desktop app background monitor: live status in the window title and Windows notifications.

Every few seconds it asks the server what is going on (/api/activity) and shows the summary next to the app
name in the title bar (also visible on the taskbar). It also compares job statuses with the previous look and
raises a Windows notification when a video is ready, published or failed.
"""

import json
import locale
import logging
import threading
import urllib.parse
import urllib.request

APP_NAME = "CiciByte AI Media Factory"
TITLE_EVERY_S = 5
JOBS_EVERY_S = 15
log = logging.getLogger(__name__)

TEXTS = {
    "en": {"ready": ("Video ready", "“{t}” is waiting for your review."),
           "published": ("Published on YouTube", "“{t}” is on YouTube."),
           "scheduled": ("Scheduled on YouTube", "“{t}” will be published at the chosen time."),
           "failed": ("Production failed", "“{t}” could not be made — open the app for details."),
           "update": ("Update available", "Version {t} of the app is ready to install.")},
    "tr": {"ready": ("Video hazır", "“{t}” incelemeni bekliyor."),
           "published": ("YouTube'da yayınlandı", "“{t}” YouTube'da."),
           "scheduled": ("YouTube'da zamanlandı", "“{t}” seçtiğin saatte yayınlanacak."),
           "failed": ("Üretim başarısız", "“{t}” üretilemedi — ayrıntılar için uygulamayı aç."),
           "update": ("Güncelleme var", "Uygulamanın {t} sürümü kurulmaya hazır.")},
}  # fmt: skip
KIND_BY_STATUS = {"needs_review": "ready", "approved": "ready", "published": "published", "scheduled": "scheduled",
                  "failed": "failed"}  # fmt: skip


def system_lang() -> str:
    try:
        import ctypes

        lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()  # type: ignore[attr-defined]
        return "tr" if (lcid & 0x3FF) == 0x1F else "en"
    except Exception:
        loc = (locale.getlocale()[0] or "").lower()
        return "tr" if loc.startswith(("tr", "turkish")) else "en"


def notifications_for(prev: dict | None, jobs: list[dict], *, lang: str) -> tuple[dict, list[dict]]:
    """(new snapshot, notifications) for the job list compared with the previous snapshot.
    The very first look only records the snapshot, so starting the app does not flood you with old news."""
    seen = {j["id"]: j["status"] for j in jobs}
    if prev is None:
        return seen, []
    texts = TEXTS.get(lang, TEXTS["en"])
    notes = []
    for j in jobs:
        old, new = prev.get(j["id"]), j["status"]
        kind = KIND_BY_STATUS.get(new)
        if old is None or old == new or kind is None:
            continue
        if kind == "ready" and old in ("needs_review", "approved"):
            continue  # approving a ready video is not news
        title, body = texts[kind]
        notes.append({"kind": kind, "job_id": j["id"], "title": title, "body": body.format(t=(j.get("title") or f"#{j['id']}")[:80]),
                      "url": (j.get("youtube") or {}).get("url")})  # fmt: skip
    return seen, notes


def title_for(activity: dict | None, *, lang: str) -> str:
    if not activity:
        return APP_NAME
    summary = (activity.get("summary") or {}).get(lang) or (activity.get("summary") or {}).get("en")
    return f"{APP_NAME} — {summary}" if summary else APP_NAME


def _get(base: str, path: str):
    u = urllib.parse.urlsplit(base)
    req = urllib.request.Request(f"{base}{path}", headers={"Host": u.netloc})
    with urllib.request.urlopen(req, timeout=8) as r:  # noqa: S310 (the user's own server)
        return json.loads(r.read())


def notify(title: str, body: str, *, url: str | None = None, icon: str | None = None) -> None:
    try:
        from winotify import Notification

        toast = Notification(app_id=APP_NAME, title=title, msg=body, icon=icon or "")
        if url:
            toast.add_actions(label="▶ YouTube", launch=url)
        toast.show()
    except Exception as exc:  # notifications are a convenience; never break the app
        log.debug("notification failed: %s", exc)


class Monitor(threading.Thread):
    def __init__(self, cfg, window, *, icon: str | None = None):
        super().__init__(name="monitor", daemon=True)
        self.cfg, self.window, self.icon = cfg, window, icon
        self.lang = system_lang()
        self.snapshot: dict | None = None
        self.update_told = False
        self.stop_event = threading.Event()

    def run(self) -> None:
        ticks = 0
        while not self.stop_event.wait(TITLE_EVERY_S if ticks else 1):
            ticks += 1
            base = self.cfg.target_url
            try:
                self.window.set_title(title_for(_get(base, "/api/activity"), lang=self.lang))
            except Exception:
                try:
                    self.window.set_title(APP_NAME)
                except Exception:
                    pass
            if not self.cfg.data.get("notifications", True):
                continue
            if self.cfg.update and not self.update_told:
                self.update_told = True
                t = TEXTS[self.lang]["update"]
                notify(t[0], t[1].format(t=self.cfg.update["version"]), icon=self.icon)
            if ticks % max(1, JOBS_EVERY_S // TITLE_EVERY_S) != 1:
                continue
            try:
                jobs = _get(base, "/api/jobs?limit=40").get("items", [])
            except Exception:
                continue
            self.snapshot, notes = notifications_for(self.snapshot, jobs, lang=self.lang)
            for n in notes:
                notify(n["title"], n["body"], url=n.get("url"), icon=self.icon)
