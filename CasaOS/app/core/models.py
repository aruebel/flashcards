"""Datenmodelle fuer Themen, Karteikarten und Lernstatus."""
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Topic:
    id: Optional[int]
    name: str


@dataclass
class Card:
    id: Optional[int]
    topic_id: int
    question_text: str
    answer_text: str
    question_image_path: Optional[str] = None
    answer_image_path: Optional[str] = None


@dataclass
class ReviewState:
    card_id: int
    box: int = 0
    mastery_streak: int = 0
    mastered: bool = False
    due_date: date = None
    total_reviews: int = 0
