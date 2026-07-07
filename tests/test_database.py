from pathlib import Path

import pytest

from flashcards.database import Database
from flashcards.models import Card
from flashcards.srs import NEIN, KOMPLETT_SICHER


@pytest.fixture
def db(tmp_path: Path):
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


def test_add_and_list_topic(db):
    topic = db.add_topic("Mathematik")
    assert topic.id is not None
    names = [t.name for t in db.list_topics()]
    assert "Mathematik" in names


def test_add_topic_rejects_empty_name(db):
    with pytest.raises(ValueError):
        db.add_topic("   ")


def test_add_card_creates_initial_review_state(db):
    topic = db.add_topic("Biologie")
    card = db.add_card(Card(id=None, topic_id=topic.id, question_text="Was ist eine Zelle?", answer_text="Grundbaustein des Lebens"))
    state = db.get_review_state(card.id)
    assert state is not None
    assert state.box == 0
    assert state.mastered is False


def test_delete_topic_cascades_to_cards(db):
    topic = db.add_topic("Chemie")
    card = db.add_card(Card(id=None, topic_id=topic.id, question_text="H2O?", answer_text="Wasser"))
    db.delete_topic(topic.id)
    assert db.get_card(card.id) is None


def test_due_cards_excludes_mastered(db):
    topic = db.add_topic("Physik")
    card = db.add_card(Card(id=None, topic_id=topic.id, question_text="F=?", answer_text="m*a"))
    state = db.get_review_state(card.id)
    state.mastered = True
    db.save_review_state(state)
    assert db.due_cards(only_due=False) == []


def test_due_cards_filters_by_topic(db):
    t1 = db.add_topic("Thema A")
    t2 = db.add_topic("Thema B")
    card_a = db.add_card(Card(id=None, topic_id=t1.id, question_text="A?", answer_text="a"))
    db.add_card(Card(id=None, topic_id=t2.id, question_text="B?", answer_text="b"))
    result = db.due_cards(topic_ids=[t1.id], only_due=False)
    assert [c.id for c in result] == [card_a.id]


def test_mastered_cards_returns_only_mastered(db):
    topic = db.add_topic("Erdkunde")
    mastered_card = db.add_card(Card(id=None, topic_id=topic.id, question_text="Hauptstadt?", answer_text="Berlin"))
    db.add_card(Card(id=None, topic_id=topic.id, question_text="Fluss?", answer_text="Rhein"))
    state = db.get_review_state(mastered_card.id)
    state.mastered = True
    db.save_review_state(state)

    result = db.mastered_cards()
    assert [c.id for c in result] == [mastered_card.id]


def test_mastered_cards_filters_by_topic(db):
    t1 = db.add_topic("Thema A")
    t2 = db.add_topic("Thema B")
    card_a = db.add_card(Card(id=None, topic_id=t1.id, question_text="A?", answer_text="a"))
    card_b = db.add_card(Card(id=None, topic_id=t2.id, question_text="B?", answer_text="b"))
    for card in (card_a, card_b):
        state = db.get_review_state(card.id)
        state.mastered = True
        db.save_review_state(state)

    result = db.mastered_cards(topic_ids=[t1.id])
    assert [c.id for c in result] == [card_a.id]


def test_reset_review_state_returns_card_to_box_zero(db):
    topic = db.add_topic("Geschichte")
    card = db.add_card(Card(id=None, topic_id=topic.id, question_text="Wann?", answer_text="1990"))
    state = db.get_review_state(card.id)
    state.box = 3
    state.mastery_streak = 2
    db.save_review_state(state)
    db.reset_review_state(card.id)
    reset_state = db.get_review_state(card.id)
    assert reset_state.box == 0
    assert reset_state.mastery_streak == 0
