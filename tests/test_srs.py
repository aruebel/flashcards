from datetime import date

import pytest

from flashcards import srs
from flashcards.models import ReviewState


def make_state(**overrides):
    base = dict(card_id=1, box=0, mastery_streak=0, mastered=False, due_date=date(2026, 1, 1), total_reviews=0)
    base.update(overrides)
    return ReviewState(**base)


def test_nein_resets_box_and_streak_and_is_due_immediately():
    state = make_state(box=3, mastery_streak=2)
    result = srs.next_state(state, srs.NEIN, today=date(2026, 1, 10))
    assert result.box == 0
    assert result.mastery_streak == 0
    assert result.mastered is False
    assert result.due_date == date(2026, 1, 10)


def test_unsicher_gives_short_interval():
    state = make_state(mastery_streak=1)
    result = srs.next_state(state, srs.UNSICHER, today=date(2026, 1, 10))
    assert result.mastery_streak == 0
    assert result.due_date == date(2026, 1, 11)


def test_sicher_gives_longer_interval_than_unsicher():
    state = make_state()
    result = srs.next_state(state, srs.SICHER, today=date(2026, 1, 10))
    assert result.due_date == date(2026, 1, 13)


def test_komplett_sicher_increments_streak_and_grows_interval():
    state = make_state(mastery_streak=0)
    result = srs.next_state(state, srs.KOMPLETT_SICHER, today=date(2026, 1, 10))
    assert result.mastery_streak == 1
    assert result.mastered is False
    assert result.due_date == date(2026, 1, 17)


def test_komplett_sicher_three_times_in_a_row_marks_mastered():
    state = make_state()
    today = date(2026, 1, 10)
    state = srs.next_state(state, srs.KOMPLETT_SICHER, today=today)
    state = srs.next_state(state, srs.KOMPLETT_SICHER, today=today)
    state = srs.next_state(state, srs.KOMPLETT_SICHER, today=today)
    assert state.mastered is True
    assert state.mastery_streak == 3


def test_a_bad_rating_in_the_middle_resets_mastery_streak():
    state = make_state()
    today = date(2026, 1, 10)
    state = srs.next_state(state, srs.KOMPLETT_SICHER, today=today)
    state = srs.next_state(state, srs.SICHER, today=today)
    state = srs.next_state(state, srs.KOMPLETT_SICHER, today=today)
    assert state.mastery_streak == 1
    assert state.mastered is False


def test_invalid_rating_raises():
    state = make_state()
    with pytest.raises(ValueError):
        srs.next_state(state, 5)


def test_initial_state_is_due_today_and_not_mastered():
    today = date(2026, 1, 10)
    state = srs.initial_state(card_id=42, today=today)
    assert state.card_id == 42
    assert state.due_date == today
    assert state.mastered is False
