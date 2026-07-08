from app import get_db
from app.core import srs
from app.core.models import Card, ChoiceOption
from tests.conftest import add_card


def _add_cards(app, topic_id, count):
    return [add_card(app, topic_id, question=f"F{i}", answer=f"A{i}") for i in range(count)]


def test_full_quiz_flow_rate_all_cards(app, client, topic_id):
    _add_cards(app, topic_id, 2)

    r = client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"},
                     follow_redirects=True)
    assert b"Karte 1 von 2" in r.data

    r = client.post("/quiz/reveal", follow_redirects=True)
    assert b"Antwort" in r.data

    r = client.post("/quiz/rate", data={"rating": srs.SICHER}, follow_redirects=True)
    assert b"Karte 2 von 2" in r.data

    client.post("/quiz/reveal")
    r = client.post("/quiz/rate", data={"rating": srs.SICHER}, follow_redirects=True)
    assert b"Fertig!" in r.data
    assert b"2 Karte(n) abgefragt" in r.data


def test_count_limit_selects_subset(app, client, topic_id):
    _add_cards(app, topic_id, 15)
    r = client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "10"},
                     follow_redirects=True)
    assert b"Karte 1 von 10" in r.data


def test_fewer_cards_available_shows_notice(app, client, topic_id):
    _add_cards(app, topic_id, 3)
    r = client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "10"},
                     follow_redirects=True)
    assert "aktuell sind aber nur 3 verfuegbar".encode() in r.data
    assert b"Karte 1 von 3" in r.data


def test_end_early_preserves_progress_and_reports_partial_count(app, client, topic_id):
    cards = _add_cards(app, topic_id, 5)
    client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"})
    client.post("/quiz/reveal")
    client.post("/quiz/rate", data={"rating": srs.SICHER})

    r = client.post("/quiz/end", follow_redirects=True)
    assert b"vorzeitig beendet" in r.data
    assert b"1 von 5" in r.data

    with app.app_context():
        db = get_db()
        rated_card = next(c for c in cards if db.get_review_state(c.id).total_reviews > 0)
        assert db.get_review_state(rated_card.id).box > 0


def test_review_mastered_mode_only_returns_mastered_cards(app, client, topic_id):
    cards = _add_cards(app, topic_id, 2)
    with app.app_context():
        db = get_db()
        state = db.get_review_state(cards[0].id)
        for _ in range(3):
            state = srs.next_state(state, srs.KOMPLETT_SICHER)
        db.save_review_state(state)
        assert db.get_review_state(cards[0].id).mastered

    r = client.post("/quiz/setup", data={"review_mastered": "1", "count": "all"}, follow_redirects=True)
    assert b"Karte 1 von 1" in r.data


def test_rating_below_komplett_sicher_drops_mastered_card_back_into_rotation(app, client, topic_id):
    card = add_card(app, topic_id)
    with app.app_context():
        db = get_db()
        state = db.get_review_state(card.id)
        for _ in range(3):
            state = srs.next_state(state, srs.KOMPLETT_SICHER)
        db.save_review_state(state)

    client.post("/quiz/setup", data={"review_mastered": "1", "count": "all"})
    client.post("/quiz/reveal")
    r = client.post("/quiz/rate", data={"rating": srs.NEIN}, follow_redirects=True)
    assert b"zurueckgeholt" in r.data

    with app.app_context():
        assert get_db().get_review_state(card.id).mastered is False


def test_no_cards_available_shows_error_and_redirects_to_setup(client, topic_id):
    r = client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"},
                     follow_redirects=True)
    assert b"keine faelligen Karten" in r.data


def _add_multiple_choice_card(app, topic_id):
    with app.app_context():
        db = get_db()
        return db.add_card(Card(
            id=None, topic_id=topic_id, question_text="Hauptstadt von Frankreich?", answer_text="",
            card_type="multiple_choice",
            choices=[
                ChoiceOption(id=None, card_id=0, text="Paris", is_correct=True, position=0),
                ChoiceOption(id=None, card_id=0, text="Berlin", is_correct=False, position=1),
            ],
        ))


def test_multiple_choice_card_shows_checkable_options(app, client, topic_id):
    _add_multiple_choice_card(app, topic_id)
    r = client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"},
                     follow_redirects=True)
    assert b"Paris" in r.data
    assert b"Berlin" in r.data
    assert b'name="choice_ids"' in r.data
    assert b"Antwort pruefen" in r.data


def test_selecting_wrong_option_does_not_reveal_immediately(app, client, topic_id):
    """Regression: bei mehreren richtigen Antworten darf die erste Auswahl allein
    noch nicht auswerten - erst der Submit-Button deckt die Antwort auf."""
    card = _add_multiple_choice_card(app, topic_id)
    client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"})

    r = client.get("/quiz/session")
    assert b'name="rating"' not in r.data  # noch keine Bewertung, da nichts abgesendet wurde
    assert b"deine Wahl" not in r.data


