from keylogger.db import Keystroke
# from __future__ import annotations
from pathlib import Path
from typing import Dict
from datetime import datetime
import pandas as pd
import sqlite3

def convert_to_readable_key(key: Keystroke | tuple):
    if type(key) == tuple:
        # (rowid, ts_us, code, os)
        return {
            "key": MAP_BY_OS.get(key[3], {}).get(key[2], "<unknown>"),
            "timestamp": datetime.fromtimestamp(key[1] / 1e6)
        }
    elif type(key) == Keystroke :
        return {
            "key": MAP_BY_OS.get(key.os, {}).get(key.code, "<unknown>"),
            "timestamp": datetime.fromtimestamp(key.ts_us / 1e6)
        }
    elif type(key) == dict:
        return {
            "key": MAP_BY_OS.get(key["os"], {}).get(key["code"], "<unknown>"),
            "timestamp": datetime.fromtimestamp(key["ts_us"] / 1e6)
        }
    raise ValueError("invalid keystroke")




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

WINDOWS_KEYMAP: Dict[int, str] = {
    # ─ letters ─
     81:"q", 87:"w", 69:"e", 82:"r", 84:"t", 89:"y", 85:"u", 73:"i", 79:"o", 80:"p",
     65:"a", 83:"s", 68:"d", 70:"f", 71:"g", 72:"h", 74:"j", 75:"k", 76:"l",
     90:"z", 88:"x", 67:"c", 86:"v", 66:"b", 78:"n", 77:"m",
    # ─ digits & symbols ─
     49:"1", 50:"2", 51:"3", 52:"4", 53:"5", 54:"6", 55:"7", 56:"8", 57:"9", 48:"0",
    189:"-",187:"=",219:"[",221:"]",186:";",222:"'",192:"`",188:",",190:".",191:"/",220:"\\",
    # ─ function row F1-F12 ─
    112:"<f1>",113:"<f2>",114:"<f3>",115:"<f4>",116:"<f5>",117:"<f6>",118:"<f7>",119:"<f8>",
    120:"<f9>",121:"<f10>",122:"<f11>",123:"<f12>",
    # ─ control / modifiers ─
    160:"<shift>",161:"<shift_r>",162:"<ctrl>",163:"<ctrl_r>",
    164:"<alt>",165:"<alt_r>", 91:"<gui>", 92:"<gui_r>",
     8:"<backspace>",  9:"<tab>", 13:"<enter>", 32:"<space>", 20:"<caps_lock>",
    # ─ navigation ─
     36:"<home>", 35:"<end>", 37:"<left>", 39:"<right>", 38:"<up>", 40:"<down>",
     46:"<delete>", 45:"<insert>", 33:"<pgup>", 34:"<pgdn>",
}

MAP_BY_OS = {
    "linux": LINUX_KEYMAP,
    "macos": MAC_KEYMAP,
    "darwin": MAC_KEYMAP,  # alias for platform.system()
    "windows": WINDOWS_KEYMAP,
}