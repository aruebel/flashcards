# Karteikarten Lernsystem

Ein einfaches Karteikarten-Lernsystem mit Themen, Text- und Bildkarten sowie
einem Spaced-Repetition-Abfragemodus.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Starten

```bash
python main.py
```

Es oeffnet sich das Hauptfenster. Beim ersten Start ist die Kartenliste leer.

## Benutzung

1. **Themen verwalten** – Themen anlegen, umbenennen oder loeschen.
2. **Neue Karte** – Frage und Antwort als Text eingeben. Optional kann pro
   Seite (Frage/Antwort) ein Bild eingefuegt werden:
   - **Bild einfuegen (Strg+V)** liest ein Bild direkt aus der Zwischenablage
     (z. B. nach einem Screenshot mit `Win+Shift+S`).
   - **Bild laden...** waehlt eine Bilddatei von der Festplatte.
3. **Abfrage starten** – Themen auswaehlen (oder keine Auswahl = alle Themen)
   und optional nur faellige Karten abfragen lassen. Danach wird jede Karte
   nacheinander angezeigt: erst die Frage, nach Klick auf "Antwort anzeigen"
   die Antwort, gefolgt von der Bewertung.

## Bewertung nach dem Aufdecken der Antwort

| Taste | Bedeutung           | Wirkung |
|-------|---------------------|---------|
| 1     | Nein                | Karte gilt als nicht gewusst, wird sofort/kurzfristig wieder abgefragt. |
| 2     | Ja, unsicher        | Karte wird bald wieder abgefragt (1 Tag). |
| 3     | Ja, sicher          | Karte wird spaeter wieder abgefragt (3 Tage). |
| 4     | Ja, komplett sicher | Intervall verlaengert sich (7, 14, 21 Tage). Nach **3x in Folge** "komplett sicher" gilt die Karte als **gelernt** und wird nicht mehr abgefragt. |

Jede Bewertung unter 4 setzt die "komplett sicher"-Serie zurueck. Gelernte
Karten koennen im Hauptfenster ueber **Lernstatus zuruecksetzen** wieder in
die aktive Abfrage aufgenommen werden.

## Daten

Alle Daten (SQLite-Datenbank und eingefuegte Bilder) liegen lokal im Ordner
`data/` neben `main.py`.

## Backup / Umzug auf einen anderen Rechner

- **Exportieren...** speichert alle Themen, Karten (inkl. Bilder) und den
  kompletten Lernfortschritt (Box, Serie, faellig am, gelernt-Status) in
  einer einzelnen `.zip`-Datei.
- **Importieren...** liest eine solche `.zip`-Datei wieder ein. Dabei gibt es
  zwei Modi:
  - **Zusammenfuehren** – neue Themen/Karten werden ergaenzt, bereits
    vorhandene Karten (gleiche Frage+Antwort im selben Thema) werden
    uebersprungen und nicht doppelt angelegt.
  - **Ersetzen** – loescht vorher alle vorhandenen Themen und Karten und
    ersetzt sie komplett durch den Inhalt des Backups. Danach folgt eine
    Sicherheitsabfrage, da dies nicht rueckgaengig gemacht werden kann.

Um auf einen anderen Rechner umzuziehen: auf dem alten Rechner
**Exportieren...**, die `.zip`-Datei z. B. per USB-Stick oder Cloud-Speicher
uebertragen, auf dem neuen Rechner die App starten und **Importieren...**
(Modus "Ersetzen" bei einer leeren neuen Installation, sonst
"Zusammenfuehren").

## Tests

```bash
python -m pytest tests/ -v
```
