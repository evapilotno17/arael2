# keylogger/stream.py
import sqlite3, time
from pathlib import Path
from typing import Iterator, Tuple

Row = Tuple[int, int, int, str]   # (rowid, ts_us, code, os)

def stream(db: str | Path, poll: float = 0.05) -> Iterator[Row]:
    """
    yield keystrokes as (rowid, ts_us, code, os) the moment they land.
    `poll` is the sleep in seconds between queries (default 50 ms).
    """
    con = sqlite3.connect(
        f"file:{Path(db).resolve()}?mode=ro&cache=shared",
        uri=True,
        isolation_level=None,          # autocommit
        check_same_thread=False,
    )
    con.execute("pragma journal_mode=wal;")      # safe even read-only
    cur = con.cursor()

    last = 0
    while True:
        cur.execute(
            "select rowid, ts_us, code, os from keystrokes "
            "where rowid > ? order by rowid",
            (last,),
        )
        rows = cur.fetchall()
        if rows:
            last = rows[-1][0]
            for r in rows:
                yield r
        time.sleep(poll)
