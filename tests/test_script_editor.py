from sqlalchemy import select

from mediafactory.db.models import JobStageRun, ProductionJob, SourceItem
from mediafactory.pipeline import handlers
from mediafactory.queue.registry import StageContext

H = {"X-MF-Client": "1"}
SCRIPT = {"title": "The Quiet House", "hook": "It was quiet.", "narration": "It was quiet. Too quiet. " * 10,
          "description": "d", "tags": ["horror"], "model": "m"}  # fmt: skip


def _item(db):
    it = SourceItem(source_type="manual", title="seed", raw_text="x" * 500, normalized_text="x" * 500, content_hash="se1")
    db.add(it)
    db.flush()
    return it


def _runs(db, jid):
    return list(db.scalars(select(JobStageRun).where(JobStageRun.job_id == jid).order_by(JobStageRun.id)))


def test_review_flow_draft_edit_then_render(client, db, monkeypatch):
    item = _item(db)
    r = client.post(f"/api/items/{item.id}/make", json={"languages": ["tr"], "review_script": True, "seconds": 40}, headers=H)
    job = db.get(ProductionJob, r.json()["jobs"][0]["id"])
    [draft] = _runs(db, job.id)
    assert draft.stage == "draft_script" and draft.job_class == "llm"

    import mediafactory.pipeline.script as script_mod

    monkeypatch.setattr(script_mod, "generate_script", lambda *a, **k: dict(SCRIPT))
    outcome = handlers.draft_script_stage(StageContext(db, job, draft, lambda m: None, lambda: False))
    job.status = outcome.next_status
    db.flush()
    assert job.status == "script_draft"
    assert client.get(f"/api/jobs/{job.id}").json()["script"]["title"] == "The Quiet House"

    edited = {"title": "Sessiz Ev", "narration": "Ev sessizdi. Fazla sessiz. " * 8, "description": "açıklama",
              "tags": ["#korku", " gizem "], "render": True}  # fmt: skip
    r = client.post(f"/api/jobs/{job.id}/script", json=edited, headers=H)
    assert r.status_code == 200 and job.status == "script_approved"
    make = _runs(db, job.id)[-1]
    assert make.stage == "make_short" and make.inputs["script"]["title"] == "Sessiz Ev"
    assert make.inputs["language"] == "tr" and make.inputs["seconds"] == 40
    assert make.inputs["script"]["tags"] == ["korku", "gizem"]


def test_make_stage_uses_the_reviewed_script(db, monkeypatch, tmp_path):
    import mediafactory.pipeline.make as make_mod

    seen = {}
    monkeypatch.setattr(make_mod, "make_short", lambda session, item_id, **kw: seen.update(kw) or {"video": "v", "title": "t"})
    job = ProductionJob(status="script_approved", language="en", payload={})
    db.add(job)
    db.flush()
    run = JobStageRun(job_id=job.id, stage="make_short", job_class="render",
                      inputs={"item_id": 1, "language": "en", "script": SCRIPT})  # fmt: skip
    db.add(run)
    db.flush()
    handlers.make_short_stage(StageContext(db, job, run, lambda m: None, lambda: False))
    assert seen["script"]["title"] == "The Quiet House"


def test_script_cannot_change_while_running_or_published(client, db):
    running = ProductionJob(status="rendering", language="en", payload={})
    published = ProductionJob(status="approved", language="en", payload={"youtube": {"id": "abc"}, "script": SCRIPT})
    db.add_all([running, published])
    db.flush()
    body = {"title": "x", "narration": "word " * 10}
    assert client.post(f"/api/jobs/{running.id}/script", json=body, headers=H).status_code == 409
    assert client.post(f"/api/jobs/{published.id}/script", json=body, headers=H).status_code == 409


def test_rerender_from_ready_uses_original_settings(client, db):
    item = _item(db)
    r = client.post(f"/api/items/{item.id}/make", json={"languages": ["en"], "background": "none"}, headers=H)
    job = db.get(ProductionJob, r.json()["jobs"][0]["id"])
    job.status = "needs_review"
    db.flush()
    body = {"title": "New title", "narration": "A better opening line. " * 6, "render": True}
    assert client.post(f"/api/jobs/{job.id}/script", json=body, headers=H).status_code == 200
    last = _runs(db, job.id)[-1]
    assert last.stage == "make_short" and last.inputs["background"] == "none" and last.inputs["script"]["title"] == "New title"
