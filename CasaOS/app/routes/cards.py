"""Karten anlegen/bearbeiten/loeschen sowie Bild-Upload (Datei oder Clipboard-Paste)."""
from pathlib import Path

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for

from .. import get_db
from ..core import images as image_store
from ..core.models import Card, ChoiceOption, PuzzlePair

cards_bp = Blueprint("cards", __name__)

ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

CARD_TYPE_LABELS = {"multiple_choice": "Multiple Choice", "typed": "Texteingabe", "puzzle": "Puzzle"}


def _validate_answer(card_type: str, answer_text: str, answer_image_path, form):
    """Validiert/normalisiert die kartentyp-spezifischen Antwortfelder.

    Gibt (card_type, answer_text, answer_image_path, choices, puzzle_pairs, error_message)
    zurueck; error_message ist None, wenn alles gueltig ist.
    """
    if card_type == "multiple_choice":
        choices = _parse_choices(form)
        if len(choices) < 2:
            return card_type, answer_text, answer_image_path, choices, [], \
                "Bitte mindestens 2 Antwortmoeglichkeiten angeben."
        if not any(c.is_correct for c in choices):
            return card_type, answer_text, answer_image_path, choices, [], \
                "Bitte mindestens eine richtige Antwort markieren."
        return card_type, "", None, choices, [], None

    if card_type == "typed":
        if not answer_text:
            return card_type, answer_text, answer_image_path, [], [], \
                "Bei Texteingabe-Karten muss die exakt einzutippende Antwort als Text vorgegeben werden."
        return card_type, answer_text, None, [], [], None

    if card_type == "puzzle":
        pairs = _parse_puzzle_pairs(form)
        if len(pairs) < 2:
            return card_type, answer_text, answer_image_path, [], pairs, \
                "Bitte mindestens 2 Puzzleteile-Paare angeben."
        return card_type, "", None, [], pairs, None

    if not answer_text and not answer_image_path:
        return "text", answer_text, answer_image_path, [], [], "Die Antwort darf nicht leer sein."
    return "text", answer_text, answer_image_path, [], [], None


def _parse_choices(form) -> list[ChoiceOption]:
    """Liest dynamisch angelegte Antwortmoeglichkeiten (choice_text_<uid> / choice_correct_<uid>) aus."""
    uids = []
    seen = set()
    for key in form.keys():
        if key.startswith("choice_text_") and key not in seen:
            seen.add(key)
            uids.append(key[len("choice_text_"):])

    choices = []
    for position, uid in enumerate(uids):
        text = form.get(f"choice_text_{uid}", "").strip()
        if not text:
            continue
        is_correct = form.get(f"choice_correct_{uid}") == "1"
        choices.append(ChoiceOption(id=None, card_id=0, text=text, is_correct=is_correct, position=position))
    return choices


def _parse_puzzle_pairs(form) -> list[PuzzlePair]:
    """Liest dynamisch angelegte Puzzle-Paare (puzzle_left_<uid> / puzzle_right_<uid>) aus."""
    uids = []
    seen = set()
    for key in form.keys():
        if key.startswith("puzzle_left_") and key not in seen:
            seen.add(key)
            uids.append(key[len("puzzle_left_"):])

    pairs = []
    for position, uid in enumerate(uids):
        left_text = form.get(f"puzzle_left_{uid}", "").strip()
        right_text = form.get(f"puzzle_right_{uid}", "").strip()
        if not left_text or not right_text:
            continue
        pairs.append(PuzzlePair(id=None, card_id=0, left_text=left_text, right_text=right_text, position=position))
    return pairs


@cards_bp.get("/")
def index():
    db = get_db()
    topics = db.list_topics()
    topic_filter = request.args.get("topic_id", type=int)
    topic_ids = [topic_filter] if topic_filter else None
    topics_by_id = {t.id: t.name for t in topics}

    cards = []
    for card in db.list_cards(topic_ids):
        state = db.get_review_state(card.id)
        status = "Gelernt" if state.mastered else f"Box {state.box}, faellig {state.due_date.isoformat()}"
        cards.append({
            "id": card.id,
            "topic_name": topics_by_id.get(card.topic_id, "?"),
            "preview": (card.question_text[:80] or "(nur Bild)"),
            "type_label": CARD_TYPE_LABELS.get(card.card_type, "Text"),
            "status": status,
        })

    return render_template("index.html", cards=cards, topics=topics, topic_filter=topic_filter)


