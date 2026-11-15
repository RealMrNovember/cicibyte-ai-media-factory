import json
from types import SimpleNamespace

from mediafactory.ai.router import TaskFailed, TaskNotConfigured
from mediafactory.pipeline import classify


def fake_ai(reply, seen=None, missing=()):
    def run(session, task, messages, **kw):
        if seen is not None:
            seen.append(task)
        if task in missing:
            raise TaskNotConfigured(task)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(text=reply if isinstance(reply, str) else json.dumps(reply), model="m", provider_id=1)

    return run


def test_ordinary_horror_passes(monkeypatch):
    monkeypatch.setattr(classify, "run_task", fake_ai({"flags": [], "severity": "none", "reason": "spooky but fine"}))
    info = classify.classify_script(None, "The attic door opened by itself.", language="en")
    check = classify.content_check(info)
    assert check["ok"] and check["name"] == "content" and info["flags"] == []


def test_always_blocked_flags_fail_even_when_mild(monkeypatch):
    monkeypatch.setattr(classify, "run_task", fake_ai({"flags": ["self_harm"], "severity": "low", "reason": "mentions suicide"}))
    check = classify.content_check(classify.classify_script(None, "text", language="en"))
    assert not check["ok"] and "self_harm" in check["value"]


def test_gore_fails_only_when_severe(monkeypatch):
    monkeypatch.setattr(classify, "run_task", fake_ai({"flags": ["graphic_gore"], "severity": "low"}))
    assert classify.content_check(classify.classify_script(None, "t", language="en"))["ok"]
    monkeypatch.setattr(classify, "run_task", fake_ai({"flags": ["graphic_gore"], "severity": "high"}))
    assert not classify.content_check(classify.classify_script(None, "t", language="en"))["ok"]


def test_unknown_flags_are_dropped(monkeypatch):
    monkeypatch.setattr(classify, "run_task", fake_ai({"flags": ["scary", "hate"], "severity": "HIGH"}))
    info = classify.classify_script(None, "t", language="en")
    assert info["flags"] == ["hate"] and info["severity"] == "high"


def test_falls_back_to_the_script_route_when_classify_is_not_set_up(monkeypatch):
    seen = []
    monkeypatch.setattr(classify, "run_task", fake_ai({"flags": [], "severity": "none"}, seen, missing=("classify",)))
    classify.classify_script(None, "t", language="tr")
    assert seen == ["classify", "script"]


def test_a_failed_check_never_stops_the_video_but_needs_review(monkeypatch):
    monkeypatch.setattr(classify, "run_task", fake_ai(TaskFailed("classify", ["down"])))
    info = classify.classify_script(None, "t", language="en")
    check = classify.content_check(info)
    assert "error" in info and not check["ok"] and "not checked" in check["value"]


def test_unreadable_reply_counts_as_not_checked(monkeypatch):
    monkeypatch.setattr(classify, "run_task", fake_ai("sure! looks fine"))
    assert "error" in classify.classify_script(None, "t", language="en")


def test_rights_check():
    assert classify.rights_check("unknown")["ok"]
    assert classify.rights_check("user_owned")["ok"]
    bad = classify.rights_check("restricted")
    assert not bad["ok"] and bad["name"] == "rights"


def test_checks_join_the_qc_result():
    qc = {"passed": True, "checks": [{"name": "audio", "ok": True, "value": "ok"}]}
    out = classify.with_checks(qc, {"flags": ["hate"], "severity": "high"}, "unknown")
    assert out["passed"] is False and [c["name"] for c in out["checks"]] == ["audio", "content", "rights"]
    assert classify.with_checks(qc, {"flags": [], "severity": "none"}, "licensed")["passed"] is True
