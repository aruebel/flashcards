"""Fenster zur Verwaltung von Themen (anlegen, umbenennen, loeschen)."""
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from ..database import Database


class TopicManagerWindow(tk.Toplevel):
    def __init__(self, master, db: Database, on_change=None):
        super().__init__(master)
        self.title("Themen verwalten")
        self.geometry("360x420")
        self.db = db
        self.on_change = on_change

        self.listbox = tk.Listbox(self, selectmode=tk.SINGLE)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        button_row = tk.Frame(self)
        button_row.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(button_row, text="Neu", command=self._add_topic).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Umbenennen", command=self._rename_topic).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_row, text="Loeschen", command=self._delete_topic).pack(side=tk.LEFT)

        self._topics = []
        self._reload()

    def _reload(self):
        self._topics = self.db.list_topics()
        self.listbox.delete(0, tk.END)
        for topic in self._topics:
            self.listbox.insert(tk.END, topic.name)

    def _selected_topic(self):
        selection = self.listbox.curselection()
        if not selection:
            return None
        return self._topics[selection[0]]

    def _add_topic(self):
        name = simpledialog.askstring("Neues Thema", "Name des Themas:", parent=self)
        if not name:
            return
        try:
            self.db.add_topic(name)
        except ValueError as exc:
            messagebox.showerror("Fehler", str(exc), parent=self)
            return
        self._reload()
        if self.on_change:
            self.on_change()

    def _rename_topic(self):
        topic = self._selected_topic()
        if not topic:
            return
        new_name = simpledialog.askstring("Thema umbenennen", "Neuer Name:", initialvalue=topic.name, parent=self)
        if not new_name:
            return
        try:
            self.db.rename_topic(topic.id, new_name)
        except ValueError as exc:
            messagebox.showerror("Fehler", str(exc), parent=self)
            return
        self._reload()
        if self.on_change:
            self.on_change()

    def _delete_topic(self):
        topic = self._selected_topic()
        if not topic:
            return
        if not messagebox.askyesno(
            "Thema loeschen",
            f"Thema '{topic.name}' und alle zugehoerigen Karten wirklich loeschen?",
            parent=self,
        ):
            return
        self.db.delete_topic(topic.id)
        self._reload()
        if self.on_change:
            self.on_change()
