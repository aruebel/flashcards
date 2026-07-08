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
        "typed_answer": "",
        "typed_correct": None,
        "puzzle_order": None,
        "puzzle_selected": {},
        "puzzle_row_correct": {},
        "puzzle_correct": None,
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

    puzzle_right_options = []

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

    elif card.card_type == "puzzle":
        # Die Teil-B-Pool-Reihenfolge wird einmal pro Karte gewuerfelt; jede
        # Zeile bekommt denselben vollstaendigen Pool (Teile verschwinden beim
        # Zuordnen nicht, das macht die Zuordnung schwieriger). Gleichlautende
        # Teil-B-Texte (Gross-/Kleinschreibung egal) werden dabei zu einer
        # einzigen Auswahloption zusammengefasst.
        order = quiz.get("puzzle_order")
        if not order:
            seen = set()
            unique_texts = []
            for pair in card.puzzle_pairs:
                key = pair.right_text.casefold()
                if key not in seen:
                    seen.add(key)
                    unique_texts.append(pair.right_text)
            random.shuffle(unique_texts)
            quiz["puzzle_order"] = unique_texts
            session["quiz"] = quiz
        puzzle_right_options = quiz["puzzle_order"]

    return render_template(
        "quiz_session.html", card=card, revealed=quiz["revealed"],
        selected_choice_ids=quiz.get("selected_choice_ids", []),
        typed_answer=quiz.get("typed_answer", ""),
        typed_correct=quiz.get("typed_correct"),
        puzzle_right_options=puzzle_right_options,
        puzzle_selected=quiz.get("puzzle_selected", {}),
        puzzle_row_correct=quiz.get("puzzle_row_correct", {}),
        puzzle_correct=quiz.get("puzzle_correct"),
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


@quiz_bp.post("/submit-typed")
def submit_typed():
    """Absenden der eingetippten Antwort: vergleicht sie exakt (nach Trimmen) mit der vorgegebenen Antwort."""
    db = get_db()
    quiz = session.get("quiz")
    if not quiz:
        return redirect(url_for("quiz.setup"))

    card = db.get_card(quiz["card_ids"][quiz["index"]])
    typed_answer = request.form.get("typed_answer", "")
    quiz["revealed"] = True
    quiz["typed_answer"] = typed_answer
    quiz["typed_correct"] = typed_answer.strip() == (card.answer_text or "").strip()
    session["quiz"] = quiz
    return redirect(url_for("quiz.quiz_session"))


@quiz_bp.post("/submit-puzzle")
def submit_puzzle():
    """Absenden der Puzzle-Zuordnung: deckt erst jetzt auf, welche Zuordnungen stimmen."""
    db = get_db()
    quiz = session.get("quiz")
    if not quiz:
        return redirect(url_for("quiz.setup"))

    card = db.get_card(quiz["card_ids"][quiz["index"]])
    selected = {}
    row_correct = {}
    all_correct = True
    for pair in card.puzzle_pairs:
        chosen_text = request.form.get(f"puzzle_answer_{pair.id}", "").strip()
        is_correct = bool(chosen_text) and chosen_text.casefold() == pair.right_text.casefold()
        # Session-Werte werden als JSON serialisiert, Dict-Keys muessen daher Strings sein.
        selected[str(pair.id)] = chosen_text
        row_correct[str(pair.id)] = is_correct
        if not is_correct:
            all_correct = False

    quiz["revealed"] = True
    quiz["puzzle_selected"] = selected
    quiz["puzzle_row_correct"] = row_correct
    quiz["puzzle_correct"] = all_correct
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
    quiz["typed_answer"] = ""
    quiz["typed_correct"] = None
    quiz["puzzle_order"] = None
    quiz["puzzle_selected"] = {}
    quiz["puzzle_row_correct"] = {}
    quiz["puzzle_correct"] = None
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
