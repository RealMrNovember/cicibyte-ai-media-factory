from mediafactory.pipeline.originality import check_originality, with_originality

SOURCE = (
    "I moved into the old farmhouse in October. Every night at three I heard footsteps in the attic, slow and heavy, "
    "like someone dragging a chain across the boards. My landlord swore nobody had lived up there for forty years."
)


def test_an_original_retelling_passes():
    script = ("It is three in the morning and something is walking above my bed. The cabin was cheap for a reason. "
              "Tonight I climb the ladder with a flashlight, and the dust up here is full of small bare footprints.")  # fmt: skip
    check = check_originality(script, SOURCE)
    assert check["ok"] and check["name"] == "originality"


def test_a_script_that_copies_a_long_passage_fails():
    script = "Listen. " + SOURCE.split(". ")[1] + ". I never slept there again."
    check = check_originality(script, SOURCE)
    assert not check["ok"]
    assert "words in a row" in check["value"]


def test_copying_many_short_phrases_fails_on_overlap():
    words = SOURCE.split()
    pieces = [" ".join(words[i : i + 6]) for i in range(0, len(words) - 6, 8)]  # 6-word chunks, re-joined
    check = check_originality(" and then ".join(pieces), SOURCE)
    assert not check["ok"] and "%" in check["value"]


def test_case_and_punctuation_do_not_hide_copying():
    copied = SOURCE.upper().replace(",", "").replace(".", "!")
    assert not check_originality(copied, SOURCE)["ok"]


def test_turkish_letters_are_compared_correctly():
    src = "Gece yarısı köy evinin tavanından ağır ayak sesleri geliyordu ve kimse yukarı çıkmaya cesaret edemiyordu."
    assert not check_originality("Dinle. " + src, src)["ok"]
    assert check_originality("Bu şehirde kimse kapısını kilitlemez, ama ben artık kilitliyorum.", src)["ok"]


def test_no_source_text_means_nothing_to_compare():
    check = check_originality("Any narration here.", "")
    assert check["ok"] and check["value"] == "no source text"


def test_the_check_is_added_to_qc_and_a_failure_fails_qc():
    qc = {"passed": True, "checks": [{"name": "audio", "ok": True, "value": "ok"}]}
    bad = with_originality(qc, SOURCE, SOURCE)
    assert bad["passed"] is False and [c["name"] for c in bad["checks"]] == ["audio", "originality"]
    good = with_originality(qc, "Something entirely different happens to me in a lighthouse.", SOURCE)
    assert good["passed"] is True
