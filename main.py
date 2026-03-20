#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py – Einstiegspunkt der IT Inventar Verwaltung.

Ablauf beim Start:
  1. Konfiguration laden (settings.json).
  2. Wenn kein Datenbankpfad konfiguriert ist oder die DB-Datei fehlt:
       → Einstellungsdialog öffnen.
  3. Hauptfenster (App) starten.
"""

import sys
import tkinter as tk
from tkinter import messagebox

# DPI-Awareness unter Windows (vor GUI-Initialisierung)
if sys.platform == "win32":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print(f"[main] DPI Awareness konnte nicht gesetzt werden: {e}")

import os
import customtkinter as ctk

import config
from gui.dialogs.settings_dialog import DBSettingsDialog
from gui.app import App


def _ensure_db_path_configured() -> bool:
    """
    Stellt sicher, dass ein gültiger Datenbankpfad konfiguriert ist.

    Returns:
        True  – Pfad vorhanden und bereit.
        False – Benutzer hat Einrichtung abgebrochen.
    """
    # Verstecktes Tk-Root-Fenster als Elternelement für den Dialog
    root = tk.Tk()
    root.withdraw()

    needs_setup = False

    if not config.load_config():
        # Keine Konfiguration gefunden
        needs_setup = True
        print("[main] Keine Konfiguration gefunden – Einstellungsdialog wird angezeigt.")
    elif not os.path.isdir(config.get_db_directory()):
        # Gespeichertes Verzeichnis existiert nicht mehr
        needs_setup = True
        messagebox.showwarning(
            "Datenbankpfad nicht gefunden",
            f"Das konfigurierte Datenbankverzeichnis wurde nicht gefunden:\n"
            f"{config.get_db_directory()}\n\n"
            "Bitte wählen Sie einen neuen Speicherort.",
        )
        print(f"[main] Verzeichnis nicht gefunden: {config.get_db_directory()}")

    if needs_setup:
        dlg = DBSettingsDialog(parent=None, startup_mode=True)
        root.wait_window(dlg)

        if not dlg.result_ok:
            # Benutzer hat abgebrochen
            root.destroy()
            return False

    root.destroy()
    return True


def main():
    """Haupteinstiegspunkt."""
    if not _ensure_db_path_configured():
        print("[main] Konfiguration abgebrochen – Programm wird beendet.")
        sys.exit(0)

    print(f"[main] Starte Anwendung – DB: {config.get_db_file()}")

    try:
        app = App()
        if app.winfo_exists():
            app.mainloop()
    except Exception as e:
        print(f"[main] FATAL: {e}")
        import traceback
        traceback.print_exc()
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Kritischer Startfehler",
                f"Ein unerwarteter Fehler hat den Start verhindert:\n\n{e}\n\n"
                "Bitte überprüfen Sie die Konsolenausgabe für Details.",
            )
            root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    main()
