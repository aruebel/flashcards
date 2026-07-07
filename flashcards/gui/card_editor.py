"""Fenster zum Anlegen/Bearbeiten einer Karteikarte (Text + Bild je Seite)."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from .. import images as image_store
from ..database import Database
from ..models import Card, Topic
from .widgets import ImagePanel

IMAGE_FILETYPES = [("Bilder", "*.png *.jpg *.jpeg *.gif *.bmp")]


class CardSide(tk.LabelFrame):
    def __init__(self, master, title: str, base_dir: Path, initial_text: str = "", initial_image: Optional[str] = None):
        super().__init__(master, text=title, padx=8, pady=8)
        self.base_dir = base_dir
        self.image_path = initial_image

        self.text = tk.Text(self, height=6, width=48, wrap=tk.WORD)
        self.text.insert("1.0", initial_text)
        self.text.pack(fill=tk.BOTH, expand=True)

        self.image_panel = ImagePanel(self, bg="#e8e8e8", width=200, height=120)
        self.image_panel.pack(pady=6)
        self.image_panel.set_image_path(self.image_path)

        button_row = tk.Frame(self)
        button_row.pack(fill=tk.X)
        ttk.Button(button_row, text="Bild einfuegen (Strg+V)", command=self._paste_from_clipboard).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Bild laden...", command=self._load_from_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_row, text="Bild entfernen", command=self._remove_image).pack(side=tk.LEFT)

    def _paste_from_clipboard(self):
        img = image_store.grab_clipboard_image()
        if img is None:
            messagebox.showinfo("Kein Bild", "In der Zwischenablage wurde kein Bild gefunden.", parent=self)
            return
        self.image_path = image_store.save_image(img, self.base_dir)
        self.image_panel.set_image_path(self.image_path)

    def _load_from_file(self):
        path = filedialog.askopenfilename(title="Bild auswaehlen", filetypes=IMAGE_FILETYPES, parent=self)
        if not path:
            return
        self.image_path = image_store.import_image_file(path, self.base_dir)
        self.image_panel.set_image_path(self.image_path)

    def _remove_image(self):
        self.image_path = None
        self.image_panel.clear()

    def get_text(self) -> str:
        return self.text.get("1.0", tk.END).strip()

    def clear(self):
        self.text.delete("1.0", tk.END)
        self._remove_image()


class CardEditorWindow(tk.Toplevel):
    def __init__(self, master, db: Database, base_dir: Path, card: Optional[Card] = None,
                 default_topic_id: Optional[int] = None, on_saved=None):
        super().__init__(master)
        self.db = db
        self.base_dir = base_dir
        self.card = card
        self.on_saved = on_saved
        self.title("Karte bearbeiten" if card else "Neue Karte")
        self.geometry("600x700")
        self.minsize(480, 400)

        self.topics = db.list_topics()
        if not self.topics:
            messagebox.showwarning("Kein Thema", "Bitte zuerst ein Thema anlegen.", parent=self)
            self.destroy()
            return

        # Wichtig: Button-Leiste zuerst packen (side=BOTTOM), damit sie ihren
        # Platz reserviert, bevor die scrollbare Flaeche mit expand=True den
        # Rest beansprucht. In umgekehrter Reihenfolge wuerde die Leiste in
        # einen zu schmalen Rest-Bereich gequetscht.
        button_row = tk.Frame(self)
        button_row.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        ttk.Button(button_row, text="Speichern", command=self._save).pack(side=tk.RIGHT)
        close_text = "Abbrechen" if card else "Fertig"
        ttk.Button(button_row, text=close_text, command=self.destroy).pack(side=tk.RIGHT, padx=5)
        self.status_label = tk.Label(button_row, fg="#2e7d32")
        self.status_label.pack(side=tk.LEFT)

        scroll_area = self._build_scroll_area()

        topic_row = tk.Frame(scroll_area)
        topic_row.pack(fill=tk.X, padx=10, pady=(10, 0))
        tk.Label(topic_row, text="Thema:").pack(side=tk.LEFT)
        self.topic_var = tk.StringVar()
        self.topic_combo = ttk.Combobox(topic_row, textvariable=self.topic_var, state="readonly",
                                         values=[t.name for t in self.topics])
        self.topic_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self._select_initial_topic(default_topic_id)

        self.question_side = CardSide(
            scroll_area, "Frage", base_dir,
            initial_text=card.question_text if card else "",
            initial_image=card.question_image_path if card else None,
        )
        self.question_side.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.answer_side = CardSide(
            scroll_area, "Antwort", base_dir,
            initial_text=card.answer_text if card else "",
            initial_image=card.answer_image_path if card else None,
        )
        self.answer_side.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def _build_scroll_area(self) -> tk.Frame:
        """Legt Frage/Antwort in eine scrollbare Flaeche, damit auf kleinen
        Bildschirmen nichts (z.B. das Antwortfeld) außerhalb des Fensters
        landet."""
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        inner = tk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def on_inner_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)

        inner.bind("<Configure>", on_inner_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Nur waehrend der Mauszeiger ueber der Flaeche ist global binden,
        # sonst wuerde das Mausrad auch andere Fenster nach dem Schliessen
        # noch beeinflussen.
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        return inner

    def _select_initial_topic(self, default_topic_id: Optional[int]):
        topic_id = default_topic_id or (self.card.topic_id if self.card else None)
        for topic in self.topics:
            if topic.id == topic_id:
                self.topic_var.set(topic.name)
                return
        self.topic_var.set(self.topics[0].name)

    def _selected_topic(self) -> Topic:
        name = self.topic_var.get()
        return next(t for t in self.topics if t.name == name)

    def _save(self):
        question_text = self.question_side.get_text()
        answer_text = self.answer_side.get_text()
        if not question_text and not self.question_side.image_path:
            messagebox.showerror("Fehler", "Die Frage darf nicht leer sein.", parent=self)
            return
        if not answer_text and not self.answer_side.image_path:
            messagebox.showerror("Fehler", "Die Antwort darf nicht leer sein.", parent=self)
            return

        topic = self._selected_topic()
        if self.card:
            self.card.topic_id = topic.id
            self.card.question_text = question_text
            self.card.answer_text = answer_text
            self.card.question_image_path = self.question_side.image_path
            self.card.answer_image_path = self.answer_side.image_path
            self.db.update_card(self.card)

            if self.on_saved:
                self.on_saved()
            self.destroy()
            return

        new_card = Card(
            id=None, topic_id=topic.id,
            question_text=question_text, answer_text=answer_text,
            question_image_path=self.question_side.image_path,
            answer_image_path=self.answer_side.image_path,
        )
        self.db.add_card(new_card)

        if self.on_saved:
            self.on_saved()

        # Beim Anlegen neuer Karten Fenster offen lassen: Frage/Antwort
        # leeren fuer die naechste Karte, das gewaehlte Thema bleibt stehen.
        self.question_side.clear()
        self.answer_side.clear()
        self.question_side.text.focus_set()
        self._show_saved_feedback()

    def _show_saved_feedback(self):
        self.status_label.configure(text="Gespeichert.")
        self.after(1500, self._clear_saved_feedback)

    def _clear_saved_feedback(self):
        if self.winfo_exists():
            self.status_label.configure(text="")
