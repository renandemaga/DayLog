"""
DayLog — All-in-one
Work hours tracker per contract/client.

Single dependency: pip install customtkinter
"""

import json
import os
import sys
import time
from datetime import date, timedelta
import customtkinter as ctk
from tkinter import messagebox

# ==============================================================================
#  DATA LAYER
# ==============================================================================

DATA_DIR        = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "DayLog")
CONTRACTS_FILE  = os.path.join(DATA_DIR, "contracts.json")
LOGS_FILE       = os.path.join(DATA_DIR, "logs.json")

os.makedirs(DATA_DIR, exist_ok=True)


def _load(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -- Contracts -----------------------------------------------------------------

def load_contracts() -> list[dict]:
    return _load(CONTRACTS_FILE, [])


def save_contracts(contracts: list[dict]):
    _save(CONTRACTS_FILE, contracts)


def add_contract(name: str) -> dict:
    contracts = load_contracts()
    new = {"id": str(int(time.time() * 1000)), "name": name}
    contracts.append(new)
    save_contracts(contracts)
    return new


def delete_contracts(ids: list[str]):
    contracts = load_contracts()
    cmap = {c["id"]: c["name"] for c in contracts if c["id"] in ids}
    logs = load_logs()
    today = date.today().isoformat()
    logs.setdefault(today, {})
    logs.setdefault("_names", {})
    for cid in ids:
        logs[today][cid + "_deleted"] = True
        if cid in cmap:
            logs["_names"][cid] = cmap[cid]
    _save(LOGS_FILE, logs)
    save_contracts([c for c in contracts if c["id"] not in ids])


# -- Logs ----------------------------------------------------------------------

def load_logs() -> dict:
    return _load(LOGS_FILE, {})


def _save_contract_name(logs: dict, contract_id: str):
    cmap = {c["id"]: c["name"] for c in load_contracts()}
    if contract_id in cmap:
        logs.setdefault("_names", {})
        logs["_names"][contract_id] = cmap[contract_id]


def add_minutes(contract_id: str, minutes: int):
    logs = load_logs()
    today = date.today().isoformat()
    logs.setdefault(today, {})
    logs[today][contract_id] = max(0, logs[today].get(contract_id, 0) + minutes)
    _save_contract_name(logs, contract_id)
    _save(LOGS_FILE, logs)


def get_today_log() -> dict:
    return load_logs().get(date.today().isoformat(), {})


def reset_hours(contract_ids: list[str]):
    logs = load_logs()
    today = date.today().isoformat()
    logs.setdefault(today, {})
    for cid in contract_ids:
        logs[today][cid + "_reset"] = True
        logs[today][cid] = 0
        _save_contract_name(logs, cid)
    _save(LOGS_FILE, logs)


def close_month() -> dict:
    """Close the monthly cycle. Returns the saved summary."""
    logs = load_logs()
    today = date.today()
    today_iso = today.isoformat()
    month_start = today.replace(day=1)

    # Aggregate monthly hours per contract
    summary: dict[str, int] = {}
    d = month_start
    while d <= today:
        day_log = logs.get(d.isoformat(), {})
        for cid, val in day_log.items():
            if cid.endswith("_reset") or cid.endswith("_deleted"):
                continue
            if isinstance(val, int):
                summary[cid] = summary.get(cid, 0) + val
        d += timedelta(days=1)

    # Aggregate by week
    weeks = []
    ws = month_start
    while ws <= today:
        we = ws + timedelta(days=(6 - ws.weekday()))
        if we > today:
            we = today
        week_totals: dict[str, int] = {}
        wd = ws
        while wd <= we:
            day_log = logs.get(wd.isoformat(), {})
            for cid, val in day_log.items():
                if cid.endswith("_reset") or cid.endswith("_deleted") or cid == "_month_closed":
                    continue
                if isinstance(val, int):
                    week_totals[cid] = week_totals.get(cid, 0) + val
            wd += timedelta(days=1)
        if any(v > 0 for v in week_totals.values()):
            weeks.append({
                "from": ws.isoformat(),
                "to": we.isoformat(),
                "summary": week_totals,
                "total": sum(week_totals.values()),
            })
        ws = we + timedelta(days=1)

    # Record closure
    logs.setdefault(today_iso, {})
    logs[today_iso]["_month_closed"] = {
        "from": month_start.isoformat(),
        "to": today_iso,
        "summary": summary,
        "total": sum(summary.values()),
        "weeks": weeks,
    }

    # Zero today's hours on Home
    for cid in summary:
        logs[today_iso][cid] = 0

    # Save contract names
    cmap = {c["id"]: c["name"] for c in load_contracts()}
    logs.setdefault("_names", {})
    for cid in summary:
        if cid in cmap:
            logs["_names"][cid] = cmap[cid]

    _save(LOGS_FILE, logs)
    return summary


# -- Helpers -------------------------------------------------------------------

def mins_to_str(mins: int) -> str:
    if not mins:
        return "0h"
    h, m = divmod(mins, 60)
    if h and m:
        return f"{h}h {m}m"
    return f"{h}h" if h else f"{m}m"


def format_date(iso: str) -> str:
    y, mo, d = iso.split("-")
    return f"{d}/{mo}/{y}"


def confirm(title: str, msg: str) -> bool:
    return messagebox.askyesno(title, msg)


# ==============================================================================
#  THEME
# ==============================================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG       = "#0c0c0c"
BG2      = "#111111"
BG3      = "#181818"
BORDER   = "#222222"
AMBER    = "#f59e0b"
AMBER_DK = "#92600a"
RED      = "#ef4444"
TEXT     = "#e0e0e0"
MUTED    = "#555555"

FONT_S  = ("Courier New", 9)
FONT_M  = ("Courier New", 11)
FONT_L  = ("Courier New", 14, "bold")
FONT_XL = ("Courier New", 22, "bold")
FONT_H  = ("Arial", 13, "bold")


# ==============================================================================
#  APP
# ==============================================================================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DayLog")
        self.geometry("780x560")
        self.minsize(700, 500)
        self.configure(fg_color=BG)

        self.active_ids: list[str] = []

        # -- Header ------------------------------------------------------------
        hdr = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="● DayLog", font=("Courier New", 15, "bold"),
                     text_color=AMBER).pack(side="left", padx=20, pady=12)
        self.hdr_mode = ctk.CTkLabel(hdr, text="// home", font=FONT_S, text_color=MUTED)
        self.hdr_mode.pack(side="right", padx=20)

        # -- Container ---------------------------------------------------------
        self.container = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.container.pack(fill="both", expand=True, padx=20, pady=16)

        self.show_home()

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def show_home(self):
        self.hdr_mode.configure(text="// home")
        self._clear()
        HomeFrame(self.container, self)

    def show_work(self):
        self.hdr_mode.configure(text="// active shift")
        self._clear()
        WorkFrame(self.container, self)

    def show_history(self):
        self.hdr_mode.configure(text="// history")
        self._clear()
        HistoryFrame(self.container, self)

    def show_report(self):
        self.hdr_mode.configure(text="// report")
        self._clear()
        ReportFrame(self.container, self)


