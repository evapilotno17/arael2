import sys, signal, numpy as np
from datetime import datetime
import time
import numpy as np
import plotext as plt
from rich.live import Live
from rich.console import Console

ROLLING_WINDOW = 120
UPDATE_INTERVAL = 0.1  # seconds

console = Console()
data = [0] * ROLLING_WINDOW

from keylogger.db import SessionLocal, Keystroke

AVG_CHARS_PER_WORD = 5
ROLLING_WINDOW     = 120 # number of seconds on the X axis
QUERY_BATCH        = 30
UPDATE_INTERVAL_MS = 100

db = SessionLocal()

console = Console()
data = [0] * ROLLING_WINDOW

def get_wpm():
    latest_batch_size_rows = (db.query(Keystroke.ts_us)
                                .order_by(Keystroke.ts_us.desc())
                                .limit(QUERY_BATCH)
                                .all())
    # db.query[i] -> tuple of the form (ts,)
    # print(latest_batch_size_rows)
    if len(latest_batch_size_rows) < 2:
        return 0.0
    # return (len(latest_batch_size_rows), latest_batch_size_rows[-1])
    ts_prev = datetime.fromtimestamp(latest_batch_size_rows[-1][0] / 1_000_000)
    ts_now = datetime.now()
    diff = (ts_now - ts_prev).total_seconds()

    return diff
    kps = len(latest_batch_size_rows) / diff
    wpm = (kps * 60) / AVG_CHARS_PER_WORD
    return wpm

ii = 0
try:
    while True:
        data.pop(0)
        data.append(get_wpm())
        # plt.clear_data()
        # plt.plot(data)
        # plt.ylim(0, 160)
        # plt.title("Live WPM")
        # print("\033[H\033[J", end="")  # clear terminal
        # plt.show()
        time.sleep(UPDATE_INTERVAL)
        print(f"RUNNING::::: {get_wpm()}")
        ii+=1
except KeyboardInterrupt:
    print("\nExiting.")


# with Live(console=console, refresh_per_second=1/UPDATE_INTERVAL):
#     while True:
#         data.pop(0)
#         data.append(get_wpm())
#         plt.clear_data()
#         plt.plot(data)
#         plt.ylim(0, 160)
#         plt.title("Live WPM")
#         # plt.colorless()
#         # canvas = plt.build(show=False)
#         canvas = plt.build()
#         console.print(canvas)
#         time.sleep(UPDATE_INTERVAL)
