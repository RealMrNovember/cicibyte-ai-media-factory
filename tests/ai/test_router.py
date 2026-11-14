import httpx
import pytest
import respx

from mediafactory.ai.router import TaskFailed, TaskNotConfigured, run_task
from mediafactory.db.models import AIProvider, AITaskRoute

MSG = [{"role": "user", "content": "hi"}]
URL1 = "http://p1.test/v1/chat/completions"
URL2 = "http://p2.test/v1/chat/completions"


def ok(text):
    return httpx.Response(200, json={"model": "m", "choices": [{"message": {"content": text}}]})


@pytest.fixture
def route(db):
    p1 = AIProvider(name="p1", base_url="http://p1.test/v1", locality="remote", timeout_s=5)
    p2 = AIProvider(name="p2", base_url="http://p2.test/v1", locality="remote", timeout_s=5)
    db.add_all([p1, p2])
    db.flush()
    r = AITaskRoute(
        task="script",
        steps=[{"provider_id": p1.id, "model": "m1"}, {"provider_id": p2.id, "model": "m2"}],
        rounds=3,
        retry_delay_s=3.0,
    )
    db.add(r)
    db.flush()
    return {"p1": p1, "p2": p2, "route": r}


@respx.mock
def test_first_step_success_no_fallback(db, route):
    first = respx.post(URL1).mock(return_value=ok("one"))
    second = respx.post(URL2).mock(return_value=ok("two"))
    result = run_task(db, "script", MSG, sleep=lambda s: None)
    assert result.text == "one" and first.call_count == 1 and second.call_count == 0


@respx.mock
def test_falls_back_to_second_step(db, route):
    respx.post(URL1).mock(return_value=httpx.Response(503, text="busy"))
    respx.post(URL2).mock(return_value=ok("two"))
    result = run_task(db, "script", MSG, sleep=lambda s: None)
    assert result.text == "two" and result.provider_id == route["p2"].id


@respx.mock
def test_sleeps_3s_between_rounds_and_stops_after_3_rounds(db, route):
    first = respx.post(URL1).mock(return_value=httpx.Response(503, text="busy"))
    second = respx.post(URL2).mock(return_value=httpx.Response(500, text="err"))
    sleeps = []
    with pytest.raises(TaskFailed) as e:
        run_task(db, "script", MSG, sleep=sleeps.append)
    assert sleeps == [3.0, 3.0]
    assert first.call_count == 3 and second.call_count == 3
    assert len(e.value.errors) == 6


@respx.mock
def test_succeeds_in_second_round(db, route):
    responses = iter([httpx.Response(503, text="busy"), ok("late")])
    respx.post(URL1).mock(side_effect=lambda request: next(responses))
    respx.post(URL2).mock(return_value=httpx.Response(503, text="busy"))
    sleeps = []
    result = run_task(db, "script", MSG, sleep=sleeps.append)
    assert result.text == "late" and sleeps == [3.0]


@respx.mock
def test_disabled_provider_skipped(db, route):
    route["p1"].enabled = False
    first = respx.post(URL1).mock(return_value=ok("one"))
    respx.post(URL2).mock(return_value=ok("two"))
    assert run_task(db, "script", MSG, sleep=lambda s: None).text == "two"
    assert first.call_count == 0


@respx.mock
def test_deleted_provider_step_skipped(db, route):
    route["route"].steps = [{"provider_id": 999999, "model": "x"}, *route["route"].steps]
    respx.post(URL1).mock(return_value=ok("one"))
    assert run_task(db, "script", MSG, sleep=lambda s: None).text == "one"


def test_unconfigured_task_raises(db):
    with pytest.raises(TaskNotConfigured):
        run_task(db, "classify", MSG, sleep=lambda s: None)