# ==============================================================================
#  HOME
# ==============================================================================

class HomeFrame(ctk.CTkFrame):
    def __init__(self, parent, app: App):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.pack(fill="both", expand=True)
        self.app = app
        self.check_vars: dict[str, ctk.BooleanVar] = {}
        self._build()

    def _build(self):
        # Left column — contract list
        left = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        left.place(relx=0, rely=0, relwidth=0.62, relheight=1)

        top_row = ctk.CTkFrame(left, fg_color=BG, corner_radius=0)
        top_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(top_row, text="ACTIVE CONTRACTS", font=FONT_S,
                     text_color=AMBER).pack(side="left")
        self.btn_select_all = ctk.CTkButton(
            top_row, text="Select all", width=130, height=24, font=FONT_S,
            fg_color="transparent", text_color="#ffffff",
            border_color="#ffffff", border_width=1, hover_color=BG3,
            command=self._toggle_select_all)
        self.btn_select_all.pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(left, fg_color=BG2, corner_radius=4,
                                                  border_width=1, border_color=BORDER)
        self.list_frame.pack(fill="both", expand=True, pady=(0, 12))
        self._populate_list()

        add_row = ctk.CTkFrame(left, fg_color=BG, corner_radius=0)
        add_row.pack(fill="x")
        self.entry = ctk.CTkEntry(add_row, placeholder_text="Contract name...",
                                  fg_color=BG2, border_color=BORDER,
                                  text_color=TEXT, font=FONT_H)
        self.entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.entry.bind("<Return>", lambda e: self._add_contract())
        ctk.CTkButton(add_row, text="+ Add", width=110, font=FONT_M,
                      fg_color=AMBER, text_color=BG, hover_color="#fbbf24",
                      command=self._add_contract).pack(side="left", padx=(8, 0))

        # Right column — action buttons
        right = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        right.place(relx=0.65, rely=0, relwidth=0.35, relheight=1)

        ctk.CTkLabel(right, text="ACTIONS", font=FONT_S,
                     text_color=AMBER).pack(anchor="w", pady=(0, 12))

        self.btn_start = ctk.CTkButton(
            right, text="▶  Start Shift", font=FONT_M, height=40,
            fg_color="transparent", text_color=MUTED,
            border_color="#ffffff", border_width=1, hover_color=BG3,
            command=self._start_work)
        self.btn_start.pack(fill="x", pady=(0, 8))

        self.btn_delete = ctk.CTkButton(
            right, text="✕  Delete Selected", font=FONT_M, height=40,
            fg_color="transparent", text_color=MUTED,
            border_color="#ffffff", border_width=1, hover_color=BG3,
            command=self._delete_selected)
        self.btn_delete.pack(fill="x", pady=(0, 8))

        self.btn_reset = ctk.CTkButton(
            right, text="⟳  Reset Hours", font=FONT_M, height=40,
            fg_color="transparent", text_color=MUTED,
            border_color="#ffffff", border_width=1, hover_color=BG3,
            command=self._reset_hours)
        self.btn_reset.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            right, text="■  Close Month", font=FONT_M, height=40,
            fg_color="transparent", text_color="#facc15",
            border_color="#facc15", border_width=1, hover_color="#1a1500",
            command=self._close_month).pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            right, text="◎  View History", font=FONT_M, height=40,
            fg_color="transparent", text_color="#22d3ee",
            border_color="#22d3ee", border_width=1, hover_color="#0a1a1e",
            command=self.app.show_history).pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            right, text="▤  Report", font=FONT_M, height=40,
            fg_color="transparent", text_color="#a78bfa",
            border_color="#a78bfa", border_width=1, hover_color="#0f0a1e",
            command=self.app.show_report).pack(fill="x")

        self._refresh_btns()

    def _populate_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.check_vars.clear()
        contracts = load_contracts()
        today_log = get_today_log()

        if not contracts:
            ctk.CTkLabel(self.list_frame, text="No contracts registered",
                         font=FONT_S, text_color=MUTED).pack(pady=30)
            return

        for c in contracts:
            var = ctk.BooleanVar(value=c["id"] in self.app.active_ids)
            self.check_vars[c["id"]] = var

            row = ctk.CTkFrame(self.list_frame, fg_color=BG2, corner_radius=0)
            row.pack(fill="x", pady=(0, 1))

            cb = ctk.CTkCheckBox(row, text="", variable=var,
                             width=24, checkbox_width=16, checkbox_height=16,
                             checkmark_color=BG, fg_color=AMBER, hover_color=AMBER_DK,
                             command=self._refresh_btns)
            cb.pack(side="left", padx=(10, 6), pady=10)

            lbl = ctk.CTkLabel(row, text=c["name"], font=FONT_H,
                         text_color=TEXT, anchor="w")
            lbl.pack(side="left", fill="x", expand=True)

            def on_row_click(e, v=var):
                v.set(not v.get())
                self._refresh_btns()
            row.bind("<Button-1>", on_row_click)
            lbl.bind("<Button-1>", on_row_click)

            mins = today_log.get(c["id"], 0)
            if mins:
                ctk.CTkLabel(row, text=mins_to_str(mins), font=FONT_S,
                             text_color=AMBER).pack(side="right", padx=12)

    def _toggle_select_all(self):
        all_selected = all(v.get() for v in self.check_vars.values()) if self.check_vars else False
        for v in self.check_vars.values():
            v.set(not all_selected)
        self._refresh_btns()

    def _refresh_btns(self):
        has = any(v.get() for v in self.check_vars.values())
        state = "normal" if has else "disabled"
        if has:
            self.btn_start.configure(state=state,
                text_color="#39ff14", border_color="#39ff14", hover_color="#0a1a00")
            self.btn_delete.configure(state=state,
                text_color=RED, border_color=RED)
            self.btn_reset.configure(state=state,
                text_color="#f97316", border_color="#f97316")
        else:
            self.btn_start.configure(state=state,
                text_color=MUTED, border_color="#ffffff")
            self.btn_delete.configure(state=state,
                text_color=MUTED, border_color="#ffffff")
            self.btn_reset.configure(state=state,
                text_color=MUTED, border_color="#ffffff")
        if self.check_vars:
            all_on = all(v.get() for v in self.check_vars.values())
            self.btn_select_all.configure(
                text="Deselect all" if all_on else "Select all")

    def _selected_ids(self) -> list[str]:
        return [cid for cid, v in self.check_vars.items() if v.get()]

    def _add_contract(self):
        name = self.entry.get().strip()
        if not name:
            return
        existing = [c["name"].lower() for c in load_contracts()]
        if name.lower() in existing:
            messagebox.showwarning("Duplicate Contract",
                                   f'A contract named "{name}" already exists.')
            return
        if not confirm("Add Contract", f'Add contract "{name}"?'):
            return
        add_contract(name)
        self.entry.delete(0, "end")
        self._populate_list()
        self._refresh_btns()

    def _delete_selected(self):
        ids = self._selected_ids()
        names = ", ".join(c["name"] for c in load_contracts() if c["id"] in ids)
        if not confirm("Delete Contracts",
                       f'Are you sure you want to delete:\n\n"{names}"\n\nThis action cannot be undone.'):
            return
        delete_contracts(ids)
        self.app.active_ids = [i for i in self.app.active_ids if i not in ids]
        self._populate_list()
        self._refresh_btns()

    def _reset_hours(self):
        ids = self._selected_ids()
        names = ", ".join(c["name"] for c in load_contracts() if c["id"] in ids)
        if not confirm("Reset Hours",
                       f'Reset hours for:\n\n"{names}"\n\nHistory will be preserved and the reset will be logged.'):
            return
        reset_hours(ids)
        self._populate_list()

    def _close_month(self):
        today = date.today()
        month_names = ["January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        month_label = f"{month_names[today.month - 1]} {today.year}"
        if not confirm("Close Month",
                       f'Close the {month_label} cycle?\n\nThe monthly summary will be saved to history and report.'):
            return
        close_month()
        self._populate_list()

    def _start_work(self):
        ids = self._selected_ids()
        names = "\n".join(f"  • {c['name']}" for c in load_contracts() if c["id"] in ids)
        if not confirm("Start Shift", f"Start shift with contracts:\n\n{names}"):
            return
        self.app.active_ids = ids
        self.app.show_work()


# ==============================================================================
#  WORK
# ==============================================================================

class WorkFrame(ctk.CTkFrame):
    def __init__(self, parent, app: App):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.pack(fill="both", expand=True)
        self.app = app
        self.card_labels: dict[str, ctk.CTkLabel] = {}
        self._build()

    def _build(self):
        active = [c for c in load_contracts() if c["id"] in self.app.active_ids]

        ctk.CTkLabel(self, text="ACTIVE CONTRACTS", font=FONT_S,
                     text_color=AMBER).pack(anchor="w", pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True, pady=(0, 12))

        cols = 3
        for i, c in enumerate(active):
            row_idx, col_idx = divmod(i, cols)
            scroll.grid_columnconfigure(col_idx, weight=1)

            card = ctk.CTkFrame(scroll, fg_color=BG2, corner_radius=4,
                                 border_width=1, border_color=BORDER)
            card.grid(row=row_idx, column=col_idx, padx=6, pady=6, sticky="nsew")

            ctk.CTkLabel(card, text=c["name"], font=FONT_H,
                         text_color=TEXT, anchor="w").pack(anchor="w", padx=14, pady=(14, 2))
            ctk.CTkLabel(card, text="HOURS TODAY", font=FONT_S,
                         text_color=MUTED).pack(anchor="w", padx=14)

            lbl = ctk.CTkLabel(card, text=mins_to_str(get_today_log().get(c["id"], 0)),
                                font=FONT_XL, text_color=AMBER)
            lbl.pack(anchor="w", padx=14, pady=(2, 10))
            self.card_labels[c["id"]] = lbl

            btn_row = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)
            btn_row.pack(fill="x", padx=10, pady=(0, 14))
            ctk.CTkButton(
                btn_row, text="-30m", width=60, height=30, font=FONT_S,
                fg_color=BG3, text_color=RED,
                hover_color=BG3, border_color=AMBER, border_width=1,
                command=lambda cid=c["id"], cn=c["name"]: self._add_time(cid, -30, cn)
            ).pack(side="left", padx=3)
            for m, lbl_text in [(30, "+30m"), (60, "+1h"), (120, "+2h")]:
                ctk.CTkButton(
                    btn_row, text=lbl_text, width=60, height=30, font=FONT_S,
                    fg_color=BG3, text_color=MUTED,
                    hover_color=BG3, border_color=AMBER, border_width=1,
                    command=lambda cid=c["id"], mins=m, cn=c["name"]: self._add_time(cid, mins, cn)
                ).pack(side="left", padx=3)

        # Footer
        footer = ctk.CTkFrame(self, fg_color=BG2, corner_radius=4,
                               border_width=1, border_color=BORDER, height=64)
        footer.pack(fill="x")
        footer.pack_propagate(False)

        lf = ctk.CTkFrame(footer, fg_color=BG2, corner_radius=0)
        lf.pack(side="left", padx=18, pady=10)
        ctk.CTkLabel(lf, text="TODAY'S TOTAL", font=FONT_S, text_color=MUTED).pack(anchor="w")
        self.total_lbl = ctk.CTkLabel(lf, text=self._total_str(), font=FONT_XL, text_color=AMBER)
        self.total_lbl.pack(anchor="w")

        ctk.CTkButton(
            footer, text="■  End Shift", width=200, height=40, font=FONT_M,
            fg_color="transparent", text_color=RED,
            border_color=RED, border_width=1, hover_color="#2a0a0a",
            command=self._end_work).pack(side="right", padx=18)

    def _total_str(self) -> str:
        log = get_today_log()
        return mins_to_str(sum(log.get(cid, 0) for cid in self.app.active_ids))

    def _add_time(self, contract_id: str, minutes: int, contract_name: str):
        add_minutes(contract_id, minutes)
        self.card_labels[contract_id].configure(
            text=mins_to_str(get_today_log().get(contract_id, 0)))
        self.total_lbl.configure(text=self._total_str())

    def _end_work(self):
        if not confirm("End Shift",
                       "End the current shift?\n\nAll hours have been saved and will appear in history."):
            return
        self.app.active_ids = []
        self.app.show_home()


