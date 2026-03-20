#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui/widgets.py – Wiederverwendbare benutzerdefinierte Widgets.

Enthält:
    AutocompleteEntry – CTkEntry mit Live-Vorschlägen als Dropdown.
"""

import tkinter as tk
import customtkinter as ctk


class AutocompleteEntry(ctk.CTkEntry):
    """
    CTkEntry-Erweiterung mit Autocomplete-Dropdown.

    Beim Tippen wird eine Vorschlagsliste angezeigt, die nach dem
    eingegebenen Präfix gefiltert wird. Navigation per Pfeiltasten
    und Auswahl per Enter oder Mausklick.
    """

    def __init__(self, master, suggestions_list: list, **kwargs):
        super().__init__(master, **kwargs)

        self.suggestions: list          = suggestions_list
        self.filtered_suggestions: list = []
        self._current_lb_selection: int = -1

        # ---------------------------------------------------------------
        # Dropdown-Fenster (unsichtbares Toplevel ohne Dekoration)
        # ---------------------------------------------------------------
        self.dropdown = tk.Toplevel(self)
        self.dropdown.withdraw()
        self.dropdown.overrideredirect(True)

        # Farben aus dem aktuellen CustomTkinter-Theme ableiten
        lb_bg, lb_fg, lb_sel_bg, lb_sel_fg, lb_border = self._resolve_colors()

        self.listbox = tk.Listbox(
            self.dropdown,
            background=lb_bg,
            foreground=lb_fg,
            selectbackground=lb_sel_bg,
            selectforeground=lb_sel_fg,
            highlightthickness=1,
            highlightcolor=lb_border,
            relief="flat",
            exportselection=False,
            height=5,
        )
        self.listbox.pack(fill="both", expand=True)

        # Events
        self.bind("<KeyRelease>",  self._on_keyrelease)
        self.bind("<FocusOut>",    self._on_focus_out)
        self.bind("<Down>",        self._on_down_key)
        self.bind("<Up>",          self._on_up_key)
        self.bind("<Return>",      self._on_enter_key)
        self.bind("<Escape>",      self.hide_dropdown)

        self.listbox.bind("<ButtonRelease-1>", self._on_listbox_select)
        self.listbox.bind("<FocusOut>",        self._on_focus_out)

    # ------------------------------------------------------------------
    # Farben
    # ------------------------------------------------------------------

    def _resolve_colors(self):
        """Ermittelt Dropdown-Farben passend zum aktuellen Theme."""
        try:
            mode        = ctk.get_appearance_mode()
            theme       = ctk.ThemeManager.theme
            idx         = 1 if mode == "Dark" else 0

            def color(cat, prop):
                return theme[cat][prop][idx]

            return (
                color("CTkFrame",  "fg_color"),
                color("CTkLabel",  "text_color"),
                color("CTkButton", "fg_color"),
                color("CTkButton", "text_color"),
                color("CTkButton", "fg_color"),
            )
        except Exception:
            dark = ctk.get_appearance_mode() == "Dark"
            if dark:
                return "#2B2B2B", "#DCE4EE", "#1F6AA5", "#FFFFFF", "#1F6AA5"
            return "#EBEBEB", "#1A1A1A", "#3B8ED0", "#FFFFFF", "#3B8ED0"

    # ------------------------------------------------------------------
    # Dropdown-Steuerung
    # ------------------------------------------------------------------

    def hide_dropdown(self, event=None):
        self.dropdown.withdraw()

    def _on_focus_out(self, event=None):
        self.after(100, self._check_focus)

    def _check_focus(self):
        try:
            focused = self.winfo_toplevel().focus_get()
            if focused not in (self.listbox, self):
                self.hide_dropdown()
        except Exception:
            self.hide_dropdown()

    def _on_keyrelease(self, event):
        if event.keysym in ("Down", "Up", "Return", "Escape", "Tab"):
            return
        text = self.get().lower()
        self.filtered_suggestions = (
            [s for s in self.suggestions if s.lower().startswith(text)] if text else []
        )
        if self.filtered_suggestions:
            self._update_listbox()
        else:
            self.hide_dropdown()

    def _update_listbox(self):
        self.listbox.delete(0, "end")
        for item in self.filtered_suggestions:
            self.listbox.insert("end", item)
        self._current_lb_selection = -1
        self.listbox.selection_clear(0, "end")
        self.dropdown.deiconify()
        self.dropdown.attributes("-topmost", True)

        x     = self.winfo_rootx()
        y     = self.winfo_rooty() + self.winfo_height()
        w     = self.winfo_width()
        h     = min(len(self.filtered_suggestions), 5) * 20 + 4
        self.dropdown.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # Tastatur-Navigation
    # ------------------------------------------------------------------

    def _on_down_key(self, event):
        if self.dropdown.winfo_ismapped():
            if self._current_lb_selection < self.listbox.size() - 1:
                self.listbox.selection_clear(self._current_lb_selection)
                self._current_lb_selection += 1
                self.listbox.selection_set(self._current_lb_selection)
                self.listbox.activate(self._current_lb_selection)
                self.listbox.see(self._current_lb_selection)
            return "break"

    def _on_up_key(self, event):
        if self.dropdown.winfo_ismapped():
            if self._current_lb_selection > 0:
                self.listbox.selection_clear(self._current_lb_selection)
                self._current_lb_selection -= 1
                self.listbox.selection_set(self._current_lb_selection)
                self.listbox.activate(self._current_lb_selection)
                self.listbox.see(self._current_lb_selection)
            return "break"

    def _on_enter_key(self, event):
        if self.dropdown.winfo_ismapped() and self._current_lb_selection != -1:
            self._set_value_from_listbox()
            return "break"

    def _on_listbox_select(self, event):
        self._set_value_from_listbox()

    def _set_value_from_listbox(self):
        try:
            value = self.listbox.get(self.listbox.curselection())
            self.delete(0, "end")
            self.insert(0, value)
            self.hide_dropdown()
            self.focus()
        except tk.TclError:
            pass
