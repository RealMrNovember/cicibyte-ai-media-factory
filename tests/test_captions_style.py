import pytest
from pydantic import ValidationError

from mediafactory.pipeline.captions import cues_for, to_ass
from mediafactory.pipeline.style import CaptionStyle, ass_colour

NARR = "The house was quiet. Then the door opened, slowly, by itself."


def test_ass_colour_is_bgr():
    assert ass_colour("#FF8800") == "&H000088FF"


def test_default_style_matches_previous_look():
    ass = to_ass(cues_for(NARR, 6.0), "en")
    assert "Montserrat Black" in ass and "\\pos(540,960)" in ass


def test_position_and_font_and_colour_applied():
    style = CaptionStyle(font="bebas", position=80, color="#FF0000", size=120, animation="none")
    ass = to_ass(cues_for(NARR, 6.0, words_per_cue=style.words_per_cue), "en", style=style)
    assert "Style: Cap,Bebas Neue,120,&H000000FF" in ass
    assert "\\pos(540,1536)" in ass


def test_words_per_cue():
    assert [c.text for c in cues_for("a b c d e", 5.0, words_per_cue=2)] == ["a b", "c d", "e"]


def test_karaoke_highlights_each_word_in_turn():
    style = CaptionStyle(animation="karaoke", highlight_color="#00FF00", uppercase=False)
    ass = to_ass(cues_for("one two three", 3.0), "en", style=style)
    events = [line for line in ass.splitlines() if line.startswith("Dialogue")]
    assert len(events) == 3  # one event per word, same three-word line
    assert "{\\c&H0000FF00&}one{\\c&H00FFFFFF&} two three" in events[0]
    assert "one {\\c&H0000FF00&}two{\\c&H00FFFFFF&} three" in events[1]


def test_lowercase_kept_when_uppercase_off():
    ass = to_ass(cues_for("quiet house", 2.0), "en", style=CaptionStyle(uppercase=False, animation="none"))
    assert "quiet house" in ass


def test_bad_colour_rejected():
    with pytest.raises(ValidationError):
        CaptionStyle(color="red")
