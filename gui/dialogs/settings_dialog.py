#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui/dialogs/settings_dialog.py – Einstellungsdialog (Datenbankpfad + Backup/Restore).

Tabs:
  1. Datenbankpfad  – Speicherort der SQLite-Datenbank konfigurieren
  2. Backup         – Backup erstellen und wiederherstellen

Wird beim Programmstart angezeigt, wenn:
  • Noch keine settings.json existiert.
  • Der gespeicherte Pfad nicht (mehr) existiert.

Kann außerdem jederzeit über den ⚙-Button im Hauptfenster geöffnet werden.
"""

import os
import shutil
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

import config


class DBSettingsDialog(ctk.CTkToplevel):
    """
    Modaler Einstellungsdialog mit zwei Reitern:
      • Datenbankpfad
      • Backup / Wiederherstellen

    Args:
        parent:       Übergeordnetes Fenster (kann None sein beim Erststart).
        startup_mode: True = Programm startet gerade, Dialog ist obligatorisch.
    """

    def __init__(self, parent=None, startup_mode: bool = False):
        super().__init__(parent)
        self.result_ok: bool = False
        self.startup_mode    = startup_mode

        self.title("Einstellungen")
        self.geometry("600x420")
        self.resizable(False, False)

        if parent:
            self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_current_path()

        if startup_mode:
            self.protocol("WM_DELETE_WINDOW", self._on_cancel_startup)
        else:
            self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ==================================================================
    # UI-Aufbau
    # ==================================================================

    def _build_ui(self):
        self.tab_view = ctk.CTkTabview(self, anchor="nw")
        self.tab_view.pack(expand=True, fill="both", padx=12, pady=12)

        self._tab_db     = self.tab_view.add("💾  Datenbankpfad")
        self._tab_backup = self.tab_view.add("📦  Backup")

        self._build_db_tab()
        self._build_backup_tab()

    # ------------------------------------------------------------------
    # Tab 1 – Datenbankpfad
    # ------------------------------------------------------------------

    def _build_db_tab(self):
        tab = self._tab_db

        hint = (
            "Wählen Sie das Verzeichnis, in dem die Datenbank\n"
            f"'{config.DB_FILENAME}' gespeichert wird (oder bereits liegt).\n"
            "Das Verzeichnis wird automatisch erstellt, falls es nicht existiert."
        )
        ctk.CTkLabel(tab, text=hint, justify="left", anchor="w",
                     font=ctk.CTkFont(size=12)).pack(fill="x", pady=(10, 6))

        # Pfadeingabe
        path_frame = ctk.CTkFrame(tab, fg_color="transparent")
        path_frame.pack(fill="x", pady=4)
        path_frame.grid_columnconfigure(0, weight=1)

        self.path_entry = ctk.CTkEntry(path_frame, placeholder_text="Pfad auswählen…")
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            path_frame, text="Durchsuchen…", width=130,
            command=self._browse_directory,
        ).grid(row=0, column=1)

        # Status
        self.status_label = ctk.CTkLabel(
            tab, text="", text_color="gray", font=ctk.CTkFont(size=11), anchor="w",
        )
        self.status_label.pack(fill="x", pady=(4, 0))

        # Buttons
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(14, 6))

        ctk.CTkButton(
            btn_frame, text="Speichern & Übernehmen", command=self._save,
        ).pack(side="left", padx=(0, 10))

        if not self.startup_mode:
            ctk.CTkButton(
                btn_frame, text="Abbrechen",
                fg_color="gray", hover_color="#555555",
                command=self.destroy,
            ).pack(side="left")

    # ------------------------------------------------------------------
    # Tab 2 – Backup
    # ------------------------------------------------------------------

    def _build_backup_tab(self):
        tab = self._tab_backup

        # ---- Backup erstellen ----------------------------------------
        box_create = ctk.CTkFrame(tab)
        box_create.pack(fill="x", pady=(10, 6), padx=4)

        ctk.CTkLabel(
            box_create,
            text="Backup erstellen",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            box_create,
            text=(
                "Erstellt eine Kopie der aktuellen Datenbank.\n"
                "Der Dateiname enthält automatisch Datum und Uhrzeit."
            ),
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(fill="x", padx=12, pady=(0, 8))

        btn_row_create = ctk.CTkFrame(box_create, fg_color="transparent")
        btn_row_create.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkButton(
            btn_row_create,
            text="📥  Backup jetzt erstellen",
            width=200,
            command=self._create_backup,
        ).pack(side="left", padx=(0, 10))

        self.backup_status_label = ctk.CTkLabel(
            btn_row_create, text="", font=ctk.CTkFont(size=11), anchor="w",
        )
        self.backup_status_label.pack(side="left", fill="x", expand=True)

        # ---- Backup einspielen ---------------------------------------
        box_restore = ctk.CTkFrame(tab)
        box_restore.pack(fill="x", pady=(6, 6), padx=4)

        ctk.CTkLabel(
            box_restore,
            text="Backup wiederherstellen",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            box_restore,
            text=(
                "Wählen Sie eine Backup-Datei (.db) aus und stellen Sie\n"
                "die Datenbank wieder her. Die aktuelle Datenbank wird dabei ersetzt!"
            ),
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(fill="x", padx=12, pady=(0, 8))

        btn_row_restore = ctk.CTkFrame(box_restore, fg_color="transparent")
        btn_row_restore.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkButton(
            btn_row_restore,
            text="📤  Backup auswählen & einspielen",
            width=240,
            fg_color="#C0392B",
            hover_color="#96281B",
            command=self._restore_backup,
        ).pack(side="left", padx=(0, 10))

        self.restore_status_label = ctk.CTkLabel(
            btn_row_restore, text="", font=ctk.CTkFont(size=11), anchor="w",
        )
        self.restore_status_label.pack(side="left", fill="x", expand=True)

    # ==================================================================
    # Tab 1 – Logik: Datenbankpfad
    # ==================================================================

    def _load_current_path(self):
        current = config.get_db_directory()
        if current:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, current)
            self._check_path_status(current)

    def _browse_directory(self):
        initial = self.path_entry.get().strip() or os.path.expanduser("~")
        chosen  = filedialog.askdirectory(
            parent=self,
            title="Datenbankverzeichnis auswählen",
            initialdir=initial,
        )
        if chosen:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, chosen)
            self._check_path_status(chosen)

    def _check_path_status(self, path: str):
        db_path = os.path.join(path, config.DB_FILENAME)
        if os.path.isfile(db_path):
            self.status_label.configure(
                text=f"✔  Datenbank gefunden: {db_path}",
                text_color="green",
            )
        elif os.path.isdir(path):
            self.status_label.configure(
                text="ℹ  Verzeichnis existiert – neue Datenbank wird erstellt.",
                text_color="orange",
            )
        else:
            self.status_label.configure(
                text="ℹ  Verzeichnis wird beim ersten Start automatisch angelegt.",
                text_color="gray",
            )

    def _save(self):
        path = self.path_entry.get().strip()
        if not path:
            messagebox.showwarning(
                "Kein Pfad",
                "Bitte geben Sie ein Verzeichnis an oder wählen Sie eines aus.",
                parent=self,
            )
            return
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            messagebox.showerror(
                "Verzeichnisfehler",
                f"Das Verzeichnis konnte nicht erstellt werden:\n{path}\n\nFehler: {e}",
                parent=self,
            )
            return

        if config.save_config(path):
            self.result_ok = True
            self.destroy()
        else:
            messagebox.showerror(
                "Speicherfehler",
                "Die Einstellungen konnten nicht gespeichert werden.\n"
                "Bitte Schreibrechte für das Programmverzeichnis prüfen.",
                parent=self,
            )

    def _on_cancel_startup(self):
        if messagebox.askyesno(
            "Programm beenden?",
            "Ohne Datenbankpfad kann das Programm nicht starten.\n\n"
            "Möchten Sie das Programm wirklich beenden?",
            parent=self,
        ):
            self.destroy()
            import sys
            sys.exit(0)

    # ==================================================================
    # Tab 2 – Logik: Backup
    # ==================================================================

    def _get_source_db(self) -> str | None:
        """Gibt den konfigurierten DB-Pfad zurück oder zeigt Fehler an."""
        db_file = config.get_db_file()
        if not db_file:
            messagebox.showerror(
                "Kein Datenbankpfad",
                "Es ist noch kein Datenbankpfad konfiguriert.\n"
                "Bitte zuerst den Pfad im Reiter 'Datenbankpfad' festlegen.",
                parent=self,
            )
            return None
        if not os.path.isfile(db_file):
            messagebox.showerror(
                "Datenbank nicht gefunden",
                f"Die Datenbankdatei wurde nicht gefunden:\n{db_file}\n\n"
                "Bitte zuerst das Programm starten, damit die Datenbank erstellt wird.",
                parent=self,
            )
            return None
        return db_file

    def _create_backup(self):
        """Kopiert die aktuelle DB-Datei in ein vom Benutzer gewähltes Verzeichnis."""
        source = self._get_source_db()
        if not source:
            return

        # Standardverzeichnis = Verzeichnis der DB selbst
        initial_dir = config.get_db_directory() or os.path.expanduser("~")

        # Zeitstempel für den Dateinamen
        timestamp   = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"backup_{timestamp}_{config.DB_FILENAME}"

        dest = filedialog.asksaveasfilename(
            parent=self,
            title="Backup speichern unter…",
            initialdir=initial_dir,
            initialfile=default_name,
            defaultextension=".db",
            filetypes=[("SQLite-Datenbank", "*.db"), ("Alle Dateien", "*.*")],
        )

        if not dest:
            return  # Benutzer hat abgebrochen

        try:
            shutil.copy2(source, dest)
            size_kb = os.path.getsize(dest) // 1024
            self.backup_status_label.configure(
                text=f"✔  Gespeichert ({size_kb} KB)",
                text_color="green",
            )
            messagebox.showinfo(
                "Backup erfolgreich",
                f"Backup wurde erfolgreich erstellt:\n\n{dest}\n\nDateigröße: {size_kb} KB",
                parent=self,
            )
        except Exception as e:
            self.backup_status_label.configure(
                text="✘  Fehler beim Erstellen", text_color="red",
            )
            messagebox.showerror(
                "Backup fehlgeschlagen",
                f"Das Backup konnte nicht erstellt werden:\n\n{e}",
                parent=self,
            )

    def _restore_backup(self):
        """Stellt eine gewählte Backup-Datei als aktive Datenbank wieder her."""
        db_file = config.get_db_file()
        if not db_file:
            messagebox.showerror(
                "Kein Datenbankpfad",
                "Es ist noch kein Datenbankpfad konfiguriert.\n"
                "Bitte zuerst den Pfad im Reiter 'Datenbankpfad' festlegen.",
                parent=self,
            )
            return

        initial_dir = config.get_db_directory() or os.path.expanduser("~")

        source = filedialog.askopenfilename(
            parent=self,
            title="Backup-Datei auswählen…",
            initialdir=initial_dir,
            filetypes=[("SQLite-Datenbank", "*.db"), ("Alle Dateien", "*.*")],
        )

        if not source:
            return  # Benutzer hat abgebrochen

        # Sicherheitsabfrage
        confirm = messagebox.askyesno(
            "Backup einspielen – Bitte bestätigen",
            f"Möchten Sie die aktuelle Datenbank wirklich ersetzen?\n\n"
            f"Backup-Datei:\n  {source}\n\n"
            f"Aktuelle Datenbank:\n  {db_file}\n\n"
            "⚠  Die aktuelle Datenbank wird ÜBERSCHRIEBEN!\n"
            "Stellen Sie sicher, dass keine anderen Nutzer die Datenbank geöffnet haben.",
            icon="warning",
            parent=self,
        )

        if not confirm:
            return

        try:
            # Automatisches Sicherheits-Backup der aktuellen DB anlegen
            if os.path.isfile(db_file):
                ts          = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                auto_backup = os.path.join(
                    config.get_db_directory(),
                    f"vor_restore_{ts}_{config.DB_FILENAME}",
                )
                shutil.copy2(db_file, auto_backup)
                print(f"[Backup] Automatisches Sicherheits-Backup erstellt: {auto_backup}")

            # Backup einspielen
            shutil.copy2(source, db_file)

            size_kb = os.path.getsize(db_file) // 1024
            self.restore_status_label.configure(
                text=f"✔  Eingespielt ({size_kb} KB)",
                text_color="green",
            )
            messagebox.showinfo(
                "Wiederherstellung erfolgreich",
                f"Das Backup wurde erfolgreich eingespielt.\n\n"
                f"Datei: {source}\n"
                f"Größe: {size_kb} KB\n\n"
                "Bitte starten Sie das Programm neu, damit alle Daten\n"
                "korrekt aus der wiederhergestellten Datenbank geladen werden.",
                parent=self,
            )
            # Ergebnis-Flag setzen damit das Hauptfenster die Liste neu lädt
            self.result_ok = True

        except Exception as e:
            self.restore_status_label.configure(
                text="✘  Fehler beim Einspielen", text_color="red",
            )
            messagebox.showerror(
                "Wiederherstellung fehlgeschlagen",
                f"Das Backup konnte nicht eingespielt werden:\n\n{e}",
                parent=self,
            )
