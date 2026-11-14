import pytest

from mediafactory.pipeline.align import align_words, norm
from mediafactory.pipeline.captions import cues_for


def test_norm_handles_punctuation_and_turkish_case():
    assert norm("İstanbul'da,") == "istanbulda"
    assert norm("KAPI!") == norm("kapı") == "kapi"
    assert norm("“Door”") == "door"


def test_exact_match_takes_whisper_times():
    narration = ["The", "door", "opened."]
    heard = [("the", 0.10, 0.30), ("door", 0.35, 0.70), ("opened", 0.80, 1.40)]
    assert align_words(narration, heard, duration=2.0) == [(0.10, 0.30), (0.35, 0.70), (0.80, 1.40)]


def test_misheard_word_is_interpolated_between_neighbours():
    narration = ["I", "heard", "Zeynep", "scream."]
    heard = [("i", 0.0, 0.2), ("heard", 0.25, 0.6), ("zainab", 0.7, 1.1), ("scream", 1.2, 1.8)]
    times = align_words(narration, heard, duration=2.0)
    assert times[0] == (0.0, 0.2) and times[3] == (1.2, 1.8)
    assert 0.6 <= times[2][0] < times[2][1] <= 1.2  # placed in the gap


def test_times_are_monotonic_and_inside_audio():
    narration = "one two three four five six".split()
    heard = [("one", 0.0, 0.3), ("two", 0.4, 0.7), ("four", 1.5, 1.8), ("six", 2.4, 2.9)]
    times = align_words(narration, heard, duration=3.0)
    starts = [s for s, _ in times]
    assert starts == sorted(starts) and times[-1][1] <= 3.0 and all(e > s for s, e in times)


def test_too_few_matches_means_no_alignment():
    assert align_words("a b c d e f g h".split(), [("x", 0, 1)], duration=4.0) is None


def test_cues_use_real_times_when_given():
    times = [(0.5, 0.9), (1.0, 1.2), (2.0, 2.5), (3.0, 3.4)]
    cues = cues_for("w1 w2 w3 w4", 4.0, words_per_cue=2, times=times)
    assert [(c.start, c.end, c.text) for c in cues] == [(0.5, 1.2, "w1 w2"), (2.0, 3.4, "w3 w4")]
    assert cues[0].words[1] == (1.0, 1.2, "w2")


def test_cues_reject_mismatched_times():
    with pytest.raises(ValueError):
        cues_for("a b c", 3.0, times=[(0, 1)])
