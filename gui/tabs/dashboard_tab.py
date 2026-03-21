#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui/tabs/dashboard_tab.py – Dashboard-Tab mit Statistiken und Diagrammen.
"""

import tkinter as tk
import tkinter.ttk as ttk
from datetime import date, timedelta

import customtkinter as ctk

from database import (
    get_dashboard_stats_db,
    get_devices_by_status_db,
    get_devices_by_location_db,
    get_expiring_devices_db,
)

# Statusfarben für Pie-Chart (passend zu den App-Farben)
_STATUS_COLORS = {
    "Lagernd":        "#81C784",
    "Im Einsatz":     "#64B5F6",
    "Lagernd & Im Einsatz": "#4DB6AC",
    "Defekt/RMA":     "#E57373",
    "Ausgemustert":   "#B0BEC5",
}
_FALLBACK_COLORS = ["#90CAF9", "#A5D6A7", "#FFCC80", "#F48FB1",
                    "#CE93D8", "#80DEEA", "#BCAAA4", "#EF9A9A"]


class DashboardTab:
    """Baut den Dashboard-Tab innerhalb des übergebenen CTkFrame auf."""

    def __init__(self, parent_frame, parent_app):
        self.parent_frame = parent_frame
        self.parent_app   = parent_app

        # Referenzen auf Label-Widgets der Stat-Cards
        self._stat_labels: dict[str, ctk.CTkLabel] = {}

        # Matplotlib verfügbar?
        self._matplotlib_ok = self._check_matplotlib()

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # Matplotlib-Check
    # ------------------------------------------------------------------

    @staticmethod
    def _check_matplotlib() -> bool:
        try:
            import matplotlib  # noqa: F401
            return True
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------

    def _build_ui(self):
        f = self.parent_frame

        # Refresh-Button (oben rechts)
        top_bar = ctk.CTkFrame(f, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkButton(top_bar, text="🔄 Aktualisieren",
                      width=140, command=self.refresh).pack(side="right")

        # Stat-Cards
        cards_frame = ctk.CTkFrame(f, fg_color="transparent")
        cards_frame.pack(fill="x", padx=10, pady=(8, 0))
        cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="cards")

        card_defs = [
            ("device_count",    "📦", "Geräte"),
            ("material_count",  "📋", "Material"),
            ("total_value",     "💶", "Gesamtwert (€)"),
            ("maintenance_due", "⚠",  "Wartung fällig"),
        ]
        for col, (key, icon, label) in enumerate(card_defs):
            card = ctk.CTkFrame(cards_frame, border_width=1, corner_radius=8)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="ew")
            ctk.CTkLabel(card, text=icon,
                         font=ctk.CTkFont(size=20)).pack(pady=(10, 0))
            val_lbl = ctk.CTkLabel(card, text="–",
                                   font=ctk.CTkFont(size=26, weight="bold"))
            val_lbl.pack()
            ctk.CTkLabel(card, text=label,
                         font=ctk.CTkFont(size=11)).pack(pady=(0, 10))
            self._stat_labels[key] = val_lbl

        # Charts-Bereich
        charts_frame = ctk.CTkFrame(f, fg_color="transparent")
        charts_frame.pack(fill="both", expand=False, padx=10, pady=(8, 0))
        charts_frame.grid_columnconfigure(0, weight=1)
        charts_frame.grid_columnconfigure(1, weight=1)

        self._pie_frame = ctk.CTkFrame(charts_frame, border_width=1, corner_radius=8)
        self._pie_frame.grid(row=0, column=0, padx=(0, 4), pady=4, sticky="nsew")

        self._bar_frame = ctk.CTkFrame(charts_frame, border_width=1, corner_radius=8)
        self._bar_frame.grid(row=0, column=1, padx=(4, 0), pady=4, sticky="nsew")

        ctk.CTkLabel(self._pie_frame,
                     text="Geräte nach Status",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(6, 0))
        ctk.CTkLabel(self._bar_frame,
                     text="Top-5 Standorte",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(6, 0))

        # Platzhalter für Chart-Canvas
        self._pie_canvas_widget = None
        self._bar_canvas_widget = None

        if not self._matplotlib_ok:
            for frm in (self._pie_frame, self._bar_frame):
                ctk.CTkLabel(frm,
                             text="matplotlib nicht installiert.\nBitte ausführen:\npip install matplotlib",
                             text_color="gray").pack(pady=20)

        # Ablauf-Tabelle
        table_label = ctk.CTkLabel(f,
                                   text="Ablaufende / überfällige Garantien & Wartungen",
                                   font=ctk.CTkFont(size=12, weight="bold"))
        table_label.pack(anchor="w", padx=14, pady=(8, 2))

        table_frame = ctk.CTkFrame(f, border_width=1, corner_radius=8)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ("Modell", "Hersteller", "Standort", "Mitarbeiter",
                "Garantie", "Nächste Wartung", "Status")
        self._exp_tree = ttk.Treeview(table_frame, columns=cols,
                                      show="headings", selectmode="browse", height=6)
        widths = {
            "Modell": 140, "Hersteller": 110, "Standort": 110, "Mitarbeiter": 110,
            "Garantie": 100, "Nächste Wartung": 120, "Status": 100,
        }
        for col in cols:
            self._exp_tree.heading(col, text=col, anchor="w")
            self._exp_tree.column(col, width=widths.get(col, 100),
                                  anchor="w", stretch=tk.YES)

        self._exp_tree.tag_configure("expired", background="#FFCCCC")
        self._exp_tree.tag_configure("warning", background="#FFE0B2")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",
                            command=self._exp_tree.yview)
        vsb.pack(side="right", fill="y")
        self._exp_tree.configure(yscrollcommand=vsb.set)
        self._exp_tree.pack(expand=True, fill="both")

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def refresh(self):
        """Lädt alle Dashboard-Daten neu und aktualisiert alle Widgets."""
        self._refresh_stat_cards()
        self._refresh_charts()
        self._refresh_expiring_table()

    def _refresh_stat_cards(self):
        stats = get_dashboard_stats_db()
        self._stat_labels["device_count"].configure(
            text=str(stats.get("device_count", 0))
        )
        self._stat_labels["material_count"].configure(
            text=str(stats.get("material_count", 0))
        )
        total_val = stats.get("total_value", 0.0)
        self._stat_labels["total_value"].configure(
            text=f"{total_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        maint = stats.get("maintenance_due", 0)
        self._stat_labels["maintenance_due"].configure(text=str(maint))
        # Farbe: rot wenn > 0
        color = "#E57373" if maint > 0 else ctk.ThemeManager.theme.get(
            "CTkLabel", {}).get("text_color", ["#1A1A1A", "#DCE4EE"]
        )[0 if ctk.get_appearance_mode() == "Light" else 1]
        self._stat_labels["maintenance_due"].configure(text_color=color)

    def _refresh_charts(self):
        if not self._matplotlib_ok:
            return

        import matplotlib
        matplotlib.use("TkAgg")
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        # --- Pie-Chart ---
        status_data = get_devices_by_status_db()
        if self._pie_canvas_widget:
            self._pie_canvas_widget.destroy()
            self._pie_canvas_widget = None

        fig_pie = Figure(figsize=(3.6, 2.8), dpi=90)
        fig_pie.patch.set_facecolor("none")
        ax_pie = fig_pie.add_subplot(111)
        ax_pie.set_facecolor("none")

        if status_data:
            labels = [r.get("status", "") or "–" for r in status_data]
            sizes  = [r.get("count", 0) for r in status_data]
            colors = [_STATUS_COLORS.get(lbl, _FALLBACK_COLORS[i % len(_FALLBACK_COLORS)])
                      for i, lbl in enumerate(labels)]
            wedges, texts, autotexts = ax_pie.pie(
                sizes, labels=None, colors=colors,
                autopct="%1.0f%%", startangle=90,
                pctdistance=0.75,
                wedgeprops={"linewidth": 0.5, "edgecolor": "white"},
            )
            for at in autotexts:
                at.set_fontsize(8)
            ax_pie.legend(wedges, labels, loc="center left",
                          bbox_to_anchor=(1.0, 0.5), fontsize=8, frameon=False)
        else:
            ax_pie.text(0.5, 0.5, "Keine Daten", ha="center", va="center",
                        transform=ax_pie.transAxes, color="gray")

        fig_pie.tight_layout(pad=0.5)
        canvas_pie = FigureCanvasTkAgg(fig_pie, master=self._pie_frame)
        self._pie_canvas_widget = canvas_pie.get_tk_widget()
        self._pie_canvas_widget.pack(fill="both", expand=True, padx=4, pady=(0, 6))
        canvas_pie.draw()

        # --- Bar-Chart ---
        location_data = get_devices_by_location_db(limit=5)
        if self._bar_canvas_widget:
            self._bar_canvas_widget.destroy()
            self._bar_canvas_widget = None

        fig_bar = Figure(figsize=(3.6, 2.8), dpi=90)
        fig_bar.patch.set_facecolor("none")
        ax_bar = fig_bar.add_subplot(111)
        ax_bar.set_facecolor("none")

        if location_data:
            locs   = [r.get("location", "") or "–" for r in location_data]
            counts = [r.get("count", 0) for r in location_data]
            bars = ax_bar.barh(locs, counts, color="#64B5F6", edgecolor="white",
                               linewidth=0.5)
            ax_bar.bar_label(bars, padding=3, fontsize=8)
            ax_bar.set_xlabel("Geräte", fontsize=8)
            ax_bar.tick_params(axis="both", labelsize=8)
            ax_bar.invert_yaxis()
            ax_bar.spines[["top", "right"]].set_visible(False)
        else:
            ax_bar.text(0.5, 0.5, "Keine Daten", ha="center", va="center",
                        transform=ax_bar.transAxes, color="gray")

        fig_bar.tight_layout(pad=0.5)
        canvas_bar = FigureCanvasTkAgg(fig_bar, master=self._bar_frame)
        self._bar_canvas_widget = canvas_bar.get_tk_widget()
        self._bar_canvas_widget.pack(fill="both", expand=True, padx=4, pady=(0, 6))
        canvas_bar.draw()

    def _refresh_expiring_table(self):
        self._exp_tree.delete(*self._exp_tree.get_children())
        devices = get_expiring_devices_db(days=30)
        today     = date.today()
        threshold = today + timedelta(days=30)

        for dev in devices:
            warranty = dev.get("warranty_date") or ""
            maint    = dev.get("next_maintenance_date") or ""
            tag = ""
            for dval in (warranty, maint):
                if dval:
                    try:
                        d = date.fromisoformat(dval)
                        if d < today:
                            tag = "expired"
                            break
                        elif d <= threshold and tag != "expired":
                            tag = "warning"
                    except ValueError:
                        pass

            self._exp_tree.insert("", "end", tags=(tag,) if tag else (), values=(
                dev.get("model", "") or "",
                dev.get("manufacturer", "") or "",
                dev.get("location", "") or "",
                dev.get("employee_name", "") or "",
                warranty,
                maint,
                dev.get("status", "") or "",
            ))
