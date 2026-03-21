#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui/dialogs/material_dialog.py – Hinzufügen / Bearbeiten von Material.
"""

from tkinter import messagebox
import customtkinter as ctk

from config import STATUS_OPTIONS, DEFAULT_ASSET_STATUS
from database import add_material_db, update_material_db
from utils import generate_id


class AddEditMaterialWindow(ctk.CTkToplevel):
    """
    Modales Fenster zum Anlegen oder Bearbeiten eines Materialeintrags.

    Args:
        parent:        Übergeordnetes Fenster (App-Instanz).
        material_data: dict mit vorhandenen Materialdaten (None = Neuanlage).
    """

    def __init__(self, parent, material_data: dict | None = None):
        super().__init__(parent)
        self.parent_app   = parent
        self.material_data = material_data
        self.material_id   = (
            material_data["material_id"] if material_data else generate_id("MAT")
        )

        is_editing = bool(material_data)
        self.title("Material bearbeiten" if is_editing else "Material hinzufügen")
        self.geometry("460x660")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui(is_editing)

        if is_editing:
            self._fill_fields(material_data)

        self.name_entry.focus()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self, is_editing: bool):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(pady=20, padx=20, fill="both", expand=True)
        frame.grid_columnconfigure(1, weight=1)

        fields = [
            ("Name*:",           "name_entry"),
            ("Typ:",             "type_entry"),
            ("Hersteller:",      "manu_entry"),
            ("Farbe:",           "color_entry"),
            ("Lagerbestand:",    "stock_entry"),
            ("EAN / Prod-Barcode:", "ean_entry"),
            ("Inventarnummer:",  "inv_entry"),
        ]

        for row, (label_text, attr) in enumerate(fields):
            ctk.CTkLabel(frame, text=label_text).grid(
                row=row, column=0, padx=(0, 10), pady=8, sticky="w"
            )
            entry = ctk.CTkEntry(frame, width=300)
            entry.grid(row=row, column=1, pady=8, sticky="ew")
            setattr(self, attr, entry)

        # Status-Dropdown
        status_row = len(fields)
        ctk.CTkLabel(frame, text="Status:").grid(
            row=status_row, column=0, padx=(0, 10), pady=8, sticky="w"
        )
        self.status_var = ctk.StringVar(value=DEFAULT_ASSET_STATUS)
        status_choices  = [s for s in STATUS_OPTIONS if s not in ("Alle anzeigen", "Lagernd & Im Einsatz")]
        self.status_menu = ctk.CTkOptionMenu(
            frame, variable=self.status_var, values=status_choices, width=300
        )
        self.status_menu.grid(row=status_row, column=1, pady=8, sticky="ew")

        # Notizen
        notes_row = status_row + 1
        ctk.CTkLabel(frame, text="Notizen:").grid(
            row=notes_row, column=0, padx=(0, 10), pady=(8, 0), sticky="nw"
        )
        self.notes_textbox = ctk.CTkTextbox(frame, height=70)
        self.notes_textbox.grid(row=notes_row, column=1, pady=(8, 0), sticky="ew")

        # Speichern-Button
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 20), padx=20, fill="x")
        ctk.CTkButton(btn_frame, text="Speichern", command=self._save).pack()

    def _fill_fields(self, data: dict):
        self.name_entry.insert(0,  data.get("name", ""))
        self.type_entry.insert(0,  data.get("type", "") or "")
        self.manu_entry.insert(0,  data.get("manufacturer", "") or "")
        self.color_entry.insert(0, data.get("color", "") or "")
        self.stock_entry.insert(0, str(data.get("stock_quantity", 0)))
        self.ean_entry.insert(0,   data.get("ean_code", "") or "")
        self.inv_entry.insert(0,   data.get("inventory_number", "") or "")
        self.status_var.set(data.get("status", DEFAULT_ASSET_STATUS))
        self.notes_textbox.delete("1.0", "end")
        self.notes_textbox.insert("1.0", data.get("notes", "") or "")

    # ------------------------------------------------------------------
    # Speichern
    # ------------------------------------------------------------------

    def _save(self):
        name             = self.name_entry.get().strip()
        mat_type         = self.type_entry.get().strip() or "-"
        manufacturer     = self.manu_entry.get().strip() or "-"
        color            = self.color_entry.get().strip() or "-"
        stock_str        = self.stock_entry.get().strip()
        ean_code         = self.ean_entry.get().strip() or None
        inventory_number = self.inv_entry.get().strip() or None
        status           = self.status_var.get()
        notes            = self.notes_textbox.get("1.0", "end").strip() or None

        if not name:
            messagebox.showwarning(
                "Eingabe fehlt",
                "Bitte geben Sie einen Materialnamen ein (Pflichtfeld).",
                parent=self,
            )
            self.name_entry.focus()
            return

        try:
            stock = int(stock_str) if stock_str else 0
            if stock < 0:
                messagebox.showwarning(
                    "Ungültige Eingabe",
                    "Lagerbestand darf nicht negativ sein.",
                    parent=self,
                )
                self.stock_entry.focus()
                return
        except ValueError:
            messagebox.showwarning(
                "Ungültige Eingabe",
                "Lagerbestand muss eine gültige ganze Zahl sein.",
                parent=self,
            )
            self.stock_entry.focus()
            return

        try:
            if self.material_data:
                success = update_material_db(
                    self.material_id, name, mat_type, manufacturer,
                    color, stock, ean_code, inventory_number, status, notes,
                )
                msg = "Material erfolgreich aktualisiert."
            else:
                success = add_material_db(
                    self.material_id, name, mat_type, manufacturer,
                    color, stock, ean_code, inventory_number, status, notes,
                )
                msg = f"Material '{name}' erfolgreich hinzugefügt."

            if success:
                messagebox.showinfo("Erfolg", msg, parent=self)
                self.parent_app.refresh_material_list()
                self.destroy()
        except Exception as e:
            messagebox.showerror("Fehler", f"Unerwarteter Fehler:\n{e}", parent=self)
            print(f"[material_dialog] Fehler beim Speichern: {e}")
