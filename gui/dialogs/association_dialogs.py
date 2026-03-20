#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui/dialogs/association_dialogs.py – Dialoge für Gerät-Material-Verknüpfungen.

Enthält:
    ShowAssociatedDevicesWindow  – Zeigt Geräte, die mit einem Material verknüpft sind.
    ShowAssociatedMaterialsWindow – Zeigt Materialien, die mit einem Gerät verknüpft sind.
"""

import tkinter as tk
import tkinter.ttk as ttk
import customtkinter as ctk

from database import (
    get_associated_devices_for_material_db,
    get_associated_materials_for_device_db,
)


class ShowAssociatedDevicesWindow(ctk.CTkToplevel):
    """Zeigt alle Geräte, die mit einem bestimmten Material verknüpft sind."""

    def __init__(self, parent, material_id: str, material_name: str):
        super().__init__(parent)
        self.material_id = material_id
        self.title(f"Zugewiesene Geräte – {material_name} (ID: {material_id})")
        self.geometry("850x500")
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text=f"Folgende Geräte sind mit dem Material '{material_name}' verknüpft:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(pady=10)

        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(pady=5, padx=10, fill="both", expand=True)

        cols = ("ID", "Modell", "Typ", "Mitarbeiter", "Standort", "Inventarnummer", "Status")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        col_widths   = {"ID": 100, "Modell": 150, "Typ": 100,
                        "Mitarbeiter": 120, "Standort": 120, "Inventarnummer": 120, "Status": 80}
        col_anchors  = {"Status": "center", "ID": "w"}

        for col in cols:
            self.tree.heading(col, text=col, anchor="w")
            self.tree.column(col, width=col_widths.get(col, 100),
                             anchor=col_anchors.get(col, "w"), stretch=tk.YES)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(expand=True, fill="both")

        self._load()
        ctk.CTkButton(self, text="Schließen", command=self.destroy).pack(pady=10)

    def _load(self):
        devices = get_associated_devices_for_material_db(self.material_id)
        self.tree.delete(*self.tree.get_children())
        db_cols = ("device_id", "model", "device_type", "employee_name",
                   "location", "inventory_number", "status")
        if devices:
            for d in devices:
                self.tree.insert("", "end",
                                 values=[str(d.get(c, "") or "") for c in db_cols])
        else:
            self.tree.insert("", "end",
                             values=("Keine", "zugewiesenen", "Geräte", "gefunden.", "", "", ""),
                             tags=("empty",))
            self.tree.tag_configure("empty", foreground="gray")


class ShowAssociatedMaterialsWindow(ctk.CTkToplevel):
    """Zeigt alle Materialien, die mit einem bestimmten Gerät verknüpft sind."""

    def __init__(self, parent, device_id: str, device_name: str):
        super().__init__(parent)
        self.device_id = device_id
        self.title(f"Zugehöriges Material – {device_name} (ID: {device_id})")
        self.geometry("950x500")
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text=f"Folgendes Material ist mit dem Gerät '{device_name}' verknüpft:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(pady=10)

        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(pady=5, padx=10, fill="both", expand=True)

        cols = ("ID", "Name", "Typ", "Hersteller", "Farbe",
                "Lagerbestand", "EAN-Code", "Inventarnummer", "Status")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        col_widths  = {"ID": 90, "Name": 160, "Typ": 100, "Hersteller": 100, "Farbe": 70,
                       "Lagerbestand": 90, "EAN-Code": 100, "Inventarnummer": 100, "Status": 90}
        col_anchors = {"Lagerbestand": "center", "Status": "center"}

        for col in cols:
            self.tree.heading(col, text=col, anchor="w")
            self.tree.column(col, width=col_widths.get(col, 90),
                             anchor=col_anchors.get(col, "w"), stretch=tk.YES)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        hsb.pack(side="bottom", fill="x")
        self.tree.configure(xscrollcommand=hsb.set)

        self.tree.pack(expand=True, fill="both")

        self._load()
        ctk.CTkButton(self, text="Schließen", command=self.destroy).pack(pady=10)

    def _load(self):
        materials = get_associated_materials_for_device_db(self.device_id)
        self.tree.delete(*self.tree.get_children())
        db_cols = ("material_id", "name", "type", "manufacturer", "color",
                   "stock_quantity", "ean_code", "inventory_number", "status")
        if materials:
            for m in materials:
                self.tree.insert("", "end",
                                 values=[str(m.get(c, "") or "") for c in db_cols])
        else:
            self.tree.insert("", "end",
                             values=("Kein", "zugewiesenes", "Material", "gefunden.",
                                     "", "", "", "", ""),
                             tags=("empty",))
            self.tree.tag_configure("empty", foreground="gray")
