#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui/dialogs/device_dialog.py – Hinzufügen / Bearbeiten von Geräten.
"""

from tkinter import messagebox
import customtkinter as ctk

from config import STATUS_OPTIONS, DEFAULT_ASSET_STATUS
from database import (
    add_device_db,
    update_device_db,
    get_all_materials_db,
    get_linked_material_ids_for_device,
    link_materials_to_device_db,
    get_unique_column_values_db,
    log_audit_db,
)
from utils import generate_id, validate_date
from gui.widgets import AutocompleteEntry


class AddEditDeviceWindow(ctk.CTkToplevel):
    """
    Modales Fenster zum Anlegen oder Bearbeiten eines Geräteeintrags.

    Args:
        parent:      Übergeordnetes Fenster (App-Instanz).
        device_data: dict mit vorhandenen Gerätedaten (None = Neuanlage).
    """

    # Felder linke Spalte
    _LABELS_LEFT = [
        "Typ:",
        "Modell*:",
        "Hersteller:",
        "Anschaffungsdatum:",
        "Garantiedatum:",
        "Nächste Wartung:",
        "Standort:",
        "Mitarbeiter:",
        "Computername:",
        "IP-Adresse:",
    ]

    # Felder rechte Spalte
    _LABELS_RIGHT = [
        "Seriennummer:",
        "Inventarnummer:",
        "EAN-Code:",
        "Händler:",
        "Rechnungsnummer:",
        "Lieferscheinnummer:",
        "Auftragsnummer:",
        "Kaufpreis (€):",
    ]

    def __init__(self, parent, device_data: dict | None = None):
        super().__init__(parent)
        self.parent_app  = parent
        self.device_data = device_data
        self.device_id   = (
            device_data["device_id"] if device_data else generate_id("DEV")
        )

        is_editing = bool(device_data)
        self.title("Gerät bearbeiten" if is_editing else "Gerät hinzufügen")
        self.geometry("1020x840")
        self.transient(parent)
        self.grab_set()

        # Autocomplete-Vorschlagslisten
        self._suggestions = {
            "Typ:":        get_unique_column_values_db("device_type"),
            "Modell:":     get_unique_column_values_db("model"),
            "Hersteller:": get_unique_column_values_db("manufacturer"),
            "Standort:":   get_unique_column_values_db("location"),
            "Mitarbeiter:": get_unique_column_values_db("employee_name"),
            "Händler:":    get_unique_column_values_db("vendor"),
        }

        self.entries: dict = {}
        self._build_ui(is_editing)

        if is_editing:
            self._fill_fields(device_data)

        self.entries["Typ:"].focus()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self, is_editing: bool):
        # 2-Spalten-Eingabebereich
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(pady=10, padx=20, fill="x")
        input_frame.grid_columnconfigure(1, weight=1)
        input_frame.grid_columnconfigure(3, weight=1)

        def make_entry(clean_label: str):
            if clean_label in self._suggestions:
                return AutocompleteEntry(
                    input_frame,
                    suggestions_list=self._suggestions[clean_label],
                    width=220,
                )
            return ctk.CTkEntry(input_frame, width=220)

        # Linke Spalte (col 0+1)
        for row, label_text in enumerate(self._LABELS_LEFT):
            clean = label_text.replace("*:", ":")
            ctk.CTkLabel(input_frame, text=label_text).grid(
                row=row, column=0, padx=(0, 8), pady=5, sticky="w"
            )
            entry = make_entry(clean)
            entry.grid(row=row, column=1, padx=(0, 20), pady=5, sticky="ew")
            self.entries[clean] = entry

        # Rechte Spalte (col 2+3)
        for row, label_text in enumerate(self._LABELS_RIGHT):
            clean = label_text.replace("*:", ":")
            ctk.CTkLabel(input_frame, text=label_text).grid(
                row=row, column=2, padx=(0, 8), pady=5, sticky="w"
            )
            entry = make_entry(clean)
            entry.grid(row=row, column=3, padx=0, pady=5, sticky="ew")
            self.entries[clean] = entry

        # Status-Dropdown (rechte Spalte, unterste Zeile)
        status_row = len(self._LABELS_RIGHT)
        ctk.CTkLabel(input_frame, text="Status:").grid(
            row=status_row, column=2, padx=(0, 8), pady=5, sticky="w"
        )
        self.status_var  = ctk.StringVar(value=DEFAULT_ASSET_STATUS)
        status_choices   = [s for s in STATUS_OPTIONS if s not in ("Alle anzeigen", "Lagernd & Im Einsatz")]
        self.status_menu = ctk.CTkOptionMenu(
            input_frame, variable=self.status_var, values=status_choices, width=220
        )
        self.status_menu.grid(row=status_row, column=3, padx=0, pady=5, sticky="ew")

        # Notizen
        notes_frame = ctk.CTkFrame(self, fg_color="transparent")
        notes_frame.pack(pady=(0, 4), padx=20, fill="x")
        ctk.CTkLabel(notes_frame, text="Notizen:").pack(anchor="w")
        self.notes_textbox = ctk.CTkTextbox(notes_frame, height=70)
        self.notes_textbox.pack(fill="x", expand=False)

        # Material-Verknüpfung
        mat_frame = ctk.CTkFrame(self, fg_color="transparent")
        mat_frame.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(
            mat_frame,
            text="Zugehöriges Material (Auswahl hinzufügen / entfernen):",
        ).pack(anchor="w", padx=5, pady=(0, 4))

        self.search_mat_entry = ctk.CTkEntry(
            mat_frame, placeholder_text="Verfügbares Material filtern…"
        )
        self.search_mat_entry.pack(fill="x", padx=5, pady=(0, 8))
        self.search_mat_entry.bind("<KeyRelease>", self._filter_checkboxes)

        self.scroll_frame = ctk.CTkScrollableFrame(mat_frame)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.material_widgets: list  = []
        self.material_vars:    dict  = {}

        linked_ids   = get_linked_material_ids_for_device(self.device_id) if is_editing else []
        all_materials = get_all_materials_db("Alle anzeigen") or []

        for mat in all_materials:
            mat_id  = mat["material_id"]
            name    = mat.get("name", "N/A")
            m_type  = mat.get("type") or ""
            manu    = mat.get("manufacturer") or ""
            stock   = mat.get("stock_quantity", 0)
            ean     = mat.get("ean_code") or "-"
            inv_num = mat.get("inventory_number") or "-"
            status  = mat.get("status") or "-"

            parts = [name]
            if m_type and m_type != "-": parts.append(f"({m_type})")
            if manu   and manu   != "-": parts.append(f"– {manu}")
            parts.append(f"[Status: {status}, Best: {stock}, EAN: {ean}, Inv: {inv_num}, ID: {mat_id}]")
            cb_text = " ".join(parts)

            search_text = (
                f"{name} {m_type} {manu} {mat.get('color','') or ''} "
                f"{ean} {inv_num} {status} {mat_id}"
            ).lower()

            var = ctk.StringVar(value="on" if mat_id in linked_ids else "off")
            cb  = ctk.CTkCheckBox(
                self.scroll_frame, text=cb_text,
                variable=var, onvalue="on", offvalue="off",
            )
            self.material_widgets.append({"widget": cb, "search_text": search_text})
            self.material_vars[mat_id] = var

        if not all_materials:
            ctk.CTkLabel(self.scroll_frame, text="Kein Material im Inventar vorhanden.").pack()

        self._filter_checkboxes()

        # Speichern-Button
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20, padx=20, fill="x")
        ctk.CTkButton(btn_frame, text="Speichern", command=self._save).pack()

    def _fill_fields(self, data: dict):
        mapping = {
            "Typ:":               ("device_type",    ""),
            "Modell:":            ("model",           ""),
            "Hersteller:":        ("manufacturer",    ""),
            "Anschaffungsdatum:": ("purchase_date",   ""),
            "Standort:":          ("location",        ""),
            "Mitarbeiter:":       ("employee_name",   ""),
            "Computername:":      ("computer_name",   ""),
            "IP-Adresse:":        ("ip_address",      ""),
            "Seriennummer:":      ("serial_number",   ""),
            "Inventarnummer:":    ("inventory_number",""),
            "EAN-Code:":          ("ean_code",        ""),
            "Rechnungsnummer:":   ("invoice_number",  ""),
            "Händler:":           ("vendor",          ""),
            "Lieferscheinnummer:":("delivery_note",   ""),
            "Auftragsnummer:":    ("order_number",           ""),
            "Kaufpreis (€):":    ("purchase_price",          ""),
            "Garantiedatum:":    ("warranty_date",           ""),
            "Nächste Wartung:":  ("next_maintenance_date",   ""),
        }
        for label, (db_key, fallback) in mapping.items():
            if label in self.entries:
                self.entries[label].insert(0, str(data.get(db_key, fallback) or ""))
        self.status_var.set(data.get("status", DEFAULT_ASSET_STATUS))
        self.notes_textbox.delete("1.0", "end")
        self.notes_textbox.insert("1.0", data.get("notes", "") or "")

    # ------------------------------------------------------------------
    # Material-Filter
    # ------------------------------------------------------------------

    def _filter_checkboxes(self, event=None):
        term = self.search_mat_entry.get().lower().strip()
        for item in self.material_widgets:
            if item["widget"].winfo_exists():
                item["widget"].pack_forget()

        any_visible = False
        for item in self.material_widgets:
            w = item["widget"]
            if w.winfo_exists():
                if not term or term in item["search_text"]:
                    w.pack(anchor="w", pady=2, fill="x")
                    any_visible = True

        # Kein-Treffer-Label
        if not any_visible and term:
            if not hasattr(self, "_no_results_lbl"):
                self._no_results_lbl = ctk.CTkLabel(
                    self.scroll_frame, text="Keine Treffer für die Suche."
                )
            lbl = self._no_results_lbl
            if lbl.winfo_exists() and not lbl.winfo_ismapped():
                lbl.pack(pady=10)
        elif hasattr(self, "_no_results_lbl"):
            lbl = self._no_results_lbl
            if lbl.winfo_exists() and lbl.winfo_ismapped():
                lbl.pack_forget()

    # ------------------------------------------------------------------
    # Speichern
    # ------------------------------------------------------------------

    def _save(self):
        g = self.entries  # Abkürzung

        dev_type     = g["Typ:"].get().strip()            or "-"
        model        = g["Modell:"].get().strip()
        manufacturer = g["Hersteller:"].get().strip()     or "-"
        p_date_raw   = g["Anschaffungsdatum:"].get().strip()
        p_date       = p_date_raw                         or "-"
        loc          = g["Standort:"].get().strip()       or "-"
        emp_raw      = g["Mitarbeiter:"].get().strip()
        comp_name    = g["Computername:"].get().strip()   or "-"
        ip_address   = g["IP-Adresse:"].get().strip()    or "-"
        serial       = g["Seriennummer:"].get().strip()   or "-"
        inv_num      = g["Inventarnummer:"].get().strip() or None
        ean_code     = g["EAN-Code:"].get().strip()       or None
        invoice_num  = g["Rechnungsnummer:"].get().strip()or None
        vendor       = g["Händler:"].get().strip()        or None
        delivery     = g["Lieferscheinnummer:"].get().strip() or None
        order_num    = g["Auftragsnummer:"].get().strip() or None
        status       = self.status_var.get()
        emp_name     = emp_raw if emp_raw and emp_raw != "-" else None
        notes        = self.notes_textbox.get("1.0", "end").strip() or None
        price_raw    = g["Kaufpreis (€):"].get().strip()
        if price_raw:
            try:
                purchase_price = float(price_raw.replace(",", "."))
                if purchase_price < 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning(
                    "Ungültige Eingabe",
                    "Kaufpreis muss eine gültige positive Zahl sein (z. B. 1299.99).",
                    parent=self,
                )
                self.entries["Kaufpreis (€):"].focus()
                return
        else:
            purchase_price = None

        if not model:
            messagebox.showwarning(
                "Eingabe fehlt",
                "Bitte geben Sie eine Modellbezeichnung ein (Pflichtfeld).",
                parent=self,
            )
            self.entries["Modell:"].focus()
            return

        if p_date_raw and p_date != "-" and not validate_date(p_date_raw):
            self.entries["Anschaffungsdatum:"].focus()
            return

        warranty_raw = g["Garantiedatum:"].get().strip()
        if warranty_raw and not validate_date(warranty_raw):
            self.entries["Garantiedatum:"].focus()
            return
        warranty_date = warranty_raw or None

        maint_raw = g["Nächste Wartung:"].get().strip()
        if maint_raw and not validate_date(maint_raw):
            self.entries["Nächste Wartung:"].focus()
            return
        next_maintenance_date = maint_raw or None

        selected_mat_ids = [
            mid for mid, var in self.material_vars.items() if var.get() == "on"
        ]

        try:
            if self.device_data:
                success = update_device_db(
                    self.device_id, dev_type, model, manufacturer, p_date,
                    loc, emp_name, comp_name, ip_address, serial,
                    inv_num, ean_code, status, invoice_num, vendor, delivery, order_num,
                    notes, purchase_price, warranty_date, next_maintenance_date,
                )
                msg = "Gerät erfolgreich aktualisiert."
            else:
                success = add_device_db(
                    self.device_id, dev_type, model, manufacturer, p_date,
                    loc, emp_name, comp_name, ip_address, serial,
                    inv_num, ean_code, status, invoice_num, vendor, delivery, order_num,
                    notes, purchase_price, warranty_date, next_maintenance_date,
                )
                msg = f"Gerät '{model}' erfolgreich hinzugefügt."

            if not success:
                messagebox.showerror(
                    "Fehler",
                    "Gerät konnte nicht gespeichert werden "
                    "(evtl. Inventarnummer bereits vergeben).",
                    parent=self,
                )
                return

            # Audit-Log
            if self.device_data:
                old = self.device_data
                field_pairs = [
                    ("device_type", dev_type), ("model", model),
                    ("manufacturer", manufacturer), ("purchase_date", p_date),
                    ("location", loc), ("employee_name", emp_name),
                    ("computer_name", comp_name), ("ip_address", ip_address),
                    ("serial_number", serial), ("inventory_number", inv_num),
                    ("ean_code", ean_code), ("status", status),
                    ("invoice_number", invoice_num), ("vendor", vendor),
                    ("delivery_note", delivery), ("order_number", order_num),
                    ("notes", notes), ("purchase_price", purchase_price),
                    ("warranty_date", warranty_date),
                    ("next_maintenance_date", next_maintenance_date),
                ]
                for field, new_val in field_pairs:
                    old_val = str(old.get(field, "") or "")
                    new_str = str(new_val or "")
                    if old_val != new_str:
                        log_audit_db("device", self.device_id, "EDIT",
                                     field, old_val, new_str)
            else:
                log_audit_db("device", self.device_id, "ADD", new_value=model)

            link_ok = link_materials_to_device_db(self.device_id, selected_mat_ids)
            if not link_ok:
                messagebox.showwarning(
                    "Warnung",
                    "Gerät gespeichert, aber Materialverknüpfungen konnten nicht "
                    "vollständig aktualisiert werden.",
                    parent=self,
                )

            messagebox.showinfo("Erfolg", msg, parent=self)
            self.parent_app.refresh_device_list()
            if hasattr(self.parent_app, "refresh_material_list"):
                self.parent_app.refresh_material_list()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Fehler", f"Unerwarteter Fehler:\n{e}", parent=self)
            print(f"[device_dialog] Fehler beim Speichern: {e}")
