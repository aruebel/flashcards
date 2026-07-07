# Karteikarten Lernsystem – CasaOS / Web-Version

Diese Variante bietet exakt die gleichen Funktionen wie die Desktop-App im
Hauptordner, aber als Webanwendung (Flask), die du als Docker-Container auf
deinem CasaOS-Server installierst und im Browser benutzt.

## Funktionsumfang (identisch zur Desktop-App)

- Themen anlegen/umbenennen/loeschen
- Karten mit Text und Bildern je Frage/Antwort-Seite
  - Bild einfuegen per Copy-&-Paste (Strg+V, z. B. nach einem Screenshot)
  - oder per Datei-Upload
  - Klick auf ein Bild zeigt es in voller Groesse (Lightbox)
- Neue Karte anlegen: Speichern leert das Formular fuer die naechste Karte,
  das Thema bleibt ausgewaehlt ("Fertig" beendet die Eingabe)
- Abfrage: Themen auswaehlen (oder alle), Anzahl der Karten (10/20/30/alle
  faelligen), "nur faellige Karten"-Option; Hinweis, falls weniger Karten
  faellig sind als angefragt
- Bewertung nach dem Aufdecken der Antwort (1 Nein / 2 unsicher / 3 sicher /
  4 komplett sicher) mit Spaced-Repetition-Logik: nach 3x "komplett sicher"
  in Folge gilt eine Karte als gelernt
- "Abfrage beenden"-Button: Fortschritt bereits bewerteter Karten bleibt
  gespeichert
- "Gelernte Karten wiederholen": gezielt bereits gelernte Karten erneut
  abfragen; faellt eine davon aus "komplett sicher" heraus, kommt sie
  automatisch zurueck in die normale Abfrage
- Export/Import als `.zip`-Backup (Zusammenfuehren oder Ersetzen)

## Architektur

```
CasaOS/
├── app/
│   ├── core/          # Reine Logik (Modelle, SRS-Algorithmus, DB, Backup) –
│   │                   inhaltlich identisch zur Desktop-App, ohne UI-Bezug
│   ├── routes/         # Flask-Blueprints (topics, cards, quiz, backup)
│   ├── templates/       # Jinja2-Templates (serverseitig gerendert)
│   └── static/          # CSS + JavaScript (Clipboard-Paste, Lightbox)
├── wsgi.py              # Einstiegspunkt fuer gunicorn/Flask
├── Dockerfile
├── docker-compose.yml
├── requirements.txt / requirements-dev.txt
└── tests/               # pytest-Suite (Flask-Test-Client)
```

Die Kernlogik (`app/core/`) ist eine unveraenderte Kopie der Desktop-Module
(`models.py`, `srs.py`, `database.py`, `backup.py`) – nur `images.py` wurde
angepasst, da die Web-Variante Bilder per Browser-Upload statt per
`PIL.ImageGrab` von der Windows-Zwischenablage bekommt.

## Daten

Alle Daten (SQLite-Datenbank `flashcards.db` + `images/`) liegen unter dem
Pfad, den die Umgebungsvariable `DATA_DIR` angibt (im Container: `/data`).
Das Compose-File mountet dafuer `/DATA/AppData/flashcards` auf dem CasaOS-
Host nach `/data` im Container – deine Karten und dein Lernfortschritt
ueberleben damit Container-Updates/-Neustarts.

## Installation auf CasaOS

### Empfohlen: Direkt auf dem CasaOS-Server bauen (per SSH)

CasaOS basiert auf Docker + Docker Compose; per SSH hast du vollen Zugriff
darauf, auch ohne die eigentliche App-Store-UI zu benutzen. Der Container
taucht danach trotzdem ganz normal im CasaOS-Dashboard auf.

```bash
# Auf deinem PC: CasaOS-Ordner auf den Server kopieren, z. B.
scp -r CasaOS/ user@casaos-server:/DATA/AppData/flashcards-src

# Auf dem CasaOS-Server per SSH:
cd /DATA/AppData/flashcards-src
docker compose up -d --build
```

Danach ist die App unter `http://<casaos-ip>:8099` erreichbar. Port und
Datenverzeichnis lassen sich in `docker-compose.yml` anpassen (`ports:` bzw.
`volumes:`).

### Alternative: Eigenes Image bauen und ueber die CasaOS-Oberflaeche installieren

1. Image lokal bauen und in eine Registry pushen (z. B. Docker Hub):
   ```bash
   docker build -t <dein-dockerhub-name>/flashcards:latest .
   docker push <dein-dockerhub-name>/flashcards:latest
   ```
2. In `docker-compose.yml` die Zeile `build: .` durch
   `image: <dein-dockerhub-name>/flashcards:latest` ersetzen.
3. In CasaOS: **App Store → Install a customized app** und den Inhalt von
   `docker-compose.yml` einfuegen.

Der `x-casaos`-Abschnitt in `docker-compose.yml` liefert Titel, Beschreibung
und Kategorie fuer die CasaOS-Oberflaeche. Sollte CasaOS dieses Format bei
dir nicht/anders interpretieren, laeuft der Container trotzdem normal –
dieser Abschnitt ist reine Anzeige-Metadaten, keine Funktionsvoraussetzung.

## Lokal entwickeln/testen (ohne Docker)

```bash
cd CasaOS
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python wsgi.py
```

Die App laeuft dann unter `http://127.0.0.1:5000` mit `DATA_DIR=./data`
(lokaler Ordner neben `wsgi.py`).

## Tests

```bash
cd CasaOS
python -m pytest tests/ -v
```

## Bekannte Abweichungen zur Desktop-App

- Es gibt (bewusst) keine Benutzer-Anmeldung/Zugriffskontrolle – wer die
  URL/Port erreicht, kann die App benutzen. Fuer den Einsatz nur im eigenen
  Heimnetz gedacht; falls von aussen erreichbar, zusaetzlich ueber einen
  Reverse Proxy mit Auth absichern.
- Bilder werden nicht mehr serverseitig auf eine feste Groesse
  herunterskaliert (das macht der Browser via CSS) – dadurch wird auch
  Pillow als Abhaengigkeit nicht mehr benoetigt.
