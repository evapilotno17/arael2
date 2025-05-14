"""utils.py – high‑level helper for keystroke DB

• loads the whole SQLite db into a pandas DataFrame on construction
• expands cols → timestamp (datetime) + keystroke (unicode)
• OS‑aware: full US‑ANSI code→glyph maps for Linux (evdev) and macOS (Quartz)
   including all alphanumerics, punctuation, and common modifiers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict
from datetime import datetime

import pandas as pd
import sqlite3

# ------------------------------------------------------------------
# complete US‑ANSI key‑code → glyph maps
# ------------------------------------------------------------------
# linux / evdev (see include/uapi/linux/input-event-codes.h)
LINUX_KEYMAP: Dict[int, str] = {
    # ─ letters ─
    16:"q",17:"w",18:"e",19:"r",20:"t",21:"y",22:"u",23:"i",24:"o",25:"p",
    30:"a",31:"s",32:"d",33:"f",34:"g",35:"h",36:"j",37:"k",38:"l",
    44:"z",45:"x",46:"c",47:"v",48:"b",49:"n",50:"m",
    # ─ digits & shifted symbols ─
    2:"1",3:"2",4:"3",5:"4",6:"5",7:"6",8:"7",9:"8",10:"9",11:"0",
    12:"-",13:"=",26:"[",27:"]",39:";",40:"'",41:"`",51:",",52:".",53:"/",43:"\\",
    # ─ function row F1‑F12 ─
    59:"<f1>",60:"<f2>",61:"<f3>",62:"<f4>",63:"<f5>",64:"<f6>",65:"<f7>",66:"<f8>",67:"<f9>",68:"<f10>",87:"<f11>",88:"<f12>",
    # ─ control / nav ─
    42:"<shift>",54:"<shift_r>",29:"<ctrl>",97:"<ctrl_r>",56:"<alt>",100:"<alt_r>",125:"<gui>",126:"<gui_r>",
    14:"<backspace>",15:"<tab>",28:"<enter>",57:"<space>",58:"<caps_lock>",
    107:"<home>", 102:"<home>",105:"<left>",106:"<right>",103:"<up>",108:"<down>",
    111:"<delete>", 110:"<insert>",  72:"<pgup>",  79:"<pgdn>",
}

# macOS / Quartz keyCode (ANSI layout)
MAC_KEYMAP: Dict[int, str] = {
    # letters
    12:"q",13:"w",14:"e",15:"r",17:"t",16:"y",32:"u",34:"i",31:"o",35:"p",
     0:"a", 1:"s", 2:"d", 3:"f", 5:"g", 4:"h",38:"j",40:"k",37:"l",
     6:"z", 7:"x", 8:"c", 9:"v",11:"b",45:"n",46:"m",
    # digits / symbols
    18:"1",19:"2",20:"3",21:"4",23:"5",22:"6",26:"7",28:"8",25:"9",29:"0",
    27:"-",24:"=",33:"[",30:"]",42:"\\",41:"'",39:"`",43:",",47:".",44:"/",
    # function row (10.15+ uses extended codes but these work)
    122:"<f1>",120:"<f2>",99:"<f3>",118:"<f4>",96:"<f5>",97:"<f6>",98:"<f7>",100:"<f8>",101:"<f9>",109:"<f10>",103:"<f11>",111:"<f12>",
    # control / modifiers
    56:"<shift>",60:"<shift_r>",59:"<ctrl>",62:"<ctrl_r>",58:"<alt>",61:"<alt_r>",55:"<cmd>",54:"<cmd_r>",
    51:"<backspace>",48:"<tab>",36:"<enter>",49:"<space>",57:"<caps_lock>",
    115:"<home>",116:"<pgup>",119:"<pgdn>",121:"<end>",123:"<left>",124:"<right>",125:"<down>",126:"<up>",
    117:"<delete>", 114:"<insert>",
}

MAP_BY_OS = {
    "linux": LINUX_KEYMAP,
    "macos": MAC_KEYMAP,
    "darwin": MAC_KEYMAP,  # alias for platform.system()
}

# ------------------------------------------------------------------
# utils class
# ------------------------------------------------------------------
class Utils:
    """Utility wrapper for keystroke SQLite db → pandas DataFrame."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_path = Path(__file__).resolve().parent / "keydb" / "keys.db"
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(self.db_path)
        self.df = self._load()

    # ---------- internal ----------
    def _load(self) -> pd.DataFrame:
        con = sqlite3.connect(self.db_path)
        df  = pd.read_sql_query("SELECT ts_us, code, os FROM keystrokes", con)
        con.close()
        df["timestamp"] = pd.to_datetime(df["ts_us"], unit="us")
        df["key"]       = df.apply(self._code_to_key, axis=1)
        return df

    @staticmethod
    def _unknown(code: int) -> str:  # helper for unmapped codes
        return f"<unk:{code}>"

    def _code_to_key(self, row) -> str:
        return MAP_BY_OS.get(row["os"].lower(), {}).get(row["code"], self._unknown(row["code"]))

    # ---------- public ----------
    def get_dataframe(self) -> pd.DataFrame:
        return self.df.copy()

    def refresh(self):
        self.df = self._load()

    def to_sequences(self) -> pd.DataFrame:
        return self.df[["timestamp", "key"]].copy()
