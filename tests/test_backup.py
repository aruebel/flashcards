from pathlib import Path

import pytest

from flashcards import backup
from flashcards.database import Database
from flashcards.models import Card
from flashcards.srs import KOMPLETT_SICHER, next_state


@pytest.fixture
def source_db(tmp_path: Path):
    database = Database(tmp_path / "source.db")
    yield database
    database.close()


@pytest.fixture
def target_db(tmp_path: Path):
    database = Database(tmp_path / "target.db")
    yield database
    database.close()


def _add_sample_card(db, topic_name="Mathematik", question="Was ist 2+2?", answer="4"):
    topic = next((t for t in db.list_topics() if t.name == topic_name), None) or db.add_topic(topic_name)
    return db.add_card(Card(id=None, topic_id=topic.id, question_text=question, answer_text=answer))


def test_export_then_import_recreates_topics_and_cards(source_db, target_db, tmp_path):
    _add_sample_card(source_db)
    zip_path = tmp_path / "backup.zip"
    backup.export_to_zip(source_db, zip_path)

    result = backup.import_from_zip(target_db, tmp_path / "target_data", zip_path, mode="merge")

    assert result.topics_added == 1
    assert result.cards_added == 1
    assert result.cards_skipped == 0
    topics = target_db.list_topics()
    assert [t.name for t in topics] == ["Mathematik"]
    cards = target_db.list_cards()
    assert cards[0].question_text == "Was ist 2+2?"


def test_import_preserves_review_state(source_db, target_db, tmp_path):
    card = _add_sample_card(source_db)
    state = source_db.get_review_state(card.id)
    state = next_state(state, KOMPLETT_SICHER)
    state = next_state(state, KOMPLETT_SICHER)
    source_db.save_review_state(state)

    zip_path = tmp_path / "backup.zip"
    backup.export_to_zip(source_db, zip_path)
    backup.import_from_zip(target_db, tmp_path / "target_data", zip_path, mode="merge")

    imported_card = target_db.list_cards()[0]
    imported_state = target_db.get_review_state(imported_card.id)
    assert imported_state.mastery_streak == 2
    assert imported_state.mastered is False


def test_merge_skips_duplicate_cards_on_second_import(source_db, target_db, tmp_path):
    _add_sample_card(source_db)
    zip_path = tmp_path / "backup.zip"
    backup.export_to_zip(source_db, zip_path)

    backup.import_from_zip(target_db, tmp_path / "target_data", zip_path, mode="merge")
    result_second = backup.import_from_zip(target_db, tmp_path / "target_data", zip_path, mode="merge")

    assert result_second.cards_added == 0
    assert result_second.cards_skipped == 1
    assert len(target_db.list_cards()) == 1


def test_replace_mode_wipes_existing_data_first(source_db, target_db, tmp_path):
    _add_sample_card(target_db, topic_name="Alt", question="Altes Wissen?", answer="Ja")
    _add_sample_card(source_db, topic_name="Neu", question="Neues Wissen?", answer="Ja")

    zip_path = tmp_path / "backup.zip"
    backup.export_to_zip(source_db, zip_path)
    backup.import_from_zip(target_db, tmp_path / "target_data", zip_path, mode="replace")

    topics = [t.name for t in target_db.list_topics()]
    assert topics == ["Neu"]
    cards = target_db.list_cards()
    assert len(cards) == 1
    assert cards[0].question_text == "Neues Wissen?"


def test_import_rejects_unknown_mode(source_db, target_db, tmp_path):
    _add_sample_card(source_db)
    zip_path = tmp_path / "backup.zip"
    backup.export_to_zip(source_db, zip_path)
    with pytest.raises(ValueError):
        backup.import_from_zip(target_db, tmp_path / "target_data", zip_path, mode="invalid")


def test_export_with_multiple_topics_and_cards(source_db, tmp_path):
    _add_sample_card(source_db, topic_name="A", question="A1?", answer="a")
    _add_sample_card(source_db, topic_name="A", question="A2?", answer="a")
    _add_sample_card(source_db, topic_name="B", question="B1?", answer="b")

    zip_path = tmp_path / "backup.zip"
    backup.export_to_zip(source_db, zip_path)

    target = Database(tmp_path / "target2.db")
    try:
        result = backup.import_from_zip(target, tmp_path / "target2_data", zip_path, mode="merge")
        assert result.topics_added == 2
        assert result.cards_added == 3
        assert len(target.list_cards()) == 3
    finally:
        target.close()
