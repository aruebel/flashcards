import io

from app import get_db

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c6360000002000100e221bc330000000049454e44ae426082"
)


def test_create_card_clears_form_and_keeps_topic(client, topic_id):
    r = client.post(
        "/cards/new",
        data={
            "topic_id": topic_id, "question_text": "Was ist Python?", "answer_text": "Eine Sprache",
            "question_image_path": "", "answer_image_path": "",
        },
        follow_redirects=True,
    )
    assert b"gespeichert" in r.data
    assert b"Was ist Python?" not in r.data  # Formular wurde geleert
    assert f'value="{topic_id}" selected'.encode() in r.data  # Thema bleibt ausgewaehlt


def test_created_card_appears_in_index(app, client, topic_id):
    client.post("/cards/new", data={
        "topic_id": topic_id, "question_text": "Frage X", "answer_text": "Antwort X",
        "question_image_path": "", "answer_image_path": "",
    })
    r = client.get("/")
    assert b"Frage X" in r.data


def test_create_card_rejects_empty_question(client, topic_id):
    r = client.post("/cards/new", data={
        "topic_id": topic_id, "question_text": "", "answer_text": "Antwort",
        "question_image_path": "", "answer_image_path": "",
    }, follow_redirects=True)
    assert b"Frage darf nicht leer sein" in r.data


def test_edit_card_redirects_to_index(app, client, topic_id):
    from tests.conftest import add_card
    card = add_card(app, topic_id, question="Alt", answer="alt")
    r = client.post(f"/cards/{card.id}/edit", data={
        "topic_id": topic_id, "question_text": "Neu", "answer_text": "neu",
        "question_image_path": "", "answer_image_path": "",
    })
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/")
    with app.app_context():
        assert get_db().get_card(card.id).question_text == "Neu"


def test_delete_card(app, client, topic_id):
    from tests.conftest import add_card
    card = add_card(app, topic_id)
    client.post(f"/cards/{card.id}/delete")
    with app.app_context():
        assert get_db().get_card(card.id) is None


def test_reset_card_progress(app, client, topic_id):
    from tests.conftest import add_card
    from app.core import srs
    card = add_card(app, topic_id)
    with app.app_context():
        db = get_db()
        state = db.get_review_state(card.id)
        state = srs.next_state(state, srs.KOMPLETT_SICHER)
        db.save_review_state(state)

    client.post(f"/cards/{card.id}/reset")
    with app.app_context():
        state = get_db().get_review_state(card.id)
    assert state.box == 0
    assert state.mastery_streak == 0


def test_image_upload_returns_media_url(client):
    r = client.post(
        "/cards/image-upload",
        data={"file": (io.BytesIO(PNG_BYTES), "test.png")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["url"].startswith("/media/")


def test_image_upload_rejects_non_image_extension(client):
    r = client.post(
        "/cards/image-upload",
        data={"file": (io.BytesIO(b"not an image"), "evil.exe")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 400


def test_create_multiple_choice_card(app, client, topic_id):
    r = client.post(
        "/cards/new",
        data={
            "topic_id": topic_id, "card_type": "multiple_choice",
            "question_text": "Hauptstadt von Frankreich?", "answer_text": "",
            "question_image_path": "", "answer_image_path": "",
            "choice_text_1": "Paris", "choice_correct_1": "1",
            "choice_text_2": "Berlin",
            "choice_text_3": "Madrid",
        },
        follow_redirects=True,
    )
    assert b"gespeichert" in r.data
    with app.app_context():
        db = get_db()
        card = db.get_card(db.list_cards(topic_ids=[topic_id])[0].id)
        assert card.card_type == "multiple_choice"
        assert len(card.choices) == 3
        assert sum(c.is_correct for c in card.choices) == 1
        assert next(c for c in card.choices if c.is_correct).text == "Paris"


def test_create_multiple_choice_card_requires_two_options(client, topic_id):
    r = client.post(
        "/cards/new",
        data={
            "topic_id": topic_id, "card_type": "multiple_choice",
            "question_text": "Frage?", "answer_text": "",
            "question_image_path": "", "answer_image_path": "",
            "choice_text_1": "Einzige Option", "choice_correct_1": "1",
        },
        follow_redirects=True,
    )
    assert "mindestens 2 Antwortmoeglichkeiten".encode() in r.data


def test_create_multiple_choice_card_requires_correct_option(client, topic_id):
    r = client.post(
        "/cards/new",
        data={
            "topic_id": topic_id, "card_type": "multiple_choice",
            "question_text": "Frage?", "answer_text": "",
            "question_image_path": "", "answer_image_path": "",
            "choice_text_1": "A", "choice_text_2": "B",
        },
        follow_redirects=True,
    )
    assert "mindestens eine richtige Antwort".encode() in r.data
