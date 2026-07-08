import io

from app import create_app, get_db
from app.core.models import Card, ChoiceOption
from tests.conftest import add_card


def test_export_then_import_round_trip_keeps_multiple_choice(app, client, topic_id, tmp_path):
    with app.app_context():
        get_db().add_card(Card(
            id=None, topic_id=topic_id, question_text="Hauptstadt von Frankreich?", answer_text="",
            card_type="multiple_choice",
            choices=[
                ChoiceOption(id=None, card_id=0, text="Paris", is_correct=True, position=0),
                ChoiceOption(id=None, card_id=0, text="Berlin", is_correct=False, position=1),
            ],
        ))

    r = client.get("/backup/export")
    zip_bytes = r.data

    other_app = create_app(data_dir=tmp_path / "mc_data")
    other_app.testing = True
    other_client = other_app.test_client()
    other_client.post(
        "/backup/import",
        data={"file": (io.BytesIO(zip_bytes), "backup.zip"), "mode": "merge"},
        content_type="multipart/form-data",
    )

    with other_app.app_context():
        db = get_db()
        card = next(c for c in db.list_cards() if c.question_text == "Hauptstadt von Frankreich?")
        card = db.get_card(card.id)
        assert card.card_type == "multiple_choice"
        assert len(card.choices) == 2
        assert next(c for c in card.choices if c.is_correct).text == "Paris"


def test_export_then_import_round_trip(app, client, topic_id, tmp_path):
    add_card(app, topic_id, question="Frage?", answer="Antwort")

    r = client.get("/backup/export")
    assert r.status_code == 200
    assert r.content_type == "application/zip"
    zip_bytes = r.data

    other_app = create_app(data_dir=tmp_path / "other_data")
    other_app.testing = True
    other_client = other_app.test_client()

    r = other_client.post(
        "/backup/import",
        data={"file": (io.BytesIO(zip_bytes), "backup.zip"), "mode": "merge"},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"Import abgeschlossen" in r.data

    with other_app.app_context():
        db = get_db()
        assert [t.name for t in db.list_topics()] == ["Python"]
        assert [c.question_text for c in db.list_cards()] == ["Frage?"]


def test_import_without_file_shows_error(client):
    r = client.post("/backup/import", data={"mode": "merge"}, content_type="multipart/form-data",
                     follow_redirects=True)
    assert b"Backup-Datei ausw" in r.data


def test_import_invalid_zip_shows_error(client):
    r = client.post(
        "/backup/import",
        data={"file": (io.BytesIO(b"not a zip file"), "broken.zip"), "mode": "merge"},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"Import fehlgeschlagen" in r.data
