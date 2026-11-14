from mediafactory.desktop_monitor import notifications_for, title_for


def job(i, status, title="Story", youtube=None):
    return {"id": i, "status": status, "title": title, "youtube": youtube}


def test_first_look_never_notifies():
    seen, notes = notifications_for(None, [job(1, "needs_review"), job(2, "failed")], lang="en")
    assert notes == [] and seen == {1: "needs_review", 2: "failed"}


def test_transitions_make_notifications():
    prev = {1: "discovered", 2: "uploading", 3: "discovered", 4: "needs_review"}
    jobs = [job(1, "needs_review", "Eleven Gallons"), job(2, "published", youtube={"url": "https://youtube.com/shorts/x"}),
            job(3, "failed"), job(4, "needs_review"), job(5, "discovered")]  # fmt: skip
    seen, notes = notifications_for(prev, jobs, lang="en")
    kinds = [(n["kind"], n["job_id"]) for n in notes]
    assert kinds == [("ready", 1), ("published", 2), ("failed", 3)]  # 4 unchanged, 5 is new but not finished
    assert "Eleven Gallons" in notes[0]["body"] and notes[1]["url"] == "https://youtube.com/shorts/x"
    assert seen[5] == "discovered"


def test_turkish_texts_and_title():
    _, notes = notifications_for({7: "rendering"}, [job(7, "approved", "Üçler Vakti")], lang="tr")
    assert notes[0]["title"].startswith("Video hazır")
    assert title_for({"summary": {"en": "Idle", "tr": "Boşta"}}, lang="tr") == "CiciByte AI Media Factory — Boşta"
    assert title_for(None, lang="tr") == "CiciByte AI Media Factory"
