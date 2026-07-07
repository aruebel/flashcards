"""Dialog zur Auswahl des Import-Modus (Zusammenfuehren/Ersetzen)."""
import tkinter as tk
from tkinter import ttk
from typing import Optional

MERGE = "merge"
REPLACE = "replace"


def ask_import_mode(master) -> Optional[str]:
    """Zeigt einen modalen Dialog und liefert 'merge', 'replace' oder None (Abbruch)."""
    dialog = tk.Toplevel(master)
    dialog.title("Import-Modus waehlen")
    dialog.geometry("400x220")
    dialog.transient(master)
    dialog.grab_set()
    dialog.resizable(False, False)

    tk.Label(
        dialog, text="Wie sollen die Daten aus dem Backup importiert werden?",
        wraplength=360, justify=tk.LEFT, font=("Segoe UI", 10, "bold"),
    ).pack(anchor=tk.W, padx=12, pady=(12, 8))

    mode_var = tk.StringVar(value=MERGE)
    tk.Radiobutton(
        dialog, variable=mode_var, value=MERGE, justify=tk.LEFT, wraplength=360,
        text="Zusammenfuehren\nNeue Themen/Karten hinzufuegen, bereits vorhandene Karten "
             "(gleiche Frage+Antwort) werden uebersprungen.",
    ).pack(anchor=tk.W, padx=12, pady=4)
    tk.Radiobutton(
        dialog, variable=mode_var, value=REPLACE, justify=tk.LEFT, wraplength=360,
        text="Ersetzen\nAlle vorhandenen Themen und Karten werden vorher geloescht "
             "und komplett durch den Inhalt des Backups ersetzt.",
    ).pack(anchor=tk.W, padx=12, pady=4)

    result = {"mode": None}

    def confirm():
        result["mode"] = mode_var.get()
        dialog.destroy()

    def cancel():
        result["mode"] = None
        dialog.destroy()

    button_row = tk.Frame(dialog)
    button_row.pack(side=tk.BOTTOM, pady=12)
    ttk.Button(button_row, text="Weiter", command=confirm).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_row, text="Abbrechen", command=cancel).pack(side=tk.LEFT)

    dialog.protocol("WM_DELETE_WINDOW", cancel)
    dialog.wait_window()
    return result["mode"]
