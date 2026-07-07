"""Karten anlegen/bearbeiten/loeschen sowie Bild-Upload (Datei oder Clipboard-Paste)."""
from pathlib import Path

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for

from .. import get_db
from ..core import images as image_store
from ..core.models import Card

cards_bp = Blueprint("cards", __name__)

ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


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
    question_text = request.form.get("question_text", "").strip()
    answer_text = request.form.get("answer_text", "").strip()
    question_image_path = request.form.get("question_image_path") or None
    answer_image_path = request.form.get("answer_image_path") or None

    if not question_text and not question_image_path:
        flash("Die Frage darf nicht leer sein.", "error")
        return redirect(url_for("cards.new_card_form", topic_id=topic_id))
    if not answer_text and not answer_image_path:
        flash("Die Antwort darf nicht leer sein.", "error")
        return redirect(url_for("cards.new_card_form", topic_id=topic_id))

    db.add_card(Card(
        id=None, topic_id=topic_id, question_text=question_text, answer_text=answer_text,
        question_image_path=question_image_path, answer_image_path=answer_image_path,
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

    question_text = request.form.get("question_text", "").strip()
    answer_text = request.form.get("answer_text", "").strip()
    question_image_path = request.form.get("question_image_path") or None
    answer_image_path = request.form.get("answer_image_path") or None

    if not question_text and not question_image_path:
        flash("Die Frage darf nicht leer sein.", "error")
        return redirect(url_for("cards.edit_card_form", card_id=card_id))
    if not answer_text and not answer_image_path:
        flash("Die Antwort darf nicht leer sein.", "error")
        return redirect(url_for("cards.edit_card_form", card_id=card_id))

    card.topic_id = request.form.get("topic_id", type=int)
    card.question_text = question_text
    card.answer_text = answer_text
    card.question_image_path = question_image_path
    card.answer_image_path = answer_image_path
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