def test_answering_multiple_choice_reveals_answer_and_keeps_question(app, client, topic_id):
    card = _add_multiple_choice_card(app, topic_id)
    client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"})

    wrong_choice = next(c for c in card.choices if not c.is_correct)
    r = client.post("/quiz/answer", data={"choice_ids": [wrong_choice.id]}, follow_redirects=True)

    assert b"Hauptstadt von Frankreich?" in r.data  # Frage bleibt sichtbar
    assert b"Antwort" in r.data
    assert b"deine Wahl" in r.data  # falsch gewaehlte Option markiert
    assert b'name="rating"' in r.data  # Bewertung weiterhin moeglich


def _add_multi_correct_card(app, topic_id):
    with app.app_context():
        db = get_db()
        return db.add_card(Card(
            id=None, topic_id=topic_id, question_text="Welche sind Primzahlen?", answer_text="",
            card_type="multiple_choice",
            choices=[
                ChoiceOption(id=None, card_id=0, text="2", is_correct=True, position=0),
                ChoiceOption(id=None, card_id=0, text="3", is_correct=True, position=1),
                ChoiceOption(id=None, card_id=0, text="4", is_correct=False, position=2),
            ],
        ))


def test_multiple_correct_answers_can_be_selected_together(app, client, topic_id):
    card = _add_multi_correct_card(app, topic_id)
    client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"})

    correct_ids = [c.id for c in card.choices if c.is_correct]
    r = client.post("/quiz/answer", data={"choice_ids": correct_ids}, follow_redirects=True)
    body = r.data.decode("utf-8")

    assert body.count("nicht gewaehlt") == 0  # beide richtigen wurden ausgewaehlt, keine verpasst
    assert body.count("deine Wahl") == 2  # beide richtigen als "deine Wahl" markiert
    assert "✗" not in body  # kein Kreuz, da keine falsche Antwort ausgewaehlt wurde


def test_choice_order_stays_stable_between_question_and_result(app, client, topic_id):
    card = _add_multiple_choice_card(app, topic_id)
    client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"})

    r1 = client.get("/quiz/session")
    order1 = [name for name in ("Paris", "Berlin") if r1.data.find(name.encode()) >= 0]
    positions1 = sorted(order1, key=lambda n: r1.data.find(n.encode()))

    correct_id = next(c.id for c in card.choices if c.is_correct)
    client.post("/quiz/answer", data={"choice_ids": [correct_id]})
    r2 = client.get("/quiz/session")
    positions2 = sorted(("Paris", "Berlin"), key=lambda n: r2.data.find(n.encode()))

    assert positions1 == positions2  # Reihenfolge bleibt zwischen Frage- und Ergebnisansicht gleich


def _add_typed_answer_card(app, topic_id):
    with app.app_context():
        db = get_db()
        return db.add_card(Card(
            id=None, topic_id=topic_id, question_text="Aktuelles Verzeichnis anzeigen?",
            answer_text="pwd", card_type="typed",
        ))


def test_typed_card_shows_input_field_before_answering(app, client, topic_id):
    _add_typed_answer_card(app, topic_id)
    r = client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"},
                     follow_redirects=True)
    assert b'name="typed_answer"' in r.data
    assert b"pwd" not in r.data  # Loesung wird vor dem Absenden nicht verraten
    assert b'name="rating"' not in r.data


def test_typed_card_marks_correct_answer(app, client, topic_id):
    _add_typed_answer_card(app, topic_id)
    client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"})

    r = client.post("/quiz/submit-typed", data={"typed_answer": "pwd"}, follow_redirects=True)
    assert "✓ Richtig!".encode() in r.data
    assert b'name="rating"' in r.data


def test_typed_card_trims_whitespace_before_comparing(app, client, topic_id):
    _add_typed_answer_card(app, topic_id)
    client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"})

    r = client.post("/quiz/submit-typed", data={"typed_answer": "  pwd  "}, follow_redirects=True)
    assert "✓ Richtig!".encode() in r.data


def test_typed_card_marks_wrong_answer_and_shows_expected(app, client, topic_id):
    _add_typed_answer_card(app, topic_id)
    client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"})

    r = client.post("/quiz/submit-typed", data={"typed_answer": "ls"}, follow_redirects=True)
    body = r.data.decode("utf-8")
    assert "Nicht ganz richtig" in body
    assert "<code>ls</code>" in body  # eigene Eingabe wird gezeigt
    assert "<code>pwd</code>" in body  # erwartete Antwort wird gezeigt


def test_revealed_text_card_still_shows_question(app, client, topic_id):
    add_card(app, topic_id, question="Was ist Python?", answer="Eine Sprache")
    client.post("/quiz/setup", data={"review_mastered": "0", "only_due": "on", "count": "all"})
    r = client.post("/quiz/reveal", follow_redirects=True)
    assert b"Was ist Python?" in r.data
    assert b"Eine Sprache" in r.data
