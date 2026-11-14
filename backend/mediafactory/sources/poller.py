"""Background collection: run sources whose next_run_at has come, with exponential backoff on failure."""

import logging
import threading
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from mediafactory.core.net import SafeFetcher
from mediafactory.core.redact import redact
from mediafactory.db.base import utcnow
from mediafactory.db.models import SourceConnector
from mediafactory.sources.adapters import AdapterError, FetchContext, get_adapter
from mediafactory.sources.credentials import credentials_for
from mediafactory.sources.ingest import IngestResult, store_items

log = logging.getLogger(__name__)

MAX_BACKOFF = timedelta(hours=24)
MAX_BACKOFF_EXPONENT = 20
ERROR_SLEEP_S = 30
OUTAGE_SLEEP_S = 5


def schedule_next(connector: SourceConnector, *, failed: bool) -> None:
    interval = timedelta(minutes=connector.poll_interval_min or 60)
    if failed:
        exponent = min(max(1, connector.consecutive_failures or 0), MAX_BACKOFF_EXPONENT)  # no overflow
        backoff = min(interval.total_seconds() * 2**exponent, MAX_BACKOFF.total_seconds())
        interval = max(interval, timedelta(seconds=backoff))  # never sooner than a healthy run
    connector.next_run_at = utcnow() + interval


def _record_failure(connector: SourceConnector, message: str) -> None:
    connector.last_run_at = utcnow()
    connector.last_error = redact(message)[:2000]
    connector.consecutive_failures = (connector.consecutive_failures or 0) + 1
    schedule_next(connector, failed=True)


def run_source(session: Session, connector: SourceConnector, *, fetcher: SafeFetcher) -> IngestResult:
    """Fetch and store one source now. Errors are recorded on the connector and returned, never raised."""
    try:
        name = connector.adapter
        creds = credentials_for(session, name)
        if name == "reddit_rss":  # Reddit often blocks keyless RSS; use the official API when an app is set up
            api_creds = credentials_for(session, "reddit")
            if api_creds:
                name, creds = "reddit", api_creds
        adapter = get_adapter(name)
        params = adapter.validate(connector.params or {})
        ctx = FetchContext(fetcher=fetcher, credentials=creds)
        items = adapter.fetch(params, ctx)
    except OperationalError:
        raise
    except (AdapterError, ValueError) as exc:
        _record_failure(connector, str(exc))
        return IngestResult(item_ids=[], error=connector.last_error)
    except Exception as exc:  # unexpected adapter bug: record it, never 500 or crash the poller
        log.exception("source %s adapter crashed", connector.id)
        _record_failure(connector, f"{type(exc).__name__}: {exc}")
        return IngestResult(item_ids=[], error=connector.last_error)
    result = store_items(session, connector, items, source_type=connector.adapter)
    connector.last_run_at = connector.last_success_at = utcnow()
    connector.last_error = None
    connector.consecutive_failures = 0
    connector.items_total = (connector.items_total or 0) + result.new
    schedule_next(connector, failed=False)
    return result


def _claim_due(factory: Callable[[], Session], limit: int) -> list[int]:
    with factory() as s:
        due = s.scalars(
            select(SourceConnector)
            .where(
                SourceConnector.enabled.is_(True),
                SourceConnector.deleted_at.is_(None),
                or_(SourceConnector.next_run_at.is_(None), SourceConnector.next_run_at <= utcnow()),
            )
            .order_by(SourceConnector.next_run_at.nulls_first(), SourceConnector.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
        for c in due:  # lease: another poller will not pick these up while we run them
            schedule_next(c, failed=False)
        s.commit()
        return [c.id for c in due]


def poll_due(factory: Callable[[], Session], *, fetcher: SafeFetcher, limit: int = 5) -> int:
    ids = _claim_due(factory, limit)
    for cid in ids:
        try:
            with factory() as s:
                # hold the row while running; skip it if "run now" is running it right now
                connector = s.scalar(
                    select(SourceConnector).where(SourceConnector.id == cid).with_for_update(skip_locked=True)
                )
                if connector is None:
                    continue
                result = run_source(s, connector, fetcher=fetcher)
                s.commit()
            log.info("source %s: %s", cid, result.as_dict())
        except OperationalError:
            raise
        except Exception as exc:  # unexpected bug in one source must not stop the others
            log.exception("source %s crashed", cid)
            with factory() as s:
                connector = s.get(SourceConnector, cid)
                if connector is not None:
                    _record_failure(connector, f"{type(exc).__name__}: {exc}")
                    s.commit()
    return len(ids)


class SourcePoller(threading.Thread):
    def __init__(
        self, factory: Callable[[], Session], *, fetcher: SafeFetcher, stop_event: threading.Event,
        interval_s: float = 30,
    ):  # fmt: skip
        super().__init__(name="source-poller", daemon=True)
        self.factory, self.fetcher, self.stop_event, self.interval_s = factory, fetcher, stop_event, interval_s
        self.error_sleep_s = ERROR_SLEEP_S

    def run(self) -> None:
        log.info("source poller started (every %ss)", self.interval_s)
        while not self.stop_event.is_set():
            try:
                poll_due(self.factory, fetcher=self.fetcher)
            except OperationalError as exc:
                log.warning("database unavailable for source polling (%s)", type(exc).__name__)
                self.stop_event.wait(OUTAGE_SLEEP_S)
                continue
            except Exception:  # a bug must never kill collection for every source
                log.exception("source poller iteration failed; retrying in %ss", self.error_sleep_s)
                self.stop_event.wait(self.error_sleep_s)
                continue
            self.stop_event.wait(self.interval_s)
