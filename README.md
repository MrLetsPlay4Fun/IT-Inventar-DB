# IT Inventar Verwaltung

Eine einfache, lokale IT-Asset-Management-Anwendung zur Verwaltung und Inventarisierung von Geräten und Material in einer IT-Abteilung.

Gebaut mit Python 3, CustomTkinter und SQLite.

---

## Funktionen

- **Geräte verwalten** – Typ, Modell, Hersteller, Seriennummer, IP-Adresse, Standort, Mitarbeiter, Rechnungsnummer, Händler, Lieferschein- und Auftragsnummer
- **Material verwalten** – Name, Typ, Hersteller, Farbe, Lagerbestand, EAN-Code
- **Gerät ↔ Material verknüpfen** – Many-to-Many-Beziehungen
- **Suche & Status-Filter** – Echtzeit-Suche, Filterung nach Status
- **Autocomplete** – Vorschläge aus bestehenden Einträgen
- **Datenbankpfad konfigurierbar** – Einstellungsdialog beim ersten Start und jederzeit über den ⚙-Button
- **Barcode-Scan-Unterstützung** für Lagerbuchungen

---

## Voraussetzungen

- **Python 3.10 oder neuer**
- **Git** (für die Installation per Repo)

---

## Installation

### Windows

1. **Git installieren**
   - Herunterladen von: https://git-scm.com/download/win
   - Installer ausführen, alle Standardoptionen bestätigen

2. **Python installieren**
   - Herunterladen von: https://www.python.org/downloads/
   - Wichtig: Bei der Installation **"Add Python to PATH"** aktivieren
   - Nach der Installation prüfen:
     ```
     python --version
     ```

3. **Repository klonen**
   - Git Bash oder Eingabeaufforderung (cmd) öffnen:
     ```
     git clone https://github.com/DEIN-USERNAME/IT-Inventar-DB.git
     cd IT-Inventar-DB
     ```

4. **Abhängigkeiten installieren**
   ```
   pip install -r requirements.txt
   ```

5. **Programm starten**
   ```
   python main.py
   ```
   Beim ersten Start erscheint ein Dialog zum Festlegen des Datenbankverzeichnisses.

---

### macOS

1. **Git installieren**
   - Git ist auf macOS meist vorinstalliert. Prüfen mit:
     ```
     git --version
     ```
   - Falls nicht vorhanden: https://git-scm.com/download/mac
     (oder über Homebrew: `brew install git`)

2. **Python installieren**
   - Herunterladen von: https://www.python.org/downloads/
   - Oder per Homebrew:
     ```
     brew install python
     ```
   - Nach der Installation prüfen:
     ```
     python3 --version
     ```

3. **Repository klonen**
   ```
   git clone https://github.com/DEIN-USERNAME/IT-Inventar-DB.git
   cd IT-Inventar-DB
   ```

4. **Abhängigkeiten installieren**
   ```
   pip3 install -r requirements.txt
   ```

5. **Programm starten**
   ```
   python3 main.py
   ```
   Beim ersten Start erscheint ein Dialog zum Festlegen des Datenbankverzeichnisses.

---

## Datenbankpfad einrichten

Beim **ersten Start** öffnet sich automatisch ein Dialog:

- Klicke auf **"Durchsuchen…"** und wähle das Verzeichnis aus, in dem die Datenbank gespeichert werden soll (z. B. ein freigegebener Netzwerkordner für mehrere Nutzer).
- Klicke auf **"Speichern & Übernehmen"**.
- Das Verzeichnis wird automatisch erstellt, falls es noch nicht existiert.
- Der Pfad wird lokal in `settings.json` gespeichert (nicht im Repository, da in `.gitignore`).

Den Datenbankpfad kann man jederzeit über den **⚙ Einstellungen**-Button im Hauptfenster ändern.

---

## Projektstruktur

```
IT-Inventar-DB/
├── main.py                        # Einstiegspunkt
├── config.py                      # Konfiguration & Pfadverwaltung
├── database.py                    # Alle Datenbankoperationen
├── utils.py                       # Hilfsfunktionen (Datum, ID)
├── requirements.txt               # Python-Abhängigkeiten
├── settings.json                  # Lokaler Datenbankpfad (nicht im Repo)
├── gui/
│   ├── app.py                     # Hauptfenster
│   ├── widgets.py                 # AutocompleteEntry
│   └── dialogs/
│       ├── device_dialog.py       # Gerät hinzufügen / bearbeiten
│       ├── material_dialog.py     # Material hinzufügen / bearbeiten
│       ├── association_dialogs.py # Verknüpfungsansichten
│       └── settings_dialog.py    # DB-Pfad Einstellungen
└── LICENSE
```

---

## Aktualisierung

```
git pull
```

---

## Lizenz

Dieses Projekt steht unter der **GNU Affero General Public License v3.0 (AGPLv3)**.
Vollständiger Lizenztext: https://www.gnu.org/licenses/agpl-3.0.html

---

## Hinweise für mehrere Benutzer / Netzwerkbetrieb

- Jeder Nutzer installiert das Programm lokal per `git clone`.
- In den **Einstellungen** wird als Datenbankpfad ein **gemeinsamer Netzwerkordner** eingetragen (z. B. `\\Server\IT\Inventar` oder ein gemountetes Netzlaufwerk).
- Die SQLite-Datenbank unterstützt keinen gleichzeitigen Schreibzugriff mehrerer Nutzer. Für größere Teams empfiehlt sich eine Datenbankmigration zu PostgreSQL oder MariaDB.
