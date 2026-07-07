import io

from app import create_app, get_db
from tests.conftest import add_card


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