@cards_bp.get("/cards/new")
def new_card_form():
    db = get_db()
    topics = db.list_topics()
    if not topics:
        flash("Bitte zuerst ein Thema anlegen.", "error")
        return redirect(url_for("topics.list_topics"))
    topic_id = request.args.get("topic_id", type=int) or topics[0].id
    return render_template("card_form.html", card=None, topics=topics, selected_topic_id=topic_id,
                            just_saved=request.args.get("saved") == "1")


@cards_bp.post("/cards/new")
def create_card():
    db = get_db()
    topic_id = request.form.get("topic_id", type=int)
    card_type = request.form.get("card_type", "text")
    question_text = request.form.get("question_text", "").strip()
    answer_text = request.form.get("answer_text", "").strip()
    question_image_path = request.form.get("question_image_path") or None
    answer_image_path = request.form.get("answer_image_path") or None

    if not question_text and not question_image_path:
        flash("Die Frage darf nicht leer sein.", "error")
        return redirect(url_for("cards.new_card_form", topic_id=topic_id))

    card_type, answer_text, answer_image_path, choices, puzzle_pairs, error = _validate_answer(
        card_type, answer_text, answer_image_path, request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("cards.new_card_form", topic_id=topic_id))

    db.add_card(Card(
        id=None, topic_id=topic_id, question_text=question_text, answer_text=answer_text,
        question_image_path=question_image_path, answer_image_path=answer_image_path,
        card_type=card_type, choices=choices, puzzle_pairs=puzzle_pairs,
    ))
    flash("Karte gespeichert.", "success")
    # Formular bleibt "offen": leeres Formular mit gleichem Thema, analog
    # zum Verhalten der Desktop-App beim Anlegen neuer Karten.
    return redirect(url_for("cards.new_card_form", topic_id=topic_id, saved="1"))


@cards_bp.get("/cards/<int:card_id>/edit")
def edit_card_form(card_id):
    db = get_db()
    card = db.get_card(card_id)
    if card is None:
        flash("Karte nicht gefunden.", "error")
        return redirect(url_for("cards.index"))
    return render_template("card_form.html", card=card, topics=db.list_topics(),
                            selected_topic_id=card.topic_id, just_saved=False)


@cards_bp.post("/cards/<int:card_id>/edit")
def update_card(card_id):
    db = get_db()
    card = db.get_card(card_id)
    if card is None:
        flash("Karte nicht gefunden.", "error")
        return redirect(url_for("cards.index"))

    card_type = request.form.get("card_type", "text")
    question_text = request.form.get("question_text", "").strip()
    answer_text = request.form.get("answer_text", "").strip()
    question_image_path = request.form.get("question_image_path") or None
    answer_image_path = request.form.get("answer_image_path") or None

    if not question_text and not question_image_path:
        flash("Die Frage darf nicht leer sein.", "error")
        return redirect(url_for("cards.edit_card_form", card_id=card_id))

    card_type, answer_text, answer_image_path, choices, puzzle_pairs, error = _validate_answer(
        card_type, answer_text, answer_image_path, request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("cards.edit_card_form", card_id=card_id))

    card.topic_id = request.form.get("topic_id", type=int)
    card.question_text = question_text
    card.answer_text = answer_text
    card.question_image_path = question_image_path
    card.answer_image_path = answer_image_path
    card.card_type = card_type
    card.choices = choices
    card.puzzle_pairs = puzzle_pairs
    db.update_card(card)
    flash("Karte gespeichert.", "success")
    return redirect(url_for("cards.index"))


@cards_bp.post("/cards/<int:card_id>/delete")
def delete_card(card_id):
    db = get_db()
    card = db.get_card(card_id)
    if card:
        image_store.delete_image(card.question_image_path)
        image_store.delete_image(card.answer_image_path)
        db.delete_card(card_id)
        flash("Karte geloescht.", "success")
    return redirect(url_for("cards.index"))


@cards_bp.post("/cards/<int:card_id>/reset")
def reset_card(card_id):
    db = get_db()
    db.reset_review_state(card_id)
    flash("Lernstatus zurueckgesetzt.", "success")
    return redirect(url_for("cards.index"))


@cards_bp.post("/cards/image-upload")
def upload_image():
    """Wird per JS sowohl fuer Datei-Auswahl als auch fuer Clipboard-Paste aufgerufen."""
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "Keine Bilddatei erhalten."}), 400

    suffix = Path(file.filename).suffix.lower() or ".png"
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        return jsonify({"error": "Nicht unterstuetztes Bildformat."}), 400

    data = file.read()
    path = image_store.save_image_bytes(data, suffix, current_app.config["DATA_DIR"])
    return jsonify({"path": path, "url": f"/media/{Path(path).name}"})
