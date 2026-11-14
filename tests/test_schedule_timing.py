from datetime import datetime, timezone

import pytest

from mediafactory.schedule.timing import next_run, parse_times


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


def test_next_slot_same_day_in_istanbul():
    # 05:00 UTC = 08:00 Istanbul -> next is 09:00 Istanbul = 06:00 UTC
    assert next_run(["09:00", "18:00"], [0, 1, 2, 3, 4, 5, 6], "Europe/Istanbul", utc(2026, 11, 16, 5, 0)) == utc(2026, 11, 16, 6, 0)


def test_rolls_to_next_day_after_last_slot():
    assert next_run(["09:00"], [], "UTC", utc(2026, 11, 16, 9, 0)) == utc(2026, 11, 17, 9, 0)


def test_respects_weekdays():
    # 2026-11-16 is a Monday; only Saturdays (5)
    assert next_run(["10:00"], [5], "UTC", utc(2026, 11, 16, 12, 0)) == utc(2026, 11, 21, 10, 0)


def test_bad_input_rejected():
    with pytest.raises(ValueError):
        parse_times(["25:00"])
    with pytest.raises(ValueError):
        next_run(["09:00"], [0], "Mars/Base", utc(2026, 1, 1))
