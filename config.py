#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py – Konfiguration & Einstellungsverwaltung für die IT Inventar Verwaltung.

Lädt und speichert den Datenbankpfad in einer lokalen settings.json-Datei.
"""

import os
import json

# ---------------------------------------------------------------------------
# Versionskonstante
# ---------------------------------------------------------------------------
APP_VERSION = "5.3.1"

# ---------------------------------------------------------------------------
# Status-Konstanten
# ---------------------------------------------------------------------------
STATUS_OPTIONS = [
    "Alle anzeigen",
    "Lagernd & Im Einsatz",
    "Lagernd",
    "Im Einsatz",
    "Defekt/RMA",
    "Ausgemustert",
]
DEFAULT_STATUS_FILTER = "Lagernd & Im Einsatz"
DEFAULT_ASSET_STATUS  = "Lagernd"

# ---------------------------------------------------------------------------
# Datenbankdateiname (unveränderlich)
# ---------------------------------------------------------------------------
DB_FILENAME = "it_inventory_v3.db"

# ---------------------------------------------------------------------------
# Pfad zur Einstellungsdatei (liegt neben main.py / diesem Skript)
# ---------------------------------------------------------------------------
_BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_BASE_DIR, "settings.json")

# ---------------------------------------------------------------------------
# Interne Zustandsvariablen
# ---------------------------------------------------------------------------
_db_directory: str | None = None
_db_file:      str | None = None


# ---------------------------------------------------------------------------
# Öffentliche Getter
# ---------------------------------------------------------------------------
def get_db_file() -> str | None:
    """Gibt den vollständigen Pfad zur SQLite-Datenbankdatei zurück."""
    return _db_file


def get_db_directory() -> str | None:
    """Gibt das Verzeichnis zurück, in dem die Datenbank gespeichert wird."""
    return _db_directory


def is_configured() -> bool:
    """True, wenn ein Datenbankpfad gesetzt ist."""
    return _db_file is not None


# ---------------------------------------------------------------------------
# Laden & Speichern
# ---------------------------------------------------------------------------
def load_config() -> bool:
    """
    Lädt die Konfiguration aus settings.json.

    Returns:
        True  – Pfad erfolgreich geladen und gesetzt.
        False – Keine Konfiguration vorhanden oder Fehler.
    """
    global _db_directory, _db_file

    if not os.path.exists(CONFIG_FILE):
        return False

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        directory = cfg.get("db_directory", "").strip()
        if directory:
            _db_directory = directory
            _db_file      = os.path.join(directory, DB_FILENAME)
            return True

    except Exception as e:
        print(f"[config] Fehler beim Laden von {CONFIG_FILE}: {e}")

    return False


def save_config(db_directory: str) -> bool:
    """
    Speichert den Datenbankpfad in settings.json und setzt die internen Variablen.

    Args:
        db_directory: Verzeichnis, in dem die SQLite-Datenbank liegt/erstellt wird.

    Returns:
        True bei Erfolg, False bei Fehler.
    """
    global _db_directory, _db_file

    _db_directory = db_directory
    _db_file      = os.path.join(db_directory, DB_FILENAME)

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"db_directory": db_directory},
                f,
                indent=2,
                ensure_ascii=False,
            )
        return True
    except Exception as e:
        print(f"[config] Fehler beim Speichern von {CONFIG_FILE}: {e}")
        return False
