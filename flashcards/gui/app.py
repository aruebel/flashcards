"""Hauptfenster der Karteikarten-App."""
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import backup
from ..database import Database
from .backup_dialog import REPLACE, ask_import_mode
from .card_editor import CardEditorWindow
from .quiz_view import QuizSetupWindow
from .topic_manager import TopicManagerWindow

ALL_TOPICS_LABEL = "Alle Themen"


class FlashcardApp(tk.Tk):
    def __init__(self, db: Database, base_dir: Path):
        super().__init__()
        self.db = db
        self.base_dir = base_dir
        self.title("Karteikarten Lernsystem")
        self.geometry("720x520")

        self._build_toolbar()
        self._build_card_list()
        self._reload_topics()
        self._reload_cards()

    def _build_toolbar(self):
        bar = tk.Frame(self)
        bar.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(bar, text="Themen verwalten", command=self._open_topic_manager).pack(side=tk.LEFT)
        ttk.Button(bar, text="Neue Karte", command=self._open_new_card).pack(side=tk.LEFT, padx=5)
        ttk.Button(bar, text="Abfrage starten", command=self._open_quiz_setup).pack(side=tk.LEFT)
        ttk.Button(bar, text="Exportieren...", command=self._export_backup).pack(side=tk.LEFT, padx=(20, 5))
        ttk.Button(bar, text="Importieren...", command=self._import_backup).pack(side=tk.LEFT)

        tk.Label(bar, text="Filter:").pack(side=tk.LEFT, padx=(20, 5))
        self.filter_var = tk.StringVar(value=ALL_TOPICS_LABEL)
        self.filter_combo = ttk.Combobox(bar, textvariable=self.filter_var, state="readonly")
        self.filter_combo.pack(side=tk.LEFT)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self._reload_cards())

    def _build_card_list(self):
        columns = ("topic", "question", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        self.tree.heading("topic", text="Thema")
        self.tree.heading("question", text="Frage")
        self.tree.heading("status", text="Status")
        self.tree.column("topic", width=140)
        self.tree.column("question", width=380)
        self.tree.column("status", width=140)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10)
        self.tree.bind("<Double-1>", lambda e: self._edit_selected())

        button_row = tk.Frame(self)
        button_row.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(button_row, text="Bearbeiten", command=self._edit_selected).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Loeschen", command=self._delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_row, text="Lernstatus zuruecksetzen", command=self._reset_selected).pack(side=tk.LEFT)

    def _reload_topics(self):
        names = [ALL_TOPICS_LABEL] + [t.name for t in self.db.list_topics()]
        self.filter_combo.configure(values=names)
        if self.filter_var.get() not in names:
            self.filter_var.set(ALL_TOPICS_LABEL)

    def _current_topic_filter(self):
        name = self.filter_var.get()
        if name == ALL_TOPICS_LABEL:
            return None
        return next((t for t in self.db.list_topics() if t.name == name), None)

    def _reload_cards(self):
        self.tree.delete(*self.tree.get_children())
        topic = self._current_topic_filter()
        topic_ids = [topic.id] if topic else None
        topics_by_id = {t.id: t.name for t in self.db.list_topics()}
        for card in self.db.list_cards(topic_ids):
            state = self.db.get_review_state(card.id)
            status = "Gelernt" if state.mastered else f"Box {state.box}, faellig {state.due_date.isoformat()}"
            preview = card.question_text[:60] or "(nur Bild)"
            self.tree.insert("", tk.END, iid=str(card.id), values=(topics_by_id.get(card.topic_id, "?"), preview, status))

    def _selected_card_id(self):
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    def _open_topic_manager(self):
        TopicManagerWindow(self, self.db, on_change=self._on_topics_changed)

    def _on_topics_changed(self):
        self._reload_topics()
        self._reload_cards()

    def _open_new_card(self):
        topic = self._current_topic_filter()
        CardEditorWindow(self, self.db, self.base_dir, default_topic_id=topic.id if topic else None,
                          on_saved=self._reload_cards)

    def _edit_selected(self):
        card_id = self._selected_card_id()
        if card_id is None:
            return
        card = self.db.get_card(card_id)
        CardEditorWindow(self, self.db, self.base_dir, card=card, on_saved=self._reload_cards)

    def _delete_selected(self):
        card_id = self._selected_card_id()
        if card_id is None:
            return
        if messagebox.askyesno("Karte loeschen", "Diese Karte wirklich loeschen?", parent=self):
            self.db.delete_card(card_id)
            self._reload_cards()

    def _reset_selected(self):
        card_id = self._selected_card_id()
        if card_id is None:
            return
        self.db.reset_review_state(card_id)
        self._reload_cards()

    def _open_quiz_setup(self):
        QuizSetupWindow(self, self.db, self.base_dir)

    def _export_backup(self):
        path = filedialog.asksaveasfilename(
            title="Backup exportieren",
            defaultextension=".zip",
            filetypes=[("ZIP-Archiv", "*.zip")],
            initialfile=f"karteikarten_backup_{date.today().isoformat()}.zip",
            parent=self,
        )
        if not path:
            return
        try:
            backup.export_to_zip(self.db, Path(path))
        except OSError as exc:
            messagebox.showerror("Export fehlgeschlagen", str(exc), parent=self)
            return
        messagebox.showinfo("Export abgeschlossen", f"Backup gespeichert unter:\n{path}", parent=self)

    def _import_backup(self):
        path = filedialog.askopenfilename(
            title="Backup importieren", filetypes=[("ZIP-Archiv", "*.zip")], parent=self
        )
        if not path:
            return
        mode = ask_import_mode(self)
        if mode is None:
            return
        if mode == REPLACE:
            if not messagebox.askyesno(
                "Daten ersetzen?",
                "Alle vorhandenen Themen und Karten werden geloescht und durch den Inhalt "
                "des Backups ersetzt. Fortfahren?",
                parent=self,
            ):
                return
        try:
            result = backup.import_from_zip(self.db, self.base_dir, Path(path), mode=mode)
        except (OSError, ValueError, KeyError) as exc:
            messagebox.showerror("Import fehlgeschlagen", str(exc), parent=self)
            return
        self._on_topics_changed()
        messagebox.showinfo(
            "Import abgeschlossen",
            f"Neue Themen: {result.topics_added}\n"
            f"Neue Karten: {result.cards_added}\n"
            f"Uebersprungen (bereits vorhanden): {result.cards_skipped}",
            parent=self,
        )
