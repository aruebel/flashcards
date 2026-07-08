"""SQLite-Speicher fuer Themen, Karten und Lernstatus (Repository Pattern)."""
import sqlite3
from datetime import date
from pathlib import Path
from typing import List, Optional

from .models import Card, ChoiceOption, ReviewState, Topic
from .srs import initial_state

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL DEFAULT '',
    answer_text TEXT NOT NULL DEFAULT '',
    question_image_path TEXT,
    answer_image_path TEXT
);

CREATE TABLE IF NOT EXISTS review_state (
    card_id INTEGER PRIMARY KEY REFERENCES cards(id) ON DELETE CASCADE,
    box INTEGER NOT NULL DEFAULT 0,
    mastery_streak INTEGER NOT NULL DEFAULT 0,
    mastered INTEGER NOT NULL DEFAULT 0,
    due_date TEXT NOT NULL,
    total_reviews INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS card_choices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    is_correct INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL DEFAULT 0
);
"""


class Database:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self):
        """Fuegt Spalten hinzu, die in bereits bestehenden Datenbanken noch fehlen."""
        columns = {row[1] for row in self._conn.execute("PRAGMA table_info(cards)")}
        if "card_type" not in columns:
            self._conn.execute("ALTER TABLE cards ADD COLUMN card_type TEXT NOT NULL DEFAULT 'text'")

    def close(self):
        self._conn.close()

    # --- Topics -----------------------------------------------------

    def add_topic(self, name: str) -> Topic:
        name = name.strip()
        if not name:
            raise ValueError("Themenname darf nicht leer sein.")
        cur = self._conn.execute("INSERT INTO topics (name) VALUES (?)", (name,))
        self._conn.commit()
        return Topic(id=cur.lastrowid, name=name)

    def rename_topic(self, topic_id: int, new_name: str):
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Themenname darf nicht leer sein.")
        self._conn.execute("UPDATE topics SET name = ? WHERE id = ?", (new_name, topic_id))
        self._conn.commit()

    def delete_topic(self, topic_id: int):
        self._conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        self._conn.commit()

    def list_topics(self) -> List[Topic]:
        rows = self._conn.execute("SELECT id, name FROM topics ORDER BY name").fetchall()
        return [Topic(id=r[0], name=r[1]) for r in rows]

    # --- Cards --------------------------------------------------------

    def add_card(self, card: Card) -> Card:
        cur = self._conn.execute(
            "INSERT INTO cards (topic_id, question_text, answer_text, question_image_path, answer_image_path, card_type) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (card.topic_id, card.question_text, card.answer_text, card.question_image_path,
             card.answer_image_path, card.card_type),
        )
        card.id = cur.lastrowid
        self._replace_choices(card.id, card.choices)
        card.choices = self.choices_for_card(card.id)
        state = initial_state(card.id)
        self._insert_review_state(state)
        self._conn.commit()
        return card

    def update_card(self, card: Card):
        self._conn.execute(
            "UPDATE cards SET topic_id=?, question_text=?, answer_text=?, "
            "question_image_path=?, answer_image_path=?, card_type=? WHERE id=?",
            (card.topic_id, card.question_text, card.answer_text,
             card.question_image_path, card.answer_image_path, card.card_type, card.id),
        )
        self._replace_choices(card.id, card.choices)
        card.choices = self.choices_for_card(card.id)
        self._conn.commit()

    # --- Antwortmoeglichkeiten (Multiple Choice) -----------------------

    def _replace_choices(self, card_id: int, choices: List[ChoiceOption]):
        self._conn.execute("DELETE FROM card_choices WHERE card_id = ?", (card_id,))
        for position, choice in enumerate(choices):
            self._conn.execute(
                "INSERT INTO card_choices (card_id, text, is_correct, position) VALUES (?, ?, ?, ?)",
                (card_id, choice.text, int(choice.is_correct), position),
            )

    def choices_for_card(self, card_id: int) -> List[ChoiceOption]:
        rows = self._conn.execute(
            "SELECT id, card_id, text, is_correct, position FROM card_choices "
            "WHERE card_id = ? ORDER BY position", (card_id,)
        ).fetchall()
        return [ChoiceOption(id=r[0], card_id=r[1], text=r[2], is_correct=bool(r[3]), position=r[4])
                for r in rows]

    def delete_card(self, card_id: int):
        self._conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        self._conn.commit()

    def get_card(self, card_id: int) -> Optional[Card]:
        row = self._conn.execute(
            "SELECT id, topic_id, question_text, answer_text, question_image_path, answer_image_path, card_type "
            "FROM cards WHERE id = ?", (card_id,)
        ).fetchone()
        if row is None:
            return None
        card = self._row_to_card(row)
        card.choices = self.choices_for_card(card.id)
        return card

    def list_cards(self, topic_ids: Optional[List[int]] = None) -> List[Card]:
        if topic_ids:
            placeholders = ",".join("?" * len(topic_ids))
            rows = self._conn.execute(
                f"SELECT id, topic_id, question_text, answer_text, question_image_path, answer_image_path, card_type "
                f"FROM cards WHERE topic_id IN ({placeholders})", topic_ids
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT id, topic_id, question_text, answer_text, question_image_path, answer_image_path, card_type "
                "FROM cards"
            ).fetchall()
        return [self._row_to_card(r) for r in rows]

    @staticmethod
    def _row_to_card(row) -> Card:
        return Card(id=row[0], topic_id=row[1], question_text=row[2], answer_text=row[3],
                     question_image_path=row[4], answer_image_path=row[5], card_type=row[6])

    # --- Review state -------------------------------------------------

    def _insert_review_state(self, state: ReviewState):
        self._conn.execute(
            "INSERT INTO review_state (card_id, box, mastery_streak, mastered, due_date, total_reviews) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (state.card_id, state.box, state.mastery_streak, int(state.mastered),
             state.due_date.isoformat(), state.total_reviews),
        )

    def get_review_state(self, card_id: int) -> Optional[ReviewState]:
        row = self._conn.execute(
            "SELECT card_id, box, mastery_streak, mastered, due_date, total_reviews "
            "FROM review_state WHERE card_id = ?", (card_id,)
        ).fetchone()
        return self._row_to_state(row) if row else None

    def save_review_state(self, state: ReviewState):
        self._conn.execute(
            "UPDATE review_state SET box=?, mastery_streak=?, mastered=?, due_date=?, total_reviews=? "
            "WHERE card_id=?",
            (state.box, state.mastery_streak, int(state.mastered),
             state.due_date.isoformat(), state.total_reviews, state.card_id),
        )
        self._conn.commit()

    def reset_review_state(self, card_id: int):
        self.save_review_state(initial_state(card_id))

    def due_cards(self, topic_ids: Optional[List[int]] = None, only_due: bool = True) -> List[Card]:
        cards = self.list_cards(topic_ids)
        result = []
        today = date.today()
        for card in cards:
            state = self.get_review_state(card.id)
            if state.mastered:
                continue
            if only_due and state.due_date > today:
                continue
            result.append(card)
        return result

    def mastered_cards(self, topic_ids: Optional[List[int]] = None) -> List[Card]:
        return [card for card in self.list_cards(topic_ids) if self.get_review_state(card.id).mastered]

    @staticmethod
    def _row_to_state(row) -> ReviewState:
        return ReviewState(card_id=row[0], box=row[1], mastery_streak=row[2], mastered=bool(row[3]),
                            due_date=date.fromisoformat(row[4]), total_reviews=row[5])
