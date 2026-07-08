"""Abfrage-Modus: Themenauswahl (Setup) und Abfrage-Session.

Der Session-Zustand (Kartenreihenfolge, Position, Zaehler) liegt in der
signierten Flask-Session (Cookie) - dort stehen nur Karten-IDs und Zahlen,
nie komplette Karteninhalte, daher bleibt das kompakt genug fuer ein Cookie.
"""
import random

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .. import get_db
from ..core import srs

quiz_bp = Blueprint("quiz", __name__, url_prefix="/quiz")

COUNT_CHOICES = ["10", "20", "30", "all"]


@quiz_bp.get("/setup")
def setup():
    db = get_db()
    review_mastered = request.args.get("review_mastered") == "1"
    return render_template(
        "quiz_setup.html", topics=db.list_topics(), review_mastered=review_mastered,
        count_choices=COUNT_CHOICES,
    )


@quiz_bp.post("/setup")
def start():
    db = get_db()
    review_mastered = request.form.get("review_mastered") == "1"
    topic_ids = [int(v) for v in request.form.getlist("topic_ids")] or None

    if review_mastered:
        cards = db.mastered_cards(topic_ids=topic_ids)
        empty_message = "Es gibt aktuell keine gelernten Karten fuer diese Auswahl."
    else:
        only_due = request.form.get("only_due") == "on"
        cards = db.due_cards(topic_ids=topic_ids, only_due=only_due)
        empty_message = "Es gibt aktuell keine faelligen Karten fuer diese Auswahl."

    if not cards:
        flash(empty_message, "error")
        return redirect(url_for("quiz.setup", review_mastered="1" if review_mastered else "0"))

    random.shuffle(cards)

    requested = request.form.get("count", "all")
    if requested != "all":
        limit = int(requested)
        if len(cards) > limit:
            cards = cards[:limit]
        else:
            flash(
                f"Angefragt waren {limit} Karten, aktuell sind aber nur {len(cards)} verfuegbar. "
                f"Es werden nur diese {len(cards)} abgefragt.",
                "info",
            )

    session["quiz"] = {
        "card_ids": [c.id for c in cards],
        "index": 0,
        "revealed": False,
        "selected_choice_ids": [],
        "choice_order": None,
        "newly_mastered": 0,
        "dropped": 0,
    }
    return redirect(url_for("quiz.quiz_session"))


@quiz_bp.get("/session")
def quiz_session():
    db = get_db()
    quiz = session.get("quiz")
    if not quiz:
        return redirect(url_for("quiz.setup"))

    total = len(quiz["card_ids"])
    if quiz["index"] >= total:
        return redirect(url_for("quiz.finish"))

    card = db.get_card(quiz["card_ids"][quiz["index"]])

    if card.card_type == "multiple_choice":
        # Reihenfolge wird einmal pro Karte gewuerfelt und in der Session
        # gehalten, damit sie zwischen Frage- und Ergebnisansicht stabil bleibt.
        order = quiz.get("choice_order")
        if not order:
            order = [c.id for c in card.choices]
            random.shuffle(order)
            quiz["choice_order"] = order
            session["quiz"] = quiz
        order_index = {choice_id: position for position, choice_id in enumerate(order)}
        card.choices.sort(key=lambda c: order_index.get(c.id, 0))

    return render_template(
        "quiz_session.html", card=card, revealed=quiz["revealed"],
        selected_choice_ids=quiz.get("selected_choice_ids", []),
        position=quiz["index"] + 1, total=total, ratings=srs.RATING_LABELS,
    )


@quiz_bp.post("/reveal")
def reveal():
    quiz = session.get("quiz")
    if not quiz:
        return redirect(url_for("quiz.setup"))
    quiz["revealed"] = True
    session["quiz"] = quiz
    return redirect(url_for("quiz.quiz_session"))


@quiz_bp.post("/answer")
def answer():
    """Absenden der markierten Multiple-Choice-Optionen: deckt erst jetzt die Antwort auf."""
    quiz = session.get("quiz")
    if not quiz:
        return redirect(url_for("quiz.setup"))
    quiz["revealed"] = True
    quiz["selected_choice_ids"] = request.form.getlist("choice_ids", type=int)
    session["quiz"] = quiz
    return redirect(url_for("quiz.quiz_session"))


@quiz_bp.post("/rate")
def rate():
    db = get_db()
    quiz = session.get("quiz")
    if not quiz:
        return redirect(url_for("quiz.setup"))

    rating = request.form.get("rating", type=int)
    card_id = quiz["card_ids"][quiz["index"]]
    state = db.get_review_state(card_id)
    was_mastered = state.mastered
    new_state = srs.next_state(state, rating)
    db.save_review_state(new_state)

    if new_state.mastered and not was_mastered:
        quiz["newly_mastered"] += 1
    elif was_mastered and not new_state.mastered:
        quiz["dropped"] += 1

    quiz["index"] += 1
    quiz["revealed"] = False
    quiz["selected_choice_ids"] = []
    quiz["choice_order"] = None
    session["quiz"] = quiz

    if quiz["index"] >= len(quiz["card_ids"]):
        return redirect(url_for("quiz.finish"))
    return redirect(url_for("quiz.quiz_session"))


@quiz_bp.post("/end")
def end_early():
    return redirect(url_for("quiz.finish", early="1"))


@quiz_bp.get("/finish")
def finish():
    quiz = session.pop("quiz", None)
    if not quiz:
        return redirect(url_for("cards.index"))

    early = request.args.get("early") == "1"
    return render_template(
        "quiz_finish.html", early=early, processed=quiz["index"], total=len(quiz["card_ids"]),
        newly_mastered=quiz["newly_mastered"], dropped=quiz["dropped"],
    )
