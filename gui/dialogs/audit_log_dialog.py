#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui/dialogs/audit_log_dialog.py – Anzeige der Änderungshistorie (Audit-Log).
"""

import csv
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from database import get_audit_log_db


class AuditLogDialog(ctk.CTkToplevel):
    """Zeigt das Audit-Log mit Filter- und CSV-Export-Funktion."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Audit-Log – Änderungshistorie")
        self.geometry("1100x600")
        self.minsize(900, 400)
        self.transient(parent)
        self.grab_set()

        self._current_data: list[dict] = []

        self._build_ui()
        self._apply_filter()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Filter-Leiste
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=10, pady=(10, 0))

        ctk.CTkLabel(filter_frame, text="Typ:").pack(side="left", padx=(0, 4))
        self.type_var = ctk.StringVar(value="Alle")
        ctk.CTkOptionMenu(
            filter_frame,
            variable=self.type_var,
            values=["Alle", "device", "material"],
            width=110,
        ).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(filter_frame, text="Aktion:").pack(side="left", padx=(0, 4))
        self.action_var = ctk.StringVar(value="Alle")
        ctk.CTkOptionMenu(
            filter_frame,
            variable=self.action_var,
            values=["Alle", "ADD", "EDIT", "DELETE"],
            width=110,
        ).pack(side="left", padx=(0, 12))

        ctk.CTkLabel(filter_frame, text="Von:").pack(side="left", padx=(0, 4))
        self.date_from_entry = ctk.CTkEntry(filter_frame, width=100,
                                            placeholder_text="YYYY-MM-DD")
        self.date_from_entry.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(filter_frame, text="Bis:").pack(side="left", padx=(0, 4))
        self.date_to_entry = ctk.CTkEntry(filter_frame, width=100,
                                          placeholder_text="YYYY-MM-DD")
        self.date_to_entry.pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            filter_frame, text="Anwenden", width=90, command=self._apply_filter
        ).pack(side="left")

        # Treeview
        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(expand=True, fill="both", padx=10, pady=8)

        cols = ("ID", "Zeitstempel", "Typ", "Entity-ID", "Aktion", "Feld", "Alt", "Neu")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 selectmode="browse")

        widths = {
            "ID": 55, "Zeitstempel": 145, "Typ": 70, "Entity-ID": 120,
            "Aktion": 65, "Feld": 140, "Alt": 190, "Neu": 190,
        }
        for col in cols:
            self.tree.heading(col, text=col, anchor="w")
            self.tree.column(col, width=widths.get(col, 100),
                             anchor="w", stretch=tk.YES)

        self.tree.tag_configure("add", background="#C8E6C9")
        self.tree.tag_configure("edit", background="#FFF9C4")
        self.tree.tag_configure("del", background="#FFCCCC")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(side="bottom", fill="x")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(expand=True, fill="both")

        # Button-Leiste
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            btn_frame, text="CSV exportieren", width=140,
            command=self._export_csv,
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame, text="Schließen", width=100,
            command=self.destroy,
        ).pack(side="right")

    # ------------------------------------------------------------------
    # Daten laden
    # ------------------------------------------------------------------

    def _apply_filter(self):
        entity_type = self.type_var.get()
        action      = self.action_var.get()
        date_from   = self.date_from_entry.get().strip() or None
        date_to     = self.date_to_entry.get().strip() or None

        rows = get_audit_log_db(
            entity_type=entity_type,
            action=action,
            date_from=date_from,
            date_to=date_to,
        )
        self._current_data = rows
        self._populate_tree(rows)

    def _populate_tree(self, rows: list[dict]):
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            action = (row.get("action") or "").upper()
            if action == "ADD":
                tag = "add"
            elif action == "DELETE":
                tag = "del"
            else:
                tag = "edit"

            self.tree.insert("", "end", tags=(tag,), values=(
                row.get("log_id", ""),
                row.get("timestamp", ""),
                row.get("entity_type", ""),
                row.get("entity_id", ""),
                row.get("action", ""),
                row.get("field_name", "") or "",
                row.get("old_value", "") or "",
                row.get("new_value", "") or "",
            ))

    # ------------------------------------------------------------------
    # CSV-Export
    # ------------------------------------------------------------------

    def _export_csv(self):
        if not self._current_data:
            messagebox.showinfo("Kein Inhalt",
                                "Keine Daten zum Exportieren vorhanden.", parent=self)
            return

        dest = filedialog.asksaveasfilename(
            parent=self,
            title="Audit-Log exportieren",
            defaultextension=".csv",
            filetypes=[("CSV-Datei", "*.csv"), ("Alle Dateien", "*.*")],
        )
        if not dest:
            return

        try:
            with open(dest, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow([
                    "ID", "Zeitstempel", "Typ", "Entity-ID",
                    "Aktion", "Feld", "Alt", "Neu",
                ])
                for row in self._current_data:
                    writer.writerow([
                        row.get("log_id", ""),
                        row.get("timestamp", ""),
                        row.get("entity_type", ""),
                        row.get("entity_id", ""),
                        row.get("action", ""),
                        row.get("field_name", "") or "",
                        row.get("old_value", "") or "",
                        row.get("new_value", "") or "",
                    ])
            messagebox.showinfo("Export erfolgreich",
                                f"Audit-Log wurde exportiert nach:\n{dest}", parent=self)
        except Exception as e:
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}", parent=self)
