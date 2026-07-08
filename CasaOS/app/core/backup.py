"""Export/Import aller Themen, Karten und Lernfortschritte als .zip-Backup.

Format (data.json im Zip):
{
  "version": 1,
  "topics": ["Thema A", "Thema B"],
  "cards": [
    {"topic_name": "Thema A", "question_text": "...", "answer_text": "...",
     "question_image": "images/xyz.png" | null, "answer_image": "..." | null,
     "review_state": {"box": 0, "mastery_streak": 0, "mastered": false,
                       "due_date": "2026-01-01", "total_reviews": 0}}
  ]
}

Themen/Karten werden ueber den Themennamen bzw. Frage+Antwort-Text
referenziert (nicht ueber IDs), damit ein Backup auf einem anderen Rechner
mit einer eigenen, unabhaengigen ID-Vergabe importiert werden kann.
"""
import json
import uuid
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from . import images as image_store
from .database import Database
from .models import Card, ChoiceOption, PuzzlePair, ReviewState

FORMAT_VERSION = 3
SUPPORTED_FORMAT_VERSIONS = (1, 2, 3)
DATA_ENTRY = "data.json"
IMAGES_PREFIX = "images/"


@dataclass
class ImportResult:
    topics_added: int = 0
    cards_added: int = 0
    cards_skipped: int = 0


def export_to_zip(db: Database, zip_path: Path) -> None:
    topics = db.list_topics()
    topic_names_by_id = {t.id: t.name for t in topics}

    exported_cards = []
    images_to_write = {}

    for card in db.list_cards():
        state = db.get_review_state(card.id)
        exported_cards.append({
            "topic_name": topic_names_by_id[card.topic_id],
            "question_text": card.question_text,
            "answer_text": card.answer_text,
            "question_image": _register_image(card.question_image_path, images_to_write),
            "answer_image": _register_image(card.answer_image_path, images_to_write),
            "card_type": card.card_type,
            "choices": [{"text": c.text, "is_correct": c.is_correct} for c in db.choices_for_card(card.id)],
            "puzzle_pairs": [{"left_text": p.left_text, "right_text": p.right_text}
                              for p in db.puzzle_pairs_for_card(card.id)],
            "review_state": {
                "box": state.box,
                "mastery_streak": state.mastery_streak,
                "mastered": state.mastered,
                "due_date": state.due_date.isoformat(),
                "total_reviews": state.total_reviews,
            },
        })

    data = {
        "version": FORMAT_VERSION,
        "topics": [t.name for t in topics],
        "cards": exported_cards,
    }

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(DATA_ENTRY, json.dumps(data, ensure_ascii=False, indent=2))
        for entry_name, source_path in images_to_write.items():
            zf.write(source_path, entry_name)


def _register_image(path: Optional[str], registry: dict) -> Optional[str]:
    if not path or not Path(path).exists():
        return None
    entry_name = f"{IMAGES_PREFIX}{Path(path).name}"
    registry[entry_name] = path
    return entry_name


def import_from_zip(db: Database, base_dir: Path, zip_path: Path, mode: str = "merge") -> ImportResult:
    if mode not in ("merge", "replace"):
        raise ValueError(f"Unbekannter Import-Modus: {mode}")

    with zipfile.ZipFile(zip_path, "r") as zf:
        data = json.loads(zf.read(DATA_ENTRY).decode("utf-8"))
        if data.get("version") not in SUPPORTED_FORMAT_VERSIONS:
            raise ValueError(f"Nicht unterstuetzte Backup-Version: {data.get('version')!r}")

        if mode == "replace":
            _wipe_all(db)

        result = ImportResult()
        topic_ids_by_name = {t.name: t.id for t in db.list_topics()}
        for topic_name in data["topics"]:
            if topic_name not in topic_ids_by_name:
                new_topic = db.add_topic(topic_name)
                topic_ids_by_name[new_topic.name] = new_topic.id
                result.topics_added += 1

        existing_keys_by_topic = {}
        for card_data in data["cards"]:
            topic_id = topic_ids_by_name.get(card_data["topic_name"])
            if topic_id is None:
                new_topic = db.add_topic(card_data["topic_name"])
                topic_ids_by_name[new_topic.name] = new_topic.id
                topic_id = new_topic.id
                result.topics_added += 1

            key = (card_data["question_text"], card_data["answer_text"])
            if mode == "merge":
                if topic_id not in existing_keys_by_topic:
                    existing_keys_by_topic[topic_id] = {
                        (c.question_text, c.answer_text) for c in db.list_cards([topic_id])
                    }
                if key in existing_keys_by_topic[topic_id]:
                    result.cards_skipped += 1
                    continue
                existing_keys_by_topic[topic_id].add(key)

            _import_card(db, base_dir, zf, topic_id, card_data)
            result.cards_added += 1

    return result


def _import_card(db: Database, base_dir: Path, zf: zipfile.ZipFile, topic_id: int, card_data: dict) -> None:
    choices = [
        ChoiceOption(id=None, card_id=0, text=c["text"], is_correct=c["is_correct"], position=i)
        for i, c in enumerate(card_data.get("choices", []))
    ]
    puzzle_pairs = [
        PuzzlePair(id=None, card_id=0, left_text=p["left_text"], right_text=p["right_text"], position=i)
        for i, p in enumerate(card_data.get("puzzle_pairs", []))
    ]
    new_card = db.add_card(Card(
        id=None, topic_id=topic_id,
        question_text=card_data["question_text"],
        answer_text=card_data["answer_text"],
        question_image_path=_extract_image(zf, card_data.get("question_image"), base_dir),
        answer_image_path=_extract_image(zf, card_data.get("answer_image"), base_dir),
        card_type=card_data.get("card_type", "text"),
        choices=choices,
        puzzle_pairs=puzzle_pairs,
    ))
    rs = card_data["review_state"]
    db.save_review_state(ReviewState(
        card_id=new_card.id,
        box=rs["box"],
        mastery_streak=rs["mastery_streak"],
        mastered=rs["mastered"],
        due_date=date.fromisoformat(rs["due_date"]),
        total_reviews=rs["total_reviews"],
    ))


def _extract_image(zf: zipfile.ZipFile, entry_name: Optional[str], base_dir: Path) -> Optional[str]:
    if not entry_name:
        return None
    suffix = Path(entry_name).suffix or ".png"
    dest_dir = base_dir / "images"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{uuid.uuid4().hex}{suffix}"
    dest_path.write_bytes(zf.read(entry_name))
    return str(dest_path)


def _wipe_all(db: Database) -> None:
    for card in db.list_cards():
        image_store.delete_image(card.question_image_path)
        image_store.delete_image(card.answer_image_path)
    for topic in db.list_topics():
        db.delete_topic(topic.id)
