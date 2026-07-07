"""Abfrage-Modus: Themenauswahl (Setup) und Abfrage-Session."""
import random
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import List, Optional

from .. import srs
from ..database import Database
from ..models import Card
from .widgets import ImagePanel


class QuizSetupWindow(tk.Toplevel):
    def __init__(self, master, db: Database, base_dir: Path):
        super().__init__(master)
        self.db = db
        self.base_dir = base_dir
        self.title("Abfrage starten")
        self.geometry("340x420")

        tk.Label(self, text="Themen auswaehlen (keine Auswahl = alle):").pack(anchor=tk.W, padx=10, pady=(10, 0))

        self.topics = db.list_topics()
        self.topic_vars = {}
        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        for topic in self.topics:
            var = tk.BooleanVar(value=False)
            tk.Checkbutton(list_frame, text=topic.name, variable=var).pack(anchor=tk.W)
            self.topic_vars[topic.id] = var

        self.only_due_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self, text="Nur faellige Karten abfragen", variable=self.only_due_var).pack(
            anchor=tk.W, padx=10, pady=10
        )

        ttk.Button(self, text="Abfrage starten", command=self._start).pack(pady=10)

    def _start(self):
        selected_ids = [tid for tid, var in self.topic_vars.items() if var.get()]
        topic_ids = selected_ids or None
        cards = self.db.due_cards(topic_ids=topic_ids, only_due=self.only_due_var.get())
        if not cards:
            messagebox.showinfo("Keine Karten", "Es gibt aktuell keine faelligen Karten fuer diese Auswahl.", parent=self)
            return
        random.shuffle(cards)
        self.destroy()
        QuizSessionWindow(self.master, self.db, self.base_dir, cards)


class QuizSessionWindow(tk.Toplevel):
    def __init__(self, master, db: Database, base_dir: Path, cards: List[Card]):
        super().__init__(master)
        self.db = db
        self.base_dir = base_dir
        self.cards = cards
        self.index = 0
        self.mastered_count = 0
        self.title("Abfrage laeuft")
        self.geometry("560x560")

        self.progress_label = tk.Label(self, font=("Segoe UI", 10))
        self.progress_label.pack(pady=(10, 0))

        self.side_label = tk.Label(self, font=("Segoe UI", 11, "bold"))
        self.side_label.pack(pady=(5, 0))

        self.text_label = tk.Label(self, wraplength=500, justify=tk.LEFT, font=("Segoe UI", 12))
        self.text_label.pack(padx=10, pady=10)

        self.image_panel = ImagePanel(self)
        self.image_panel.pack(pady=5)

        self.reveal_button = ttk.Button(self, text="Antwort anzeigen", command=self._reveal_answer)
        self.reveal_button.pack(pady=10)

        self.rating_frame = tk.Frame(self)
        for rating in (srs.NEIN, srs.UNSICHER, srs.SICHER, srs.KOMPLETT_SICHER):
            ttk.Button(
                self.rating_frame, text=f"({rating}) {srs.RATING_LABELS[rating]}",
                command=lambda r=rating: self._rate(r),
            ).pack(side=tk.LEFT, padx=4)

        self._show_question()

    def _current_card(self) -> Optional[Card]:
        return self.cards[self.index] if self.index < len(self.cards) else None

    def _show_question(self):
        card = self._current_card()
        if card is None:
            self._finish()
            return
        self.progress_label.configure(text=f"Karte {self.index + 1} von {len(self.cards)}")
        self.side_label.configure(text="Frage")
        self.text_label.configure(text=card.question_text)
        self.image_panel.set_image_path(card.question_image_path)
        self.rating_frame.pack_forget()
        self.reveal_button.pack(pady=10)

    def _reveal_answer(self):
        card = self._current_card()
        self.side_label.configure(text="Antwort")
        self.text_label.configure(text=card.answer_text)
        self.image_panel.set_image_path(card.answer_image_path)
        self.reveal_button.pack_forget()
        self.rating_frame.pack(pady=10)

    def _rate(self, rating: int):
        card = self._current_card()
        state = self.db.get_review_state(card.id)
        new_state = srs.next_state(state, rating)
        self.db.save_review_state(new_state)
        if new_state.mastered:
            self.mastered_count += 1
        self.index += 1
        self._show_question()

    def _finish(self):
        messagebox.showinfo(
            "Abfrage beendet",
            f"Fertig! {len(self.cards)} Karte(n) abgefragt.\n"
            f"Davon neu als 'gelernt' markiert: {self.mastered_count}.",
            parent=self,
        )
        self.destroy()
