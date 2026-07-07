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

COUNT_CHOICES = ["10", "20", "30"]


class QuizSetupWindow(tk.Toplevel):
    def __init__(self, master, db: Database, base_dir: Path, review_mastered: bool = False):
        super().__init__(master)
        self.db = db
        self.base_dir = base_dir
        self.review_mastered = review_mastered
        self.all_label = "Alle gelernten" if review_mastered else "Alle faelligen"
        self.title("Gelernte Karten wiederholen" if review_mastered else "Abfrage starten")
        self.geometry("340x480")

        tk.Label(self, text="Themen auswaehlen (keine Auswahl = alle):").pack(anchor=tk.W, padx=10, pady=(10, 0))

        self.topics = db.list_topics()
        self.topic_vars = {}
        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        for topic in self.topics:
            var = tk.BooleanVar(value=False)
            tk.Checkbutton(list_frame, text=topic.name, variable=var).pack(anchor=tk.W)
            self.topic_vars[topic.id] = var

        if review_mastered:
            tk.Label(
                self, wraplength=300, justify=tk.LEFT,
                text="Fragt gezielt Karten ab, die bereits als 'gelernt' gelten und sonst "
                     "nicht mehr in der normalen Abfrage vorkommen. Karten, die dabei nicht "
                     "mehr sicher gewusst werden, kommen automatisch wieder in die normale "
                     "Abfrage zurueck.",
            ).pack(anchor=tk.W, padx=10, pady=10)
        else:
            self.only_due_var = tk.BooleanVar(value=True)
            tk.Checkbutton(self, text="Nur faellige Karten abfragen", variable=self.only_due_var).pack(
                anchor=tk.W, padx=10, pady=10
            )

        tk.Label(self, text="Anzahl Karten:").pack(anchor=tk.W, padx=10)
        self.count_var = tk.StringVar(value=self.all_label)
        count_row = tk.Frame(self)
        count_row.pack(anchor=tk.W, padx=10, pady=(0, 10))
        for choice in COUNT_CHOICES + [self.all_label]:
            tk.Radiobutton(count_row, text=choice, variable=self.count_var, value=choice).pack(side=tk.LEFT)

        button_text = "Wiederholung starten" if review_mastered else "Abfrage starten"
        ttk.Button(self, text=button_text, command=self._start).pack(pady=10)

    def _start(self):
        selected_ids = [tid for tid, var in self.topic_vars.items() if var.get()]
        topic_ids = selected_ids or None
        if self.review_mastered:
            cards = self.db.mastered_cards(topic_ids=topic_ids)
            empty_message = "Es gibt aktuell keine gelernten Karten fuer diese Auswahl."
        else:
            cards = self.db.due_cards(topic_ids=topic_ids, only_due=self.only_due_var.get())
            empty_message = "Es gibt aktuell keine faelligen Karten fuer diese Auswahl."
        if not cards:
            messagebox.showinfo("Keine Karten", empty_message, parent=self)
            return

        random.shuffle(cards)

        requested = self.count_var.get()
        if requested != self.all_label:
            limit = int(requested)
            if len(cards) > limit:
                cards = cards[:limit]
            else:
                messagebox.showinfo(
                    "Weniger Karten verfuegbar",
                    f"Angefragt waren {limit} Karten, aktuell sind aber nur {len(cards)} verfuegbar. "
                    f"Es werden nur diese {len(cards)} abgefragt.",
                    parent=self,
                )

        self.destroy()
        QuizSessionWindow(self.master, self.db, self.base_dir, cards)


class QuizSessionWindow(tk.Toplevel):
    def __init__(self, master, db: Database, base_dir: Path, cards: List[Card]):
        super().__init__(master)
        self.db = db
        self.base_dir = base_dir
        self.cards = cards
        self.index = 0
        self.newly_mastered_count = 0
        self.dropped_from_mastery_count = 0
        self.title("Abfrage laeuft")
        self.geometry("560x560")

        top_bar = tk.Frame(self)
        top_bar.pack(fill=tk.X, padx=10, pady=(10, 0))
        self.progress_label = tk.Label(top_bar, font=("Segoe UI", 10))
        self.progress_label.pack(side=tk.LEFT)
        ttk.Button(top_bar, text="Abfrage beenden", command=self._end_early).pack(side=tk.RIGHT)

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
        was_mastered = state.mastered
        new_state = srs.next_state(state, rating)
        self.db.save_review_state(new_state)
        if new_state.mastered and not was_mastered:
            self.newly_mastered_count += 1
        elif was_mastered and not new_state.mastered:
            self.dropped_from_mastery_count += 1
        self.index += 1
        self._show_question()

    def _end_early(self):
        remaining = len(self.cards) - self.index
        if remaining > 0 and not messagebox.askyesno(
            "Abfrage beenden?",
            f"Es sind noch {remaining} Karte(n) uebrig. Abfrage wirklich beenden?\n"
            f"Der bisherige Fortschritt bleibt gespeichert.",
            parent=self,
        ):
            return
        self._finish(early=True)

    def _finish(self, early: bool = False):
        processed = self.index
        if early:
            header = (
                f"Abfrage vorzeitig beendet. {processed} von {len(self.cards)} Karte(n) abgefragt, "
                f"der Fortschritt wurde gespeichert."
            )
        else:
            header = f"Fertig! {processed} Karte(n) abgefragt."

        message = f"{header}\nDavon neu als 'gelernt' markiert: {self.newly_mastered_count}."
        if self.dropped_from_mastery_count:
            message += (
                f"\nWieder in die normale Abfrage zurueckgeholt (nicht mehr sicher gewusst): "
                f"{self.dropped_from_mastery_count}."
            )
        messagebox.showinfo("Abfrage beendet", message, parent=self)
        self.destroy()