# ==============================================================================
#  HISTORY
# ==============================================================================

class HistoryFrame(ctk.CTkFrame):
    def __init__(self, parent, app: App):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.pack(fill="both", expand=True)
        self.app = app
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        top.pack(fill="x", pady=(0, 12))
        ctk.CTkButton(top, text="← Back", width=90, height=30, font=FONT_S,
                       fg_color="transparent", text_color="#ffffff",
                       border_color="#ffffff", border_width=1, hover_color=BG3,
                       command=self.app.show_home).pack(side="left")
        ctk.CTkLabel(top, text="HOURS HISTORY", font=FONT_S,
                     text_color=AMBER).pack(side="left", padx=16)

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        cmap = {c["id"]: c["name"] for c in load_contracts()}
        logs = load_logs()
        saved_names = logs.pop("_names", {})
        cmap = {**saved_names, **cmap}

        if not logs:
            ctk.CTkLabel(scroll, text="No records yet.",
                         font=FONT_M, text_color=MUTED).pack(pady=40)
            return

        for day in sorted(logs.keys(), reverse=True):
            day_log = logs[day]
            total = sum(v for k, v in day_log.items()
                        if not k.endswith("_reset") and not k.endswith("_deleted")
                        and k != "_month_closed" and isinstance(v, int))

            card = ctk.CTkFrame(scroll, fg_color=BG2, corner_radius=4,
                                 border_width=1, border_color=BORDER)
            card.pack(fill="x", pady=(0, 8))

            # Clickable header
            hdr = ctk.CTkFrame(card, fg_color=BG3, corner_radius=0)
            hdr.pack(fill="x")
            arrow = ctk.CTkLabel(hdr, text="▸", font=FONT_M, text_color=MUTED)
            arrow.pack(side="left", padx=(14, 0), pady=8)
            ctk.CTkLabel(hdr, text=format_date(day), font=FONT_L,
                         text_color=AMBER).pack(side="left", padx=(6, 0), pady=8)
            ctk.CTkLabel(hdr, text=f"Total: {mins_to_str(total)}", font=FONT_S,
                         text_color=AMBER).pack(side="right", padx=14)

            # Collapsible content
            content = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)

            # Show month closure if present
            if "_month_closed" in day_log:
                mc = day_log["_month_closed"]
                mc_row = ctk.CTkFrame(content, fg_color="#1a1500", corner_radius=0)
                mc_row.pack(fill="x")
                period = f"{format_date(mc['from'])} → {format_date(mc['to'])}"
                ctk.CTkLabel(mc_row, text=f"■ Month closed ({period})", font=FONT_H,
                             text_color="#facc15", anchor="w").pack(side="left", padx=18, pady=7)
                ctk.CTkLabel(mc_row, text=mins_to_str(mc["total"]), font=FONT_M,
                             text_color="#facc15").pack(side="right", padx=18)
                for scid, smins in mc.get("summary", {}).items():
                    if smins > 0:
                        sr = ctk.CTkFrame(content, fg_color=BG2, corner_radius=0)
                        sr.pack(fill="x")
                        sname = cmap.get(scid, f"Contract ({scid[-4:]})")
                        ctk.CTkLabel(sr, text=f"  {sname}", font=FONT_H,
                                     text_color=TEXT, anchor="w").pack(side="left", padx=18, pady=5)
                        ctk.CTkLabel(sr, text=mins_to_str(smins), font=FONT_M,
                                     text_color=AMBER).pack(side="right", padx=18)

            for cid, val in day_log.items():
                if cid == "_month_closed":
                    continue
                if cid.endswith("_deleted"):
                    real_cid = cid[:-8]
                    row = ctk.CTkFrame(content, fg_color=BG2, corner_radius=0)
                    row.pack(fill="x")
                    name = cmap.get(real_cid, f"Contract ({real_cid[-4:]})")
                    ctk.CTkLabel(row, text=name, font=FONT_H,
                                 text_color=TEXT, anchor="w").pack(side="left", padx=18, pady=7)
                    ctk.CTkLabel(row, text="✕ Contract removed", font=FONT_M,
                                 text_color=RED).pack(side="right", padx=18)
                elif cid.endswith("_reset"):
                    real_cid = cid[:-6]
                    row = ctk.CTkFrame(content, fg_color=BG2, corner_radius=0)
                    row.pack(fill="x")
                    name = cmap.get(real_cid, f"Contract ({real_cid[-4:]})")
                    ctk.CTkLabel(row, text=name, font=FONT_H,
                                 text_color=TEXT, anchor="w").pack(side="left", padx=18, pady=7)
                    ctk.CTkLabel(row, text="⟳ Hours reset", font=FONT_M,
                                 text_color="#f97316").pack(side="right", padx=18)
                else:
                    row = ctk.CTkFrame(content, fg_color=BG2, corner_radius=0)
                    row.pack(fill="x")
                    name = cmap.get(cid, f"Removed contract ({cid[-4:]})")
                    ctk.CTkLabel(row, text=name, font=FONT_H,
                                 text_color=TEXT, anchor="w").pack(side="left", padx=18, pady=7)
                    ctk.CTkLabel(row, text=mins_to_str(val), font=FONT_M,
                                 text_color=AMBER).pack(side="right", padx=18)

            def toggle(e, c=content, a=arrow):
                if c.winfo_manager():
                    c.pack_forget()
                    a.configure(text="▸")
                else:
                    c.pack(fill="x")
                    a.configure(text="▾")
            hdr.bind("<Button-1>", toggle)
            for child in hdr.winfo_children():
                child.bind("<Button-1>", toggle)


