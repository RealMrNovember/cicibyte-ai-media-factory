import json
from types import SimpleNamespace

import pytest

from mediafactory.ai.router import TaskFailed
from mediafactory.pipeline import doctor, script

ITEM = SimpleNamespace(title="The attic", normalized_text="Something walks in the attic every night.")


def words(n: int) -> str:
    return " ".join(["dark"] * n)


def draft(narration: str, title: str = "Draft") -> str:
    return json.dumps({"title": title, "hook": "It came back.", "narration": narration, "description": "d", "tags": ["#a"]})


class FakeAI:
    """Answers the writer and the doctor from queues and records every call."""

    def __init__(self, drafts: list[str], reviews: list):
        self.drafts, self.reviews, self.calls = list(drafts), list(reviews), []

    def __call__(self, session, task, messages, **kw):
        kind = "review" if messages[0]["content"].startswith(doctor.REVIEW_SYSTEM[:40]) else "write"
        self.calls.append((kind, messages))
        reply = self.drafts.pop(0) if kind == "write" else self.reviews.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(text=reply if isinstance(reply, str) else json.dumps(reply), model="m", provider_id=1)


def review(score: int, *problems: str) -> dict:
    return {"score": score, "problems": list(problems)}


@pytest.fixture
def ai(monkeypatch):
    def install(drafts, reviews):
        fake = FakeAI(drafts, reviews)
        monkeypatch.setattr(script, "run_task", fake)
        monkeypatch.setattr(doctor, "run_task", fake)
        return fake

    return install


def test_a_good_script_is_kept_after_one_review(ai):
    fake = ai([draft(words(125))], [review(8)])
    data = script.generate_script(None, ITEM, language="en", seconds=50, doctor=True)
    assert [k for k, _ in fake.calls] == ["write", "review"]
    assert data["doctor"] == {"score": 8, "problems": [], "revised": False}


def test_a_weak_script_is_rewritten_with_the_reviewers_notes(ai):
    fake = ai([draft(words(125)), draft(words(120), title="Better")], [review(4, "the hook is flat"), review(8)])
    data = script.generate_script(None, ITEM, language="en", seconds=50, doctor=True)
    assert [k for k, _ in fake.calls] == ["write", "review", "write", "review"]
    rewrite_prompt = fake.calls[2][1][-1]["content"]
    assert "the hook is flat" in rewrite_prompt and words(10) in rewrite_prompt
    assert data["title"] == "Better"
    assert data["doctor"] == {"score": 8, "problems": [], "revised": True, "first_score": 4}


def test_a_rewrite_that_scores_lower_is_thrown_away(ai):
    ai([draft(words(125)), draft(words(125), title="Worse")], [review(5, "slow middle"), review(3)])
    data = script.generate_script(None, ITEM, language="en", seconds=50, doctor=True)
    assert data["title"] == "Draft"
    assert data["doctor"]["score"] == 5 and data["doctor"]["revised"] is False


def test_a_script_far_from_the_target_length_is_rewritten_even_if_the_model_likes_it(ai):
    fake = ai([draft(words(40)), draft(words(125))], [review(9), review(8)])
    data = script.generate_script(None, ITEM, language="en", seconds=50, doctor=True)
    assert len(fake.calls) == 4
    assert "too short" in fake.calls[2][1][-1]["content"]
    assert data["doctor"]["revised"] is True


def test_the_doctor_never_breaks_script_writing(ai):
    ai([draft(words(125))], [TaskFailed("script", ["down"])])
    data = script.generate_script(None, ITEM, language="en", seconds=50, doctor=True)
    assert data["title"] == "Draft" and "error" in data["doctor"]


def test_an_unreadable_review_is_ignored(ai):
    ai([draft(words(125))], ["no json here"])
    data = script.generate_script(None, ITEM, language="en", seconds=50, doctor=True)
    assert data["title"] == "Draft" and "error" in data["doctor"]


def test_a_failed_rewrite_keeps_the_first_draft(ai):
    ai([draft(words(125)), TaskFailed("script", ["down"])], [review(3, "boring")])
    data = script.generate_script(None, ITEM, language="en", seconds=50, doctor=True)
    assert data["title"] == "Draft" and data["doctor"]["score"] == 3 and data["doctor"]["revised"] is False


def test_the_doctor_can_be_turned_off(ai):
    fake = ai([draft(words(125))], [])
    data = script.generate_script(None, ITEM, language="en", seconds=50, doctor=False)
    assert len(fake.calls) == 1 and "doctor" not in data


def test_review_scores_are_clamped():
    assert doctor.parse_review('{"score": 42, "problems": ["x", 5]}') == (10, ["x", "5"])
    assert doctor.parse_review('{"score": "7"}') == (7, [])
