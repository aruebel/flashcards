import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app, get_db
from app.core.models import Card


@pytest.fixture
def app(tmp_path):
    application = create_app(data_dir=tmp_path / "data")
    application.testing = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def topic_id(app, client):
    client.post("/topics/new", data={"name": "Python"})
    with app.app_context():
        return get_db().list_topics()[0].id


def add_card(app, topic_id, question="Frage?", answer="Antwort"):
    with app.app_context():
        db = get_db()
        return db.add_card(Card(id=None, topic_id=topic_id, question_text=question, answer_text=answer))
