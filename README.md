# IT Inventar Verwaltung

![Version](https://img.shields.io/badge/Version-5.3.1-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![Lizenz](https://img.shields.io/badge/Lizenz-AGPLv3-orange)

Eine einfache, lokale IT-Asset-Management-Anwendung zur Verwaltung und Inventarisierung von Geräten und Material in einer IT-Abteilung.

Gebaut mit **Python 3**, **CustomTkinter** und **SQLite**.

---

## Funktionen

- **Geräte verwalten** – Typ, Modell, Hersteller, Seriennummer, IP-Adresse, Standort, Mitarbeiter, Rechnungsnummer, Händler, Lieferschein- und Auftragsnummer
- **Material verwalten** – Name, Typ, Hersteller, Farbe, Lagerbestand, EAN-Code
- **Notizen / Kommentare** – Freies Textfeld pro Gerät und Material für interne Hinweise
- **Gerät ↔ Material verknüpfen** – Many-to-Many-Beziehungen
- **Suche & Status-Filter** – Echtzeit-Suche, Filterung nach Status
- **Autocomplete** – Vorschläge aus bestehenden Einträgen
- **Datenbankpfad konfigurierbar** – Einstellungsdialog beim ersten Start und jederzeit über den ⚙-Button
- **Backup & Restore** – Backup erstellen und einspielen direkt in der GUI
- **Barcode-Scan-Unterstützung** für Lagerbuchungen

---

## Installation

### Windows

#### ✅ Empfohlen: pipx (sauber & isoliert)

**1. Python installieren**
- Herunterladen von: https://www.python.org/downloads/
- Wichtig: Bei der Installation **„Add Python to PATH"** aktivieren

**2. Git installieren**
- Herunterladen von: https://git-scm.com/download/win
- Installer ausführen, alle Standardoptionen bestätigen

**3. pipx installieren**

Eingabeaufforderung (cmd) öffnen und ausführen:
```
python -m pip install --upgrade pip
python -m pip install pipx
python -m pipx ensurepath
```
Terminal neu öffnen (damit der Pfad aktiv ist).

**4. Programm installieren & starten**
```
pipx install git+https://github.com/MrLetsPlay4Fun/IT-Inventar-DB.git
it-inventar
```

---

#### Alternative: Virtualenv (manuell)

```
git clone https://github.com/MrLetsPlay4Fun/IT-Inventar-DB.git
cd IT-Inventar-DB
python -m venv .venv
.venv\Scripts\activate
pip install .
it-inventar
```

---

### macOS

#### ✅ Empfohlen: pipx (sauber & isoliert)

**1. Python & Git installieren**

Homebrew verwenden (https://brew.sh):
```
brew install python git pipx
pipx ensurepath
```
Terminal neu öffnen.

**2. Programm installieren & starten**
```
pipx install git+https://github.com/MrLetsPlay4Fun/IT-Inventar-DB.git
it-inventar
```

---

#### Alternative: Virtualenv (manuell)

```
git clone https://github.com/MrLetsPlay4Fun/IT-Inventar-DB.git
cd IT-Inventar-DB
python3 -m venv .venv
source .venv/bin/activate
pip install .
it-inventar
```

---

## Erster Start

Beim ersten Start erscheint automatisch ein Einrichtungsdialog:

1. Auf **„Durchsuchen…"** klicken
2. Verzeichnis auswählen, in dem die Datenbank gespeichert werden soll
   *(z. B. ein lokaler Ordner oder ein freigegebener Netzwerkordner)*
3. **„Speichern & Übernehmen"** klicken

Das Verzeichnis wird automatisch erstellt, falls es noch nicht existiert.
Der Pfad wird lokal in `settings.json` gespeichert *(nicht im Repository)*.

Den Datenbankpfad kann man jederzeit über den **⚙ Einstellungen**-Button im Hauptfenster ändern.

---

## Backup & Wiederherstellung

Im Hauptfenster auf **⚙ Einstellungen** → Reiter **📦 Backup**:

| Funktion | Beschreibung |
|---|---|
| **📥 Backup erstellen** | Kopiert die aktuelle Datenbank in ein beliebiges Verzeichnis. Dateiname enthält automatisch Datum und Uhrzeit. |
| **📤 Backup einspielen** | Wählt eine Backup-Datei aus und stellt sie wieder her. Vor dem Überschreiben wird automatisch ein Sicherheits-Backup der aktuellen Datenbank erstellt. |

---

## Aktualisierung

### pipx

```
pipx upgrade it-inventar-db
```

### Virtualenv

```
cd IT-Inventar-DB
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS
git pull
pip install .
```

---

## Projektstruktur

```
IT-Inventar-DB/
├── main.py                        # Einstiegspunkt
├── config.py                      # Konfiguration & Pfadverwaltung
├── database.py                    # Alle Datenbankoperationen
├── utils.py                       # Hilfsfunktionen (Datum, ID)
├── pyproject.toml                 # Paket-Konfiguration & Einstiegspunkt
├── requirements.txt               # Python-Abhängigkeiten
├── settings.json                  # Lokaler Datenbankpfad (nicht im Repo)
├── gui/
│   ├── app.py                     # Hauptfenster
│   ├── widgets.py                 # AutocompleteEntry
│   └── dialogs/
│       ├── device_dialog.py       # Gerät hinzufügen / bearbeiten
│       ├── material_dialog.py     # Material hinzufügen / bearbeiten
│       ├── association_dialogs.py # Verknüpfungsansichten
│       └── settings_dialog.py     # DB-Pfad & Backup
└── LICENSE
```

---

## Hinweise für mehrere Benutzer / Netzwerkbetrieb

- Jeder Nutzer installiert das Programm lokal (per pipx oder Virtualenv).
- In den **Einstellungen** wird als Datenbankpfad ein **gemeinsamer Netzwerkordner** eingetragen
  *(z. B. `\\Server\IT\Inventar` unter Windows oder ein gemountetes Netzlaufwerk unter macOS)*.
- SQLite unterstützt keinen gleichzeitigen Schreibzugriff mehrerer Nutzer.
  Für größere Teams empfiehlt sich eine Migration zu PostgreSQL oder MariaDB.

---

## Changelog

### v5.3.1 – 2026-03-21
- **Neu:** Kaufpreisfeld pro Gerät (`purchase_price`) und Stückpreisfeld pro Material (`unit_price`) mit Float-Validierung
- **Neu:** Automatische Datenbankmigration für bestehende Installationen (Spalten werden ohne Datenverlust ergänzt)

### v5.3.0 – 2026-03-21
- **Neu:** Notizfeld pro Gerät und Material – freies mehrzeiliges Textfeld für interne Hinweise, Besonderheiten oder Kommentare
- **Neu:** Automatische Datenbankmigration für bestehende Installationen (Spalte `notes` wird ohne Datenverlust ergänzt)

### v5.2.0
- Barcode-Scan-Unterstützung für schnelle Lagerbuchungen
- Autocomplete für Geräteeingabefelder (Typ, Hersteller, Modell, Standort, Mitarbeiter, Händler)
- Backup & Restore direkt in der GUI
- Konfigurierbare Datenbankpfade inkl. Netzwerkpfad-Unterstützung
- Many-to-Many-Verknüpfung zwischen Geräten und Material
- Status-Filter und Echtzeit-Suche in beiden Tabs

---

## Lizenz

Dieses Projekt steht unter der **GNU Affero General Public License v3.0 (AGPLv3)**.
Vollständiger Lizenztext: [LICENSE](LICENSE) · https://www.gnu.org/licenses/agpl-3.0.html
