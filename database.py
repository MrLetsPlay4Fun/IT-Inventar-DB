#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
database.py – Datenbankzugriff und SQL-Operationen für die IT Inventar Verwaltung.

Alle Funktionen lesen den aktuellen DB-Pfad dynamisch aus config.get_db_file(),
sodass eine Pfadänderung zur Laufzeit sofort wirksam wird.
"""

import os
import sqlite3
from tkinter import messagebox

import config

# ---------------------------------------------------------------------------
# Interner Helfer: aktuellen DB-Pfad holen
# ---------------------------------------------------------------------------

def _db() -> str:
    """Gibt den konfigurierten Datenbankpfad zurück; wirft RuntimeError wenn nicht gesetzt."""
    path = config.get_db_file()
    if not path:
        raise RuntimeError("Kein Datenbankpfad konfiguriert. Bitte zuerst Einstellungen speichern.")
    return path


# ---------------------------------------------------------------------------
# Datenbank-Initialisierung
# ---------------------------------------------------------------------------

def setup_database() -> None:
    """
    Erstellt Verzeichnis + Tabellen, falls sie nicht existieren.
    Führt außerdem Schema-Migrationen durch (fehlende Spalten hinzufügen).
    """
    db_dir = config.get_db_directory()
    db_file = config.get_db_file()

    # Verzeichnis anlegen
    try:
        os.makedirs(db_dir, exist_ok=True)
        print(f"[DB] Verzeichnis: {os.path.abspath(db_dir)}")
    except OSError as e:
        messagebox.showerror(
            "Verzeichnisfehler",
            f"Konnte das Datenbank-Verzeichnis nicht erstellen:\n{db_dir}\n\nFehler: {e}",
        )
        raise SystemExit(f"Verzeichnis nicht erstellbar: {db_dir}") from e

    conn = None
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        # --- Tabelle: materials ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                material_id     TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                type            TEXT,
                manufacturer    TEXT,
                color           TEXT,
                stock_quantity  INTEGER DEFAULT 0,
                ean_code        TEXT UNIQUE,
                inventory_number TEXT,
                status          TEXT DEFAULT 'Lagernd',
                notes           TEXT,
                unit_price      REAL
            )
        """)

        # --- Tabelle: devices ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id        TEXT PRIMARY KEY,
                device_type      TEXT,
                model            TEXT NOT NULL,
                manufacturer     TEXT,
                purchase_date    TEXT,
                location         TEXT,
                employee_name    TEXT,
                computer_name    TEXT,
                ip_address       TEXT,
                serial_number    TEXT,
                inventory_number TEXT UNIQUE,
                ean_code         TEXT,
                status           TEXT DEFAULT 'Lagernd',
                invoice_number   TEXT,
                vendor           TEXT,
                delivery_note    TEXT,
                order_number     TEXT,
                notes                 TEXT,
                purchase_price        REAL,
                warranty_date         TEXT,
                next_maintenance_date TEXT
            )
        """)

        # --- Tabelle: device_materials (Verknüpfungstabelle) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_materials (
                link_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id   TEXT NOT NULL,
                material_id TEXT NOT NULL,
                FOREIGN KEY (device_id)   REFERENCES devices   (device_id)   ON DELETE CASCADE,
                FOREIGN KEY (material_id) REFERENCES materials (material_id) ON DELETE CASCADE,
                UNIQUE (device_id, material_id)
            )
        """)

        # --- Tabelle: audit_log ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id   TEXT NOT NULL,
                action      TEXT NOT NULL,
                field_name  TEXT,
                old_value   TEXT,
                new_value   TEXT
            )
        """)

        conn.commit()

    except sqlite3.Error as e:
        messagebox.showerror("Datenbank Setup Fehler", f"Konnte die Datenbank nicht initialisieren:\n{e}")
        raise SystemExit(f"Datenbank Setup Fehler: {e}") from e
    finally:
        if conn:
            conn.close()

    # Schema-Migrationen (fehlende Spalten ergänzen)
    _run_migrations(db_file)


def _run_migrations(db_file: str) -> None:
    """Fügt fehlende Spalten zu bestehenden Tabellen hinzu (rückwärtskompatibel)."""

    def add_column_if_not_exists(table: str, column: str, col_type: str, default_value=None):
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            existing = [row[1] for row in cursor.fetchall()]
            if column not in existing:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                print(f"[DB Migration] Spalte '{column}' zu '{table}' hinzugefügt.")
                if default_value is not None:
                    cursor.execute(f"UPDATE {table} SET {column} = ?", (default_value,))
                conn.commit()
        except sqlite3.OperationalError as e:
            print(f"[DB Migration] Warnung für {column}: {e}")
        finally:
            if conn:
                conn.close()

    # Geräte-Migrationen
    add_column_if_not_exists("devices", "manufacturer",     "TEXT")
    add_column_if_not_exists("devices", "inventory_number", "TEXT")
    add_column_if_not_exists("devices", "ean_code",         "TEXT")
    add_column_if_not_exists("devices", "status",           "TEXT", default_value=config.DEFAULT_ASSET_STATUS)
    add_column_if_not_exists("devices", "ip_address",       "TEXT")
    add_column_if_not_exists("devices", "invoice_number",   "TEXT")
    add_column_if_not_exists("devices", "vendor",           "TEXT")
    add_column_if_not_exists("devices", "delivery_note",    "TEXT")
    add_column_if_not_exists("devices", "order_number",     "TEXT")
    add_column_if_not_exists("devices", "notes",            "TEXT")
    add_column_if_not_exists("devices", "purchase_price",        "REAL")
    add_column_if_not_exists("devices", "warranty_date",         "TEXT")
    add_column_if_not_exists("devices", "next_maintenance_date", "TEXT")

    # Material-Migrationen
    add_column_if_not_exists("materials", "manufacturer",     "TEXT")
    add_column_if_not_exists("materials", "color",            "TEXT")
    add_column_if_not_exists("materials", "ean_code",         "TEXT")
    add_column_if_not_exists("materials", "inventory_number", "TEXT")
    add_column_if_not_exists("materials", "status",           "TEXT", default_value=config.DEFAULT_ASSET_STATUS)
    add_column_if_not_exists("materials", "notes",            "TEXT")
    add_column_if_not_exists("materials", "unit_price",       "REAL")


# ---------------------------------------------------------------------------
# Generische Query-Hilfsfunktion
# ---------------------------------------------------------------------------

def run_query(query: str, params=(), *, fetchone=False, fetchall=False, commit=False):
    """
    Führt eine SQL-Abfrage gegen die konfigurierte Datenbank aus.

    Args:
        query:    SQL-String mit Platzhaltern (?).
        params:   Parameter-Tupel.
        fetchone: Gibt einen einzelnen Datensatz als dict zurück.
        fetchall: Gibt alle Datensätze als list[dict] zurück.
        commit:   Schreibt Änderungen (INSERT/UPDATE/DELETE).

    Returns:
        dict | list[dict] | True | None
    """
    conn = None
    try:
        conn = sqlite3.connect(_db())
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()
        cursor.execute(query, params)

        result_data = None

        if commit:
            conn.commit()
            if not fetchone and not fetchall:
                return True

        if fetchone:
            result_data = cursor.fetchone()
        elif fetchall:
            result_data = cursor.fetchall()

        if isinstance(result_data, list):
            return [dict(row) for row in result_data]
        elif isinstance(result_data, sqlite3.Row):
            return dict(result_data)

        return result_data

    except sqlite3.Error as e:
        print(f"[DB] Fehler: {e} | Query: {query[:120]}…")

        if "database is locked" in str(e):
            messagebox.showerror(
                "Datenbankfehler",
                "Datenbank ist gesperrt. Bitte kurz warten und erneut versuchen.",
                icon="warning",
            )
        elif "no such table" in str(e):
            messagebox.showerror(
                "Datenbankfehler",
                f"Tabelle nicht gefunden – ist die Datenbankdatei korrekt?\n{e}",
                icon="error",
            )
        elif "UNIQUE constraint failed" in str(e):
            messagebox.showerror(
                "Eingabefehler",
                "Ein eindeutiger Wert (z. B. EAN-Code oder Inventarnummer) ist bereits vergeben.",
                icon="error",
            )
        return None
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Status-Filter-Hilfsfunktion
# ---------------------------------------------------------------------------

def get_status_filter_clause(status_filter_text: str, is_material: bool = True):
    """Erzeugt den WHERE-Teil und Parameter für den Status-Filter."""
    if status_filter_text == "Alle anzeigen":
        return "", ()
    if status_filter_text == "Lagernd & Im Einsatz":
        return "WHERE status IN (?, ?)", ("Lagernd", "Im Einsatz")
    return "WHERE status = ?", (status_filter_text,)


# ---------------------------------------------------------------------------
# Material-Datenbankfunktionen
# ---------------------------------------------------------------------------

def add_material_db(mat_id, name, type_, manufacturer, color, stock,
                    ean_code, inventory_number, status, notes=None, unit_price=None):
    query = """
        INSERT INTO materials
        (material_id, name, type, manufacturer, color, stock_quantity,
         ean_code, inventory_number, status, notes, unit_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    return run_query(
        query,
        (mat_id, name, type_, manufacturer, color, stock, ean_code, inventory_number, status, notes, unit_price),
        commit=True,
    )


def get_all_materials_db(status_filter_text="Alle anzeigen"):
    filter_clause, params = get_status_filter_clause(status_filter_text)
    query = f"""
        SELECT material_id, name, type, manufacturer, color,
               stock_quantity, ean_code, inventory_number, status, notes, unit_price
        FROM materials
        {filter_clause}
        ORDER BY name
    """
    return run_query(query, params, fetchall=True)


def update_material_db(mat_id, name, type_, manufacturer, color, stock,
                       ean_code, inventory_number, status, notes=None, unit_price=None):
    query = """
        UPDATE materials SET
            name = ?, type = ?, manufacturer = ?, color = ?,
            stock_quantity = ?, ean_code = ?, inventory_number = ?, status = ?, notes = ?,
            unit_price = ?
        WHERE material_id = ?
    """
    return run_query(
        query,
        (name, type_, manufacturer, color, stock, ean_code, inventory_number, status, notes, unit_price, mat_id),
        commit=True,
    )


def delete_material_db(mat_id):
    return run_query("DELETE FROM materials WHERE material_id = ?", (mat_id,), commit=True)


def get_material_by_id_db(mat_id):
    return run_query(
        "SELECT material_id, name, type, manufacturer, color, stock_quantity, "
        "ean_code, inventory_number, status, notes, unit_price FROM materials WHERE material_id = ?",
        (mat_id,),
        fetchone=True,
    )


def get_material_by_barcode_db(barcode):
    query = """
        SELECT material_id, name, type, manufacturer, color,
               stock_quantity, ean_code, inventory_number, status
        FROM materials
        WHERE ean_code = ? OR inventory_number = ?
    """
    return run_query(query, (barcode, barcode), fetchone=True)


def update_material_stock_db(material_id, new_stock_quantity):
    if not isinstance(new_stock_quantity, int) or new_stock_quantity < 0:
        print(f"[DB] Ungültiger Lagerbestand ({new_stock_quantity}) für {material_id} verhindert.")
        return False
    result = run_query(
        "UPDATE materials SET stock_quantity = ? WHERE material_id = ?",
        (new_stock_quantity, material_id),
        commit=True,
    )
    return result is True


def search_materials_db(search_term, status_filter_text="Alle anzeigen"):
    filter_clause, status_params = get_status_filter_clause(status_filter_text)
    cols = ["name", "type", "manufacturer", "color", "material_id", "ean_code", "inventory_number"]
    placeholder = " OR ".join(f"{c} LIKE ?" for c in cols)
    search_params = ("%" + search_term + "%",) * len(cols)

    where = f"{filter_clause} AND ({placeholder})" if filter_clause else f"WHERE {placeholder}"
    query = f"""
        SELECT material_id, name, type, manufacturer, color,
               stock_quantity, ean_code, inventory_number, status, notes, unit_price
        FROM materials
        {where}
        ORDER BY name
    """
    return run_query(query, status_params + search_params, fetchall=True)


# ---------------------------------------------------------------------------
# Geräte-Datenbankfunktionen
# ---------------------------------------------------------------------------

def add_device_db(dev_id, dev_type, model, manufacturer, p_date, loc,
                  emp_name, comp_name, ip_address, serial, inventory_number,
                  ean_code, status, invoice_number, vendor, delivery_note, order_number,
                  notes=None, purchase_price=None, warranty_date=None,
                  next_maintenance_date=None):
    query = """
        INSERT INTO devices
        (device_id, device_type, model, manufacturer, purchase_date, location,
         employee_name, computer_name, ip_address, serial_number, inventory_number,
         ean_code, status, invoice_number, vendor, delivery_note, order_number, notes,
         purchase_price, warranty_date, next_maintenance_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    return run_query(
        query,
        (dev_id, dev_type, model, manufacturer, p_date, loc, emp_name, comp_name,
         ip_address, serial, inventory_number, ean_code, status,
         invoice_number, vendor, delivery_note, order_number, notes, purchase_price,
         warranty_date, next_maintenance_date),
        commit=True,
    )


def get_all_devices_db(status_filter_text="Alle anzeigen"):
    filter_clause, params = get_status_filter_clause(status_filter_text, is_material=False)
    query = f"""
        SELECT device_id, device_type, model, manufacturer, purchase_date, location,
               employee_name, computer_name, ip_address, serial_number, inventory_number,
               ean_code, status, invoice_number, vendor, delivery_note, order_number, notes,
               purchase_price, warranty_date, next_maintenance_date
        FROM devices
        {filter_clause}
        ORDER BY model
    """
    return run_query(query, params, fetchall=True)


def update_device_db(dev_id, dev_type, model, manufacturer, p_date, loc,
                     emp_name, comp_name, ip_address, serial, inventory_number,
                     ean_code, status, invoice_number, vendor, delivery_note, order_number,
                     notes=None, purchase_price=None, warranty_date=None,
                     next_maintenance_date=None):
    query = """
        UPDATE devices SET
            device_type = ?, model = ?, manufacturer = ?, purchase_date = ?,
            location = ?, employee_name = ?, computer_name = ?, ip_address = ?,
            serial_number = ?, inventory_number = ?, ean_code = ?, status = ?,
            invoice_number = ?, vendor = ?, delivery_note = ?, order_number = ?, notes = ?,
            purchase_price = ?, warranty_date = ?, next_maintenance_date = ?
        WHERE device_id = ?
    """
    return run_query(
        query,
        (dev_type, model, manufacturer, p_date, loc, emp_name, comp_name,
         ip_address, serial, inventory_number, ean_code, status,
         invoice_number, vendor, delivery_note, order_number, notes, purchase_price,
         warranty_date, next_maintenance_date, dev_id),
        commit=True,
    )


def delete_device_db(dev_id):
    return run_query("DELETE FROM devices WHERE device_id = ?", (dev_id,), commit=True)


def get_device_by_id_db(dev_id):
    query = """
        SELECT device_id, device_type, model, manufacturer, purchase_date, location,
               employee_name, computer_name, ip_address, serial_number, inventory_number,
               ean_code, status, invoice_number, vendor, delivery_note, order_number, notes,
               purchase_price, warranty_date, next_maintenance_date
        FROM devices WHERE device_id = ?
    """
    return run_query(query, (dev_id,), fetchone=True)


def search_devices_db(search_term, status_filter_text="Alle anzeigen"):
    filter_clause, status_params = get_status_filter_clause(status_filter_text, is_material=False)
    cols = [
        "model", "device_type", "manufacturer", "location", "employee_name",
        "computer_name", "ip_address", "serial_number", "purchase_date",
        "device_id", "inventory_number", "ean_code",
        "invoice_number", "vendor", "delivery_note", "order_number",
    ]
    placeholder = " OR ".join(f"{c} LIKE ?" for c in cols)
    search_params = ("%" + search_term + "%",) * len(cols)

    where = f"{filter_clause} AND ({placeholder})" if filter_clause else f"WHERE {placeholder}"
    query = f"""
        SELECT device_id, device_type, model, manufacturer, purchase_date, location,
               employee_name, computer_name, ip_address, serial_number, inventory_number,
               ean_code, status, invoice_number, vendor, delivery_note, order_number, notes,
               purchase_price, warranty_date, next_maintenance_date
        FROM devices
        {where}
        ORDER BY model
    """
    return run_query(query, status_params + search_params, fetchall=True)


# ---------------------------------------------------------------------------
# Autocomplete
# ---------------------------------------------------------------------------

def get_unique_column_values_db(column_name: str) -> list:
    """Eindeutige, nicht-leere Werte einer Gerätespalte für Autocomplete."""
    allowed = {"device_type", "manufacturer", "model", "location", "employee_name", "vendor"}
    if column_name not in allowed:
        print(f"[DB] Ungültiger Autocomplete-Spaltenname: {column_name}")
        return []
    query = (
        f"SELECT DISTINCT {column_name} FROM devices "
        f"WHERE {column_name} IS NOT NULL AND {column_name} != '' AND {column_name} != '-' "
        f"ORDER BY {column_name}"
    )
    results = run_query(query, fetchall=True)
    return [row[column_name] for row in results] if results else []


# ---------------------------------------------------------------------------
# Gerät ↔ Material Verknüpfungen
# ---------------------------------------------------------------------------

def get_associated_devices_for_material_db(material_id):
    query = """
        SELECT d.device_id, d.model, d.device_type, d.employee_name,
               d.location, d.inventory_number, d.status
        FROM devices d
        JOIN device_materials dm ON d.device_id = dm.device_id
        WHERE dm.material_id = ?
        ORDER BY d.model, d.employee_name
    """
    return run_query(query, (material_id,), fetchall=True)


def link_materials_to_device_db(device_id, material_ids):
    """Setzt die Material-Verknüpfungen eines Geräts (erst löschen, dann neu einfügen)."""
    run_query("DELETE FROM device_materials WHERE device_id = ?", (device_id,), commit=True)

    if not material_ids:
        return True

    params = [(device_id, mid) for mid in material_ids]
    conn = None
    try:
        conn = sqlite3.connect(_db())
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executemany(
            "INSERT OR IGNORE INTO device_materials (device_id, material_id) VALUES (?, ?)",
            params,
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        messagebox.showerror("Datenbankfehler", f"Fehler beim Verknüpfen von Materialien:\n{e}")
        return False
    finally:
        if conn:
            conn.close()


def get_associated_materials_for_device_db(device_id):
    query = """
        SELECT m.material_id, m.name, m.type, m.manufacturer, m.color,
               m.stock_quantity, m.ean_code, m.inventory_number, m.status
        FROM materials m
        JOIN device_materials dm ON m.material_id = dm.material_id
        WHERE dm.device_id = ?
        ORDER BY m.name
    """
    return run_query(query, (device_id,), fetchall=True)


def get_linked_material_ids_for_device(device_id) -> list:
    results = run_query(
        "SELECT material_id FROM device_materials WHERE device_id = ?",
        (device_id,),
        fetchall=True,
    )
    return [row["material_id"] for row in results] if results else []


# ---------------------------------------------------------------------------
# Audit-Log
# ---------------------------------------------------------------------------

def get_dashboard_stats_db() -> dict:
    """Liefert Gesamtzahlen: Geräte, Material, Gesamtwert, fällige Wartungen."""
    from datetime import date
    today     = date.today().isoformat()
    dev_count = run_query("SELECT COUNT(*) AS n FROM devices", fetchone=True)
    mat_count = run_query("SELECT COUNT(*) AS n FROM materials", fetchone=True)
    dev_value = run_query(
        "SELECT COALESCE(SUM(purchase_price), 0) AS v FROM devices", fetchone=True
    )
    mat_value = run_query(
        "SELECT COALESCE(SUM(unit_price * stock_quantity), 0) AS v FROM materials",
        fetchone=True,
    )
    maint_due = run_query(
        "SELECT COUNT(*) AS n FROM devices "
        "WHERE next_maintenance_date IS NOT NULL AND next_maintenance_date != '' "
        "AND next_maintenance_date <= ?",
        (today,), fetchone=True,
    )
    return {
        "device_count":    (dev_count or {}).get("n", 0),
        "material_count":  (mat_count or {}).get("n", 0),
        "total_value":     (dev_value or {}).get("v", 0.0) + (mat_value or {}).get("v", 0.0),
        "maintenance_due": (maint_due or {}).get("n", 0),
    }


def get_devices_by_status_db() -> list:
    """Geräte gruppiert nach Status: [{'status': ..., 'count': ...}, ...]"""
    return run_query(
        "SELECT status, COUNT(*) AS count FROM devices "
        "GROUP BY status ORDER BY count DESC",
        fetchall=True,
    ) or []


def get_devices_by_location_db(limit: int = 5) -> list:
    """Top-N Standorte nach Geräteanzahl: [{'location': ..., 'count': ...}, ...]"""
    return run_query(
        "SELECT COALESCE(location, '(kein Standort)') AS location, "
        "COUNT(*) AS count FROM devices "
        "WHERE location IS NOT NULL AND location != '' AND location != '-' "
        "GROUP BY location ORDER BY count DESC LIMIT ?",
        (limit,), fetchall=True,
    ) or []


def get_expiring_devices_db(days: int = 30) -> list:
    """Geräte mit abgelaufener oder bald ablaufender Garantie/Wartung (≤ days Tage)."""
    from datetime import date, timedelta
    threshold = (date.today() + timedelta(days=days)).isoformat()
    return run_query(
        "SELECT device_id, model, manufacturer, location, employee_name, "
        "warranty_date, next_maintenance_date, status FROM devices "
        "WHERE (warranty_date IS NOT NULL AND warranty_date != '' "
        "       AND warranty_date <= ?) "
        "   OR (next_maintenance_date IS NOT NULL AND next_maintenance_date != '' "
        "       AND next_maintenance_date <= ?) "
        "ORDER BY COALESCE(NULLIF(warranty_date,''), '9999'), "
        "         COALESCE(NULLIF(next_maintenance_date,''), '9999')",
        (threshold, threshold), fetchall=True,
    ) or []


def log_audit_db(entity_type: str, entity_id: str, action: str,
                 field_name=None, old_value=None, new_value=None):
    """Schreibt einen Eintrag in die audit_log-Tabelle."""
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_query(
        "INSERT INTO audit_log (timestamp, entity_type, entity_id, action, "
        "field_name, old_value, new_value) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ts, entity_type, entity_id, action, field_name,
         str(old_value) if old_value is not None else None,
         str(new_value) if new_value is not None else None),
        commit=True,
    )


def get_audit_log_db(entity_type=None, action=None,
                     date_from=None, date_to=None) -> list:
    """Liest Audit-Log-Einträge mit optionalen Filtern."""
    conditions, params = [], []
    if entity_type and entity_type != "Alle":
        conditions.append("entity_type = ?")
        params.append(entity_type)
    if action and action != "Alle":
        conditions.append("action = ?")
        params.append(action)
    if date_from:
        conditions.append("timestamp >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("timestamp <= ?")
        params.append(date_to + " 23:59:59")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return run_query(
        f"SELECT log_id, timestamp, entity_type, entity_id, action, "
        f"field_name, old_value, new_value FROM audit_log {where} "
        f"ORDER BY log_id DESC",
        tuple(params),
        fetchall=True,
    ) or []
