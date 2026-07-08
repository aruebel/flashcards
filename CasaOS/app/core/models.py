"""Datenmodelle fuer Themen, Karteikarten und Lernstatus."""
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class Topic:
    id: Optional[int]
    name: str


@dataclass
class ChoiceOption:
    id: Optional[int]
    card_id: int
    text: str
    is_correct: bool
    position: int = 0


@dataclass
class PuzzlePair:
    id: Optional[int]
    card_id: int
    left_text: str
    right_text: str
    position: int = 0


@dataclass
class Card:
    id: Optional[int]
    topic_id: int
    question_text: str
    answer_text: str
    question_image_path: Optional[str] = None
    answer_image_path: Optional[str] = None
    card_type: str = "text"
    choices: List[ChoiceOption] = field(default_factory=list)
    puzzle_pairs: List[PuzzlePair] = field(default_factory=list)


@dataclass
class ReviewState:
    card_id: int
    box: int = 0
    mastery_streak: int = 0
    mastered: bool = False
    due_date: date = None
    total_reviews: int = 0