# ==============================================================================
#  REPORT
# ==============================================================================

class ReportFrame(ctk.CTkFrame):
    def __init__(self, parent, app: App):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.pack(fill="both", expand=True)
        self.app = app
        self._build()

    def _aggregate(self, start: date, end: date) -> dict[str, int]:
        logs = load_logs()
        logs.pop("_names", None)
        totals: dict[str, int] = {}
        d = start
        while d <= end:
            day_log = logs.get(d.isoformat(), {})
            for cid, val in day_log.items():
                if cid.endswith("_reset") or cid.endswith("_deleted") or cid == "_month_closed":
                    continue
                if isinstance(val, int):
                    totals[cid] = totals.get(cid, 0) + val
            d += timedelta(days=1)
        return totals

    def _get_name(self, cid: str, cmap: dict, saved: dict) -> str:
        return cmap.get(cid, saved.get(cid, f"Contract ({cid[-4:]})"))

    def _build(self):
        top = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        top.pack(fill="x", pady=(0, 12))
        ctk.CTkButton(top, text="← Back", width=90, height=30, font=FONT_S,
                       fg_color="transparent", text_color="#ffffff",
                       border_color="#ffffff", border_width=1, hover_color=BG3,
                       command=self.app.show_home).pack(side="left")
        ctk.CTkLabel(top, text="REPORT", font=FONT_S,
                     text_color="#a78bfa").pack(side="left", padx=16)

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        cmap = {c["id"]: c["name"] for c in load_contracts()}
        logs = load_logs()
        saved_names = logs.get("_names", {})

        today = date.today()
        month_start = today.replace(day=1)
        month_names = ["January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]

        # Detect closed cycles
        closed = []
        current_month_closed = None
        for day_key, day_log in logs.items():
            if day_key == "_names":
                continue
            if isinstance(day_log, dict) and "_month_closed" in day_log:
                mc = day_log["_month_closed"]
                closed.append(mc)
                mc_from = date.fromisoformat(mc["from"])
                if mc_from.year == today.year and mc_from.month == today.month:
                    current_month_closed = mc
        closed.sort(key=lambda x: x["to"], reverse=True)

        # -- Current week/month (always show if there are hours) ---------------
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_totals = self._aggregate(week_start, today)

        if any(v > 0 for v in week_totals.values()):
            self._render_section(scroll, f"CURRENT WEEK  ({format_date(week_start.isoformat())} → {format_date(week_end.isoformat())})",
                                 week_totals, cmap, saved_names, "#a78bfa")

        month_totals = self._aggregate(month_start, today)
        month_label = f"{month_names[today.month - 1]} {today.year}"

        if any(v > 0 for v in month_totals.values()):
            self._render_section(scroll, f"CURRENT MONTH  ({month_label})",
                                 month_totals, cmap, saved_names, "#a78bfa")

        if current_month_closed is None:
            ws = month_start
            week_num = 1
            while ws <= today:
                we = ws + timedelta(days=(6 - ws.weekday()))
                if we > today:
                    we = today
                if ws != week_start:
                    wt = self._aggregate(ws, we)
                    if wt:
                        self._render_section(scroll,
                            f"WEEK {week_num}  ({format_date(ws.isoformat())} → {format_date(we.isoformat())})",
                            wt, cmap, saved_names, "#a78bfa")
                ws = we + timedelta(days=1)
                week_num += 1

        # -- Closed cycles -----------------------------------------------------
        for mc in closed:
            period = f"{format_date(mc['from'])} → {format_date(mc['to'])}"
            month_from = date.fromisoformat(mc["from"])
            month_label = f"{month_names[month_from.month - 1]} {month_from.year}"

            # Month summary
            summary = {k: v for k, v in mc.get("summary", {}).items() if v > 0}
            self._render_section(scroll,
                f"■ MONTH CLOSED  ({month_label})",
                summary, cmap, saved_names, "#a78bfa")

            # Week breakdown
            for i, wk in enumerate(mc.get("weeks", []), 1):
                wk_summary = {k: v for k, v in wk.get("summary", {}).items() if v > 0}
                if wk_summary:
                    wk_period = f"{format_date(wk['from'])} → {format_date(wk['to'])}"
                    self._render_section(scroll,
                        f"  WEEK {i}  ({wk_period})",
                        wk_summary, cmap, saved_names, "#a78bfa")

    def _render_section(self, parent, title: str, totals: dict[str, int],
                        cmap: dict, saved: dict, color: str):
        card = ctk.CTkFrame(parent, fg_color=BG2, corner_radius=4,
                             border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(0, 12))

        hdr = ctk.CTkFrame(card, fg_color=BG3, corner_radius=0)
        hdr.pack(fill="x")
        arrow = ctk.CTkLabel(hdr, text="▸", font=FONT_M, text_color=MUTED)
        arrow.pack(side="left", padx=(14, 0), pady=8)
        ctk.CTkLabel(hdr, text=title, font=FONT_S,
                     text_color=color).pack(side="left", padx=(6, 0), pady=8)

        grand_total = sum(totals.values())
        ctk.CTkLabel(hdr, text=f"Total: {mins_to_str(grand_total)}", font=FONT_S,
                     text_color="#a78bfa").pack(side="right", padx=14)

        content = ctk.CTkFrame(card, fg_color=BG2, corner_radius=0)

        if not totals:
            ctk.CTkLabel(content, text="No records", font=FONT_S,
                         text_color=MUTED).pack(pady=12)
        else:
            for cid, mins in sorted(totals.items(), key=lambda x: x[1], reverse=True):
                row = ctk.CTkFrame(content, fg_color=BG2, corner_radius=0)
                row.pack(fill="x")
                name = self._get_name(cid, cmap, saved)
                ctk.CTkLabel(row, text=name, font=FONT_H,
                             text_color=TEXT, anchor="w").pack(side="left", padx=18, pady=7)
                ctk.CTkLabel(row, text=mins_to_str(mins), font=FONT_M,
                             text_color=AMBER).pack(side="right", padx=18)

        def toggle(e, c=content, a=arrow):
            if c.winfo_manager():
                c.pack_forget()
                a.configure(text="▸")
            else:
                c.pack(fill="x")
                a.configure(text="▾")
        hdr.bind("<Button-1>", toggle)
        for child in hdr.winfo_children():
            child.bind("<Button-1>", toggle)


# ==============================================================================
#  ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    LOCK_FILE = os.path.join(DATA_DIR, ".lock")

    # Try to acquire exclusive lock
    try:
        _lock_fd = open(LOCK_FILE, "w")
        import msvcrt
        msvcrt.locking(_lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
    except (OSError, IOError):
        import tkinter.messagebox as mb
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        mb.showwarning("DayLog", "DayLog is already running in another window.")
        root.destroy()
        sys.exit(0)

    try:
        App().mainloop()
    finally:
        try:
            msvcrt.locking(_lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
            _lock_fd.close()
            os.remove(LOCK_FILE)
        except OSError:
            pass
