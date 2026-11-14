import pytest

from mediafactory.ai.jsonparse import extract_json


def test_plain_object():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_fenced_with_chatter_and_trailing_comma():
    text = 'Sure! Here it is:\n```json\n{"title": "x", "tags": ["a", "b",],}\n```'
    assert extract_json(text) == {"title": "x", "tags": ["a", "b"]}


def test_top_level_list():
    assert extract_json("```\n[1, 2]\n```") == [1, 2]


def test_no_json_raises():
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_raw_newlines_inside_strings_accepted():
    assert extract_json('{"narration": "line one\nline two"}') == {"narration": "line one\nline two"}
