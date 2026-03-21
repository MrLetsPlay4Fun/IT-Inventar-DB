#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui/app.py – Hauptfenster der IT Inventar Verwaltung.

Enthält die App-Klasse mit:
  • Tab "Geräte"   – Treeview, Suche, Filter, CRUD-Buttons
  • Tab "Material" – Treeview, Suche, Filter, CRUD-Buttons, Lagerbestand-Popup
  • ⚙-Button       – öffnet den Einstellungsdialog zum Ändern des DB-Pfads
"""

import sys
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
from datetime import date, timedelta
import customtkinter as ctk

import config
from database import (
    setup_database,
    get_all_devices_db,
    get_all_materials_db,
    search_devices_db,
    search_materials_db,
    get_device_by_id_db,
    get_material_by_id_db,
    get_material_by_barcode_db,
    get_associated_materials_for_device_db,
    delete_device_db,
    delete_material_db,
    update_material_stock_db,
    log_audit_db,
)
from gui.dialogs.device_dialog      import AddEditDeviceWindow
from gui.dialogs.material_dialog    import AddEditMaterialWindow
from gui.dialogs.association_dialogs import (
    ShowAssociatedDevicesWindow,
    ShowAssociatedMaterialsWindow,
)
from gui.dialogs.settings_dialog    import DBSettingsDialog
from gui.tabs.dashboard_tab         import DashboardTab


class App(ctk.CTk):
    """Hauptanwendungsklasse der IT Inventar Verwaltung."""

    def __init__(self):
        super().__init__()

        # Popup-Zustand
        self.popup_window                 = None
        self.popup_material_tree          = None
        self.popup_full_material_list     = []
        self.popup_selected_material_label = None
        self.popup_stock_change_entry     = None
        self.popup_stock_book_button      = None
        self.selected_popup_material_id   = None
        self.selected_popup_current_stock = None
        self.popup_search_barcode_entry   = None

        # Filter-Variablen
        self.device_status_filter_var   = ctk.StringVar(value=config.DEFAULT_STATUS_FILTER)
        self.material_status_filter_var = ctk.StringVar(value=config.DEFAULT_STATUS_FILTER)

        # Fenster
        self.title(f"IT Inventar Verwaltung v{config.APP_VERSION}")
        self.geometry("1420x720")
        self.minsize(1000, 600)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        print("[App] Initialisiere Datenbank …")
        try:
            setup_database()
            print(f"[App] Datenbank: {config.get_db_file()}")
        except SystemExit as e:
            print(f"[App] Kritischer DB-Fehler: {e}")
            self.after(100, self.destroy)
            return

        self._setup_treeview_style()
        self._build_ui()

        self.refresh_device_list()
        self.refresh_material_list()
        print("[App] Initialisierung abgeschlossen.")

    # ==================================================================
    # UI-Aufbau
    # ==================================================================

    def _build_ui(self):
        # Titelzeile mit Einstellungs-Button
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 0))

        ctk.CTkLabel(
            header,
            text=f"IT Inventar Verwaltung  v{config.APP_VERSION}",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="⚙  Einstellungen",
            width=160,
            command=self._open_settings,
        ).pack(side="right")

        ctk.CTkButton(
            header,
            text="📋 Audit-Log",
            width=110,
            command=self._open_audit_log,
        ).pack(side="right", padx=5)

        # Tabs
        self.tab_view = ctk.CTkTabview(self, anchor="nw")
        self.tab_view.pack(expand=True, fill="both", padx=10, pady=(4, 10))
        self.tab_dashboard = self.tab_view.add("📊 Dashboard")
        self.tab_devices   = self.tab_view.add("Geräte")
        self.tab_materials = self.tab_view.add("Material")
        self.tab_view.set("Geräte")
        self.tab_view.configure(command=self._on_tab_change)

        self._setup_devices_tab()
        self._setup_materials_tab()
        self.dashboard_tab = DashboardTab(self.tab_dashboard, parent_app=self)

    def _setup_treeview_style(self):
        style = ttk.Style()
        try:
            if sys.platform == "win32":   style.theme_use("vista")
            elif sys.platform == "darwin": style.theme_use("aqua")
            else:                          style.theme_use("clam")
        except tk.TclError:
            style.theme_use("default")

        mode = ctk.get_appearance_mode()
        try:
            theme = ctk.ThemeManager.theme
            idx   = 1 if mode == "Dark" else 0
            def c(cat, prop): return theme[cat][prop][idx]
            bg     = c("CTkFrame",  "fg_color")
            fg     = c("CTkLabel",  "text_color")
            sel_bg = c("CTkButton", "fg_color")
            sel_fg = c("CTkButton", "text_color")
            hdr_bg = c("CTkFrame",  "border_color")
        except (KeyError, TypeError):
            if mode == "Dark":
                bg, fg, sel_bg, sel_fg, hdr_bg = "#2B2B2B","#DCE4EE","#1F6AA5","#FFFFFF","#565B5E"
            else:
                bg, fg, sel_bg, sel_fg, hdr_bg = "#EBEBEB","#1A1A1A","#3B8ED0","#FFFFFF","#D6D6D6"

        style.configure("Treeview",
                        background=bg, foreground=fg, fieldbackground=bg,
                        rowheight=25, font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                        background=hdr_bg, foreground="black",
                        font=("Segoe UI", 10, "bold"), relief="flat", padding=(5, 5))
        style.map("Treeview",
                  background=[("selected", sel_bg)],
                  foreground=[("selected", sel_fg)])
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    # ------------------------------------------------------------------
    # Geräte-Tab
    # ------------------------------------------------------------------

    def _setup_devices_tab(self):
        tab = self.tab_devices

        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.pack(fill="x", pady=5, padx=5)

        ctk.CTkButton(ctrl, text="Gerät hinzufügen",  command=self.open_add_device_window).pack(side="left", padx=5)
        self.edit_device_btn   = ctk.CTkButton(ctrl, text="Gerät bearbeiten",  command=self.open_edit_device_window, state="disabled")
        self.edit_device_btn.pack(side="left", padx=5)
        self.del_device_btn    = ctk.CTkButton(ctrl, text="Gerät löschen",     command=self.delete_selected_device,
                                               state="disabled", fg_color="#D32F2F", hover_color="#B71C1C")
        self.del_device_btn.pack(side="left", padx=5)
        self.show_mat_btn      = ctk.CTkButton(ctrl, text="Zugeh. Material…",  command=self.show_associated_materials, state="disabled")
        self.show_mat_btn.pack(side="left", padx=5)

        # Rechte Seite: Status-Filter + Suche
        ctk.CTkLabel(ctrl, text="Status-Filter:").pack(side="right", padx=(20, 5))
        ctk.CTkOptionMenu(
            ctrl,
            variable=self.device_status_filter_var,
            values=config.STATUS_OPTIONS,
            command=lambda s: self.refresh_device_list(status_filter=s),
            width=150,
        ).pack(side="right", padx=5)
        ctk.CTkButton(ctrl, text="✕", width=30, command=self.reset_device_search).pack(side="right", padx=(5, 0))
        self.device_search_entry = ctk.CTkEntry(
            ctrl,
            placeholder_text="Gerät suchen (Modell, SN, MA, Ort, IP, Rechnungsnr, Händler …)",
            width=340,
        )
        self.device_search_entry.pack(side="right", padx=0, fill="x", expand=True)
        self.device_search_entry.bind("<Return>",    lambda e: self.search_devices())
        self.device_search_entry.bind("<KeyRelease>", lambda e: self.search_devices())

        # Treeview
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.pack(expand=True, fill="both", padx=5, pady=(0, 5))

        cols = ("ID", "Typ", "Modell", "Hersteller", "Anschaffung", "Garantie",
                "Nächste Wartung", "Standort", "Mitarbeiter", "Computer", "IP-Adresse",
                "Seriennr.", "Inventarnr.", "EAN-Code", "Rechnungsnr.", "Händler",
                "Lieferscheinnr.", "Auftragsnr.", "Status")
        self.device_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        widths = {
            "ID": 80, "Typ": 80, "Modell": 130, "Hersteller": 90, "Anschaffung": 80,
            "Garantie": 90, "Nächste Wartung": 110,
            "Standort": 90, "Mitarbeiter": 90, "Computer": 90, "IP-Adresse": 100,
            "Seriennr.": 90, "Inventarnr.": 90, "EAN-Code": 90,
            "Rechnungsnr.": 100, "Händler": 100, "Lieferscheinnr.": 110,
            "Auftragsnr.": 100, "Status": 90,
        }
        anchors = {"Anschaffung": "center", "Garantie": "center", "Nächste Wartung": "center",
                   "ID": "w", "Status": "center", "IP-Adresse": "w"}

        for col in cols:
            self.device_tree.heading(col, text=col, anchor="w")
            self.device_tree.column(col, width=widths.get(col, 80),
                                    anchor=anchors.get(col, "w"), stretch=tk.YES)

        self.device_tree.tag_configure("expired", background="#FFCCCC")
        self.device_tree.tag_configure("warning", background="#FFE0B2")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.device_tree.yview)
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",  command=self.device_tree.xview)
        hsb.pack(side="bottom", fill="x")
        self.device_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.device_tree.pack(expand=True, fill="both")

        self.device_tree.bind("<<TreeviewSelect>>", self.on_device_select)
        self.device_tree.bind("<Double-1>",          self._on_device_double_click)

    # ------------------------------------------------------------------
    # Material-Tab
    # ------------------------------------------------------------------

    def _setup_materials_tab(self):
        tab = self.tab_materials

        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.pack(fill="x", pady=5, padx=5)

        ctk.CTkButton(ctrl, text="Material hinzufügen", command=self.open_add_material_window).pack(side="left", padx=5)
        self.edit_mat_btn = ctk.CTkButton(ctrl, text="Material bearbeiten", command=self.open_edit_material_window, state="disabled")
        self.edit_mat_btn.pack(side="left", padx=5)
        self.del_mat_btn  = ctk.CTkButton(ctrl, text="Material löschen",   command=self.delete_selected_material,
                                          state="disabled", fg_color="#D32F2F", hover_color="#B71C1C")
        self.del_mat_btn.pack(side="left", padx=5)
        self.show_dev_btn = ctk.CTkButton(ctrl, text="Zugewiesene Geräte anzeigen",
                                          command=self.show_assigned_devices, state="disabled")
        self.show_dev_btn.pack(side="left", padx=5)

        ctk.CTkLabel(ctrl, text="Status-Filter:").pack(side="right", padx=(20, 5))
        ctk.CTkOptionMenu(
            ctrl,
            variable=self.material_status_filter_var,
            values=config.STATUS_OPTIONS,
            command=lambda s: self.refresh_material_list(status_filter=s),
            width=150,
        ).pack(side="right", padx=5)
        ctk.CTkButton(ctrl, text="✕", width=30, command=self.reset_material_search).pack(side="right", padx=(5, 0))
        self.material_search_entry = ctk.CTkEntry(
            ctrl,
            placeholder_text="Material suchen (Name, Typ, EAN, Inventarnr …)",
            width=300,
        )
        self.material_search_entry.pack(side="right", padx=0, fill="x", expand=True)
        self.material_search_entry.bind("<Return>",    lambda e: self.search_materials())
        self.material_search_entry.bind("<KeyRelease>", lambda e: self.search_materials())

        # Treeview
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.pack(expand=True, fill="both", padx=5, pady=(0, 5))

        cols = ("ID", "Name", "Typ", "Hersteller", "Farbe", "Lagerbestand", "EAN-Code", "Inventarnummer", "Status")
        self.material_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        widths  = {"ID": 90, "Name": 160, "Typ": 100, "Hersteller": 100, "Farbe": 70,
                   "Lagerbestand": 90, "EAN-Code": 100, "Inventarnummer": 100, "Status": 90}
        anchors = {"Lagerbestand": "center", "Status": "center"}

        for col in cols:
            self.material_tree.heading(col, text=col, anchor="w")
            self.material_tree.column(col, width=widths.get(col, 90),
                                      anchor=anchors.get(col, "w"), stretch=tk.YES)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.material_tree.yview)
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",  command=self.material_tree.xview)
        hsb.pack(side="bottom", fill="x")
        self.material_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.material_tree.pack(expand=True, fill="both")

        self.material_tree.bind("<<TreeviewSelect>>", self.on_material_select)
        self.material_tree.bind("<Double-1>",          self._on_material_double_click)

    # ==================================================================
    # Einstellungen
    # ==================================================================

    def _on_tab_change(self):
        if self.tab_view.get() == "📊 Dashboard":
            self.dashboard_tab.refresh()

    def _open_audit_log(self):
        from gui.dialogs.audit_log_dialog import AuditLogDialog
        AuditLogDialog(self)

    def _open_settings(self):
        """Öffnet den DB-Pfad-Einstellungsdialog."""
        dlg = DBSettingsDialog(parent=self, startup_mode=False)
        self.wait_window(dlg)
        if dlg.result_ok:
            # Datenbank neu initialisieren mit neuem Pfad
            try:
                setup_database()
                self.refresh_device_list()
                self.refresh_material_list()
                messagebox.showinfo(
                    "Einstellungen gespeichert",
                    f"Datenbank wird jetzt verwendet aus:\n{config.get_db_file()}",
                )
            except SystemExit:
                messagebox.showerror(
                    "Fehler",
                    "Der neue Datenbankpfad konnte nicht initialisiert werden.",
                )

    # ==================================================================
    # Hilfsmethoden
    # ==================================================================

    def get_selected_item_id(self, treeview):
        try:
            sel = treeview.selection()
            if sel:
                item = treeview.item(sel[0])
                if item and item.get("values"):
                    return item["values"][0]
        except Exception as e:
            print(f"[App] Fehler bei Treeview-Auswahl: {e}")
        return None

    # ==================================================================
    # Geräte-Methoden
    # ==================================================================

    def on_device_select(self, event=None):
        if not hasattr(self, "edit_device_btn") or not self.edit_device_btn.winfo_exists():
            return
        state = "normal" if self.get_selected_item_id(self.device_tree) else "disabled"
        self.edit_device_btn.configure(state=state)
        self.del_device_btn.configure(state=state)
        self.show_mat_btn.configure(state=state)

    def populate_device_tree(self, device_list):
        if self.device_tree.selection():
            self.device_tree.selection_remove(self.device_tree.selection())
        self.on_device_select()
        self.device_tree.delete(*self.device_tree.get_children())

        db_cols = (
            "device_id", "device_type", "model", "manufacturer", "purchase_date",
            "warranty_date", "next_maintenance_date",
            "location", "employee_name", "computer_name", "ip_address",
            "serial_number", "inventory_number", "ean_code",
            "invoice_number", "vendor", "delivery_note", "order_number", "status",
        )
        today     = date.today()
        threshold = today + timedelta(days=30)
        for dev in (device_list or []):
            tag = ""
            for date_field in ("warranty_date", "next_maintenance_date"):
                val = dev.get(date_field) or ""
                if val:
                    try:
                        d = date.fromisoformat(val)
                        if d < today:
                            tag = "expired"
                            break
                        elif d <= threshold and tag != "expired":
                            tag = "warning"
                    except ValueError:
                        pass
            self.device_tree.insert("", "end",
                                    values=[str(dev.get(c, "") or "") for c in db_cols],
                                    tags=(tag,) if tag else ())
        self.on_device_select()

    def refresh_device_list(self, status_filter=None):
        self.device_search_entry.delete(0, "end")
        ft = status_filter or self.device_status_filter_var.get()
        self.populate_device_tree(get_all_devices_db(ft) or [])

    def search_devices(self):
        term = self.device_search_entry.get().strip()
        ft   = self.device_status_filter_var.get()
        self.populate_device_tree(search_devices_db(term, ft) or [])

    def reset_device_search(self):
        self.device_search_entry.delete(0, "end")
        self.device_status_filter_var.set(config.DEFAULT_STATUS_FILTER)
        self.refresh_device_list()

    def open_add_device_window(self):
        AddEditDeviceWindow(self)

    def open_edit_device_window(self):
        selected_id = self.get_selected_item_id(self.device_tree)
        if selected_id:
            data = get_device_by_id_db(selected_id)
            if data:
                AddEditDeviceWindow(self, device_data=data)
            else:
                messagebox.showerror("Fehler",
                    f"Gerät (ID: {selected_id}) nicht mehr in der Datenbank.", parent=self)
                self.refresh_device_list()

    def _on_device_double_click(self, event):
        if self.device_tree.identify_row(event.y):
            self.open_edit_device_window()

    def delete_selected_device(self):
        selected_id = self.get_selected_item_id(self.device_tree)
        if not selected_id:
            return
        data  = get_device_by_id_db(selected_id)
        name  = data.get("model", selected_id) if data else selected_id
        if messagebox.askyesno(
            "Löschen bestätigen",
            f"Gerät '{name}' (ID: {selected_id}) wirklich löschen?\n\n"
            "ACHTUNG: Alle Materialverknüpfungen werden ebenfalls entfernt!",
            icon="warning", parent=self,
        ):
            if delete_device_db(selected_id) is True:
                log_audit_db("device", selected_id, "DELETE",
                             old_value=data.get("model", "") if data else "")
                messagebox.showinfo("Gelöscht", "Gerät erfolgreich gelöscht.", parent=self)
                self.refresh_device_list()
            else:
                messagebox.showerror("Fehler", "Gerät konnte nicht gelöscht werden.", parent=self)

    def show_associated_materials(self):
        selected_id = self.get_selected_item_id(self.device_tree)
        if selected_id:
            data = get_device_by_id_db(selected_id)
            if data:
                ShowAssociatedMaterialsWindow(self, selected_id, data.get("model", selected_id))
            else:
                messagebox.showerror("Fehler", "Gerät nicht in der Datenbank gefunden.", parent=self)

    # ==================================================================
    # Material-Methoden
    # ==================================================================

    def on_material_select(self, event=None):
        if not hasattr(self, "edit_mat_btn") or not self.edit_mat_btn.winfo_exists():
            return
        state = "normal" if self.get_selected_item_id(self.material_tree) else "disabled"
        self.edit_mat_btn.configure(state=state)
        self.del_mat_btn.configure(state=state)
        self.show_dev_btn.configure(state=state)

    def populate_material_tree(self, material_list):
        if self.material_tree.selection():
            self.material_tree.selection_remove(self.material_tree.selection())
        self.on_material_select()
        self.material_tree.delete(*self.material_tree.get_children())

        db_cols = ("material_id", "name", "type", "manufacturer", "color",
                   "stock_quantity", "ean_code", "inventory_number", "status")
        for mat in (material_list or []):
            self.material_tree.insert("", "end",
                                      values=[str(mat.get(c, "") or "") for c in db_cols])
        self.on_material_select()

    def refresh_material_list(self, status_filter=None):
        self.material_search_entry.delete(0, "end")
        ft = status_filter or self.material_status_filter_var.get()
        self.populate_material_tree(get_all_materials_db(ft) or [])

    def search_materials(self):
        term = self.material_search_entry.get().strip()
        ft   = self.material_status_filter_var.get()
        self.populate_material_tree(search_materials_db(term, ft) or [])

    def reset_material_search(self):
        self.material_search_entry.delete(0, "end")
        self.material_status_filter_var.set(config.DEFAULT_STATUS_FILTER)
        self.refresh_material_list()

    def open_add_material_window(self):
        AddEditMaterialWindow(self)

    def open_edit_material_window(self):
        selected_id = self.get_selected_item_id(self.material_tree)
        if selected_id:
            data = get_material_by_id_db(selected_id)
            if data:
                AddEditMaterialWindow(self, material_data=data)
            else:
                messagebox.showerror("Fehler",
                    f"Material (ID: {selected_id}) nicht mehr in der Datenbank.", parent=self)
                self.refresh_material_list()

    def _on_material_double_click(self, event):
        if self.material_tree.identify_row(event.y):
            self.open_edit_material_window()

    def delete_selected_material(self):
        selected_id = self.get_selected_item_id(self.material_tree)
        if not selected_id:
            return
        data = get_material_by_id_db(selected_id)
        name = data.get("name", selected_id) if data else selected_id
        if messagebox.askyesno(
            "Löschen bestätigen",
            f"Material '{name}' (ID: {selected_id}) wirklich löschen?\n\n"
            "ACHTUNG: Alle Geräteverknüpfungen werden ebenfalls entfernt!",
            icon="warning", parent=self,
        ):
            if delete_material_db(selected_id) is True:
                log_audit_db("material", selected_id, "DELETE",
                             old_value=data.get("name", "") if data else "")
                messagebox.showinfo("Gelöscht", "Material erfolgreich gelöscht.", parent=self)
                self.refresh_material_list()
            else:
                messagebox.showerror("Fehler", "Material konnte nicht gelöscht werden.", parent=self)

    def show_assigned_devices(self):
        selected_id = self.get_selected_item_id(self.material_tree)
        if selected_id:
            data = get_material_by_id_db(selected_id)
            if data:
                ShowAssociatedDevicesWindow(self, selected_id, data.get("name", selected_id))
            else:
                messagebox.showerror("Fehler", "Material nicht in der Datenbank gefunden.", parent=self)

    # ==================================================================
    # Lagerbestand-Popup (Barcode-Scan)
    # ==================================================================

    def _handle_barcode_scan_entry(self, event):
        barcode = self.popup_search_barcode_entry.get().strip()
        if not barcode:
            return

        mat_data = get_material_by_barcode_db(barcode)
        if not mat_data:
            messagebox.showwarning(
                "Nicht gefunden",
                f"Kein Material mit dem Code '{barcode}' gefunden.",
                parent=self.popup_window,
            )
            self.popup_search_barcode_entry.delete(0, "end")
            return

        mat_id        = mat_data.get("material_id")
        mat_name      = mat_data.get("name")
        current_stock = mat_data.get("stock_quantity", 0)

        self.selected_popup_material_id   = mat_id
        self.selected_popup_current_stock = current_stock
        self.popup_selected_material_label.configure(
            text=f"Scan: {mat_name} (Bestand: {current_stock})"
        )
        self.popup_stock_change_entry.configure(state="normal")
        self.popup_stock_change_entry.delete(0, "end")
        self.popup_stock_change_entry.insert(0, "-1")
        self.popup_stock_book_button.configure(state="normal")

        if event is not None and event.keysym == "Return":
            self.popup_window.after(50, lambda: self._handle_popup_stock_change(auto_scan=True))
        else:
            self.popup_stock_change_entry.focus()

    def _handle_popup_stock_change(self, auto_scan=False):
        if not self.selected_popup_material_id or self.selected_popup_current_stock is None:
            messagebox.showwarning(
                "Keine Auswahl",
                "Bitte wählen Sie zuerst ein Material aus oder scannen Sie.",
                parent=self.popup_window,
            )
            return

        change_str = self.popup_stock_change_entry.get().strip()
        if not change_str:
            messagebox.showwarning(
                "Leere Eingabe",
                "Bitte geben Sie eine Änderung (+/- Wert) oder den neuen Gesamtbestand ein.",
                parent=self.popup_window,
            )
            self.popup_stock_change_entry.focus()
            return

        try:
            latest = get_material_by_id_db(self.selected_popup_material_id)
            if not latest:
                messagebox.showerror(
                    "Fehler",
                    f"Material {self.selected_popup_material_id} nicht mehr gefunden!",
                    parent=self.popup_window,
                )
                return

            current = latest.get("stock_quantity", 0)
            if change_str.startswith(("+", "-")):
                new_stock = current + int(change_str)
            else:
                new_stock = int(change_str)

            if new_stock < 0:
                messagebox.showerror(
                    "Ungültiger Bestand",
                    f"Resultierender Lagerbestand ({new_stock}) darf nicht negativ sein.",
                    parent=self.popup_window,
                )
                self.popup_stock_change_entry.focus()
                return

            success = update_material_stock_db(self.selected_popup_material_id, new_stock)
            if success:
                if not auto_scan:
                    messagebox.showinfo(
                        "Gebucht",
                        f"Bestand für '{latest.get('name')}' auf {new_stock} aktualisiert.",
                        parent=self.popup_window,
                    )
                self.refresh_material_list()
                selected_dev_id = self.get_selected_item_id(self.device_tree)
                if selected_dev_id:
                    self.popup_full_material_list = (
                        get_associated_materials_for_device_db(selected_dev_id) or []
                    )
                    self._filter_popup_materials()
                self._clear_popup_selection()
                self.popup_search_barcode_entry.delete(0, "end")
                self.popup_search_barcode_entry.focus()
            else:
                messagebox.showerror(
                    "Fehler",
                    "Lagerbestand konnte nicht aktualisiert werden.",
                    parent=self.popup_window,
                )
                self.popup_stock_change_entry.focus()

        except ValueError:
            messagebox.showerror(
                "Ungültige Eingabe",
                f"'{change_str}' ist keine gültige Zahl oder Änderung (+/- Zahl).",
                parent=self.popup_window,
            )
            self.popup_stock_change_entry.focus()
        except Exception as e:
            messagebox.showerror("Fehler", f"Unerwarteter Fehler:\n{e}", parent=self.popup_window)
            print(f"[App] Fehler in _handle_popup_stock_change: {e}")

    def _populate_popup_material_tree(self, materials):
        if not hasattr(self, "popup_material_tree") or not self.popup_material_tree.winfo_exists():
            return
        self._clear_popup_selection()
        self.popup_material_tree.delete(*self.popup_material_tree.get_children())
        db_cols = ("material_id", "name", "type", "manufacturer", "color",
                   "stock_quantity", "ean_code", "inventory_number", "status")
        for mat in (materials or []):
            self.popup_material_tree.insert(
                "", "end",
                values=[str(mat.get(db_cols[i], "") or "") for i in range(len(db_cols))],
            )

    def _filter_popup_materials(self, event=None):
        if not hasattr(self, "popup_full_material_list"):
            return
        term     = self.popup_search_barcode_entry.get().lower().strip()
        filtered = []
        for mat in self.popup_full_material_list:
            text = " ".join(str(mat.get(k, "") or "") for k in
                            ("material_id", "name", "type", "manufacturer",
                             "color", "ean_code", "inventory_number", "status")).lower()
            if term in text:
                filtered.append(mat)
        self._populate_popup_material_tree(filtered)

    def _clear_popup_selection(self):
        if hasattr(self, "popup_material_tree") and self.popup_material_tree.winfo_exists():
            if self.popup_material_tree.selection():
                self.popup_material_tree.selection_remove(self.popup_material_tree.selection())
        if hasattr(self, "popup_selected_material_label") and self.popup_selected_material_label.winfo_exists():
            self.popup_selected_material_label.configure(text="Material aus Tabelle auswählen …")
        if hasattr(self, "popup_stock_change_entry") and self.popup_stock_change_entry.winfo_exists():
            self.popup_stock_change_entry.delete(0, "end")
            self.popup_stock_change_entry.configure(state="disabled")
        if hasattr(self, "popup_stock_book_button") and self.popup_stock_book_button.winfo_exists():
            self.popup_stock_book_button.configure(state="disabled")
        self.selected_popup_material_id   = None
        self.selected_popup_current_stock = None
