#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils.py – Allgemeine Hilfsfunktionen für die IT Inventar Verwaltung.
"""

import datetime
import uuid
from tkinter import messagebox


def validate_date(date_str: str) -> bool:
    """
    Prüft ob date_str ein gültiges Datum im Format JJJJ-MM-TT ist.
    Leere Werte und '-' werden als gültig akzeptiert.

    Returns:
        True  – gültiges oder leeres Datum.
        False – ungültiges Datum (zeigt automatisch eine Fehlermeldung an).
    """
    if not date_str or date_str == "-":
        return True
    try:
        datetime.date.fromisoformat(date_str)
        return True
    except ValueError:
        messagebox.showerror(
            "Ungültiges Datum",
            f"'{date_str}' ist kein gültiges Datum.\n"
            "Bitte Format JJJJ-MM-TT verwenden oder das Feld leer lassen.",
            icon="warning",
        )
        return False


def generate_id(prefix: str) -> str:
    """
    Erzeugt eine eindeutige ID im Format PREFIX-XXXXXXXX.

    Beispiel:
        generate_id("DEV")  →  "DEV-3F8A21C4"
        generate_id("MAT")  →  "MAT-A0B12E7F"
    """
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
