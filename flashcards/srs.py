"""Spaced-repetition Logik (Leitner-artig) fuer die Bewertungen 1-4.

Bewertungsskala nach dem Aufdecken der Antwort:
  1 = Nein               -> sofort/kurzfristig wiederholen
  2 = Ja, unsicher        -> bald wieder abfragen
  3 = Ja, sicher          -> spaeter wieder abfragen
  4 = Ja, komplett sicher -> Intervall verlaengert sich; nach 3x in Folge
                             gilt die Karte als gelernt und wird nicht mehr
                             abgefragt (bis sie manuell zurueckgesetzt wird).

Jede Bewertung < 4 setzt die "komplett sicher"-Serie zurueck.
"""
from datetime import date, timedelta

from .models import ReviewState

NEIN = 1
UNSICHER = 2
SICHER = 3
KOMPLETT_SICHER = 4

RATING_LABELS = {
    NEIN: "Nein",
    UNSICHER: "Ja, unsicher",
    SICHER: "Ja, sicher",
    KOMPLETT_SICHER: "Ja, komplett sicher",
}

_BOX_FOR_RATING = {NEIN: 0, UNSICHER: 1, SICHER: 2}
_INTERVAL_DAYS_FOR_RATING = {NEIN: 0, UNSICHER: 1, SICHER: 3}
_MASTERY_BOX = 3
_MASTERY_STREAK_THRESHOLD = 3
_MASTERY_BASE_INTERVAL_DAYS = 7


def next_state(state: ReviewState, rating: int, today: date = None) -> ReviewState:
    if rating not in RATING_LABELS:
        raise ValueError(f"Ungueltige Bewertung: {rating}")
    today = today or date.today()

    if rating == KOMPLETT_SICHER:
        streak = state.mastery_streak + 1
        box = _MASTERY_BOX
        mastered = streak >= _MASTERY_STREAK_THRESHOLD
        interval_days = _MASTERY_BASE_INTERVAL_DAYS * streak
    else:
        streak = 0
        box = _BOX_FOR_RATING[rating]
        mastered = False
        interval_days = _INTERVAL_DAYS_FOR_RATING[rating]

    return ReviewState(
        card_id=state.card_id,
        box=box,
        mastery_streak=streak,
        mastered=mastered,
        due_date=today if mastered else today + timedelta(days=interval_days),
        total_reviews=state.total_reviews + 1,
    )


def initial_state(card_id: int, today: date = None) -> ReviewState:
    today = today or date.today()
    return ReviewState(card_id=card_id, box=0, mastery_streak=0, mastered=False, due_date=today, total_reviews=0)
