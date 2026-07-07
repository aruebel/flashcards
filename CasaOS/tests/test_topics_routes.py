from app import get_db


def test_add_topic_shows_in_list(client):
    client.post("/topics/new", data={"name": "Mathematik"})
    r = client.get("/topics/")
    assert b"Mathematik" in r.data


def test_add_topic_rejects_empty_name(client):
    r = client.post("/topics/new", data={"name": "   "}, follow_redirects=True)
    assert b"leer sein" in r.data


def test_rename_topic(app, client, topic_id):
    client.post(f"/topics/{topic_id}/rename", data={"name": "Umbenannt"})
    with app.app_context():
        names = [t.name for t in get_db().list_topics()]
    assert names == ["Umbenannt"]


def test_delete_topic_cascades_cards(app, client, topic_id):
    from tests.conftest import add_card
    card = add_card(app, topic_id)
    client.post(f"/topics/{topic_id}/delete")
    with app.app_context():
        db = get_db()
        assert db.list_topics() == []
        assert db.get_card(card.id) is None
