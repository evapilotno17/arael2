#!/usr/bin/env python3

import glob
import os
import platform
import signal
import subprocess
import argparse
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------
# config – edit if your tree layout changes
# --------------------------------------------------------------------
LINUX_BIN  = Path(__file__).parent.with_name("linux") / "keylog.exe"      # compiled binary
MACOS_BIN  = Path(__file__).parent.with_name("macos") / "keylog.exe"      # compiled binary
PID_FILE   = Path(__file__).with_name(".keylog.pid")           # store child pid
# --------------------------------------------------------------------


def detect_os() -> str:
    """return 'linux' or 'macos' (darwin). exit for anything else."""
    name = platform.system().lower()
    if name.startswith("linux"):
        return "linux"
    if name.startswith("darwin"):
        return "macos"
    sys.exit(f"unsupported os: {platform.system()}")


def find_keyboard_device() -> str:
    """for linux: pick the first by‑path symlink ending in -kbd."""
    paths = sorted(glob.glob("/dev/input/by-path/*-kbd"))
    if not paths:
        sys.exit("no keyboard event device found (glob /dev/input/by-path/*-kbd)")
    return os.path.realpath(paths[0])


def is_running() -> bool:
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text())
            os.kill(pid, 0)        # check signal 0
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
            PID_FILE.unlink(missing_ok=True)
            return 0
    return 0


def start(verbose=True):
    if is_running():
        print("keylogger already running")
        return

    os_type = detect_os()
    if os_type == "linux":
        bin_path = LINUX_BIN
        device   = find_keyboard_device()
        cmd      = [str(bin_path), device]
        sudo     = True
    else:  # macos
        bin_path = MACOS_BIN
        cmd      = [str(bin_path)]
        sudo     = False           # not needed; event‑tap runs as user

    if not bin_path.exists():
        sys.exit(f"binary not found: {bin_path}. compile it first.")

    if sudo:
        cmd.insert(0, "sudo")

    print(cmd)

    redir = None if verbose else subprocess.DEVNULL
    proc = subprocess.Popen(
        cmd,
        stdout=redir,
        stderr=redir,
        start_new_session=True,    # decouple from this tty
    )

    PID_FILE.write_text(str(proc.pid))
    time.sleep(0.3)
    if proc.poll() is not None:
        PID_FILE.unlink(missing_ok=True)
        sys.exit("keylogger failed to start (check binary manually)")
    print(f"arael has awakened and is running at [{proc.pid}] ({os_type})")


def stop():
    if not PID_FILE.exists():
        print("no pidfile → not running?")
        return
    pid = int(PID_FILE.read_text())
    try:
        os.kill(pid, signal.SIGINT)
    except ProcessLookupError:
        print("process already gone")
    PID_FILE.unlink(missing_ok=True)
    print("keylogger stopped")


def status():
    pid = is_running()
    print(f"arael is running at pid {pid}" if pid else "arael is not running")

def help():
    helpstr = """
        usage:
            help - displays this help message
            start - starts the keylogger
                ->flags 
                (--verbose | prints logged keystrokes to the terminal)
                (--live | starts a live typing speed monitor)
            stop - stops the keylogger
            status - checks if the keylogger is running
            live - starts a live typing speed graph (arael should already be running for this)
            logs - generates and dumps logs in a human readable format - by default, it regenerates logs only for today
                -> flags
                (--all | regenerates logs for ALL days)
                (--days X | regenerates logs for the last X days)
    """
    print(helpstr)


def main():

    # if len(sys.argv) < 2 or sys.argv[1] not in {"start", "stop", "status"}:
    #     help()
    #     sys.exit(1)
    # {"help":help, "start": start, "stop": stop, "status": status}[sys.argv[1]]()

    # commands = "sudo /home/evapilotno17/central_dogma/arael2/linux/keylog.exe /dev/input/event3".split(' ')
    # print(commands)

    # subprocess.run(commands)

    parser = argparse.ArgumentParser(prog="Arael", description="a keylogger <3")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # start
    start_parser = subparsers.add_parser("start", help="awaken arael")
    start_parser.add_argument("--verbose", action="store_true", help="print captured keystrokes to terminal")
    start_parser.add_argument("--live", action="store_true", help="start a live wpm tracking graph")

    # stop
    stop_parser = subparsers.add_parser("stop", help="kill the arael subprocess") 

    # status
    status_parser = subparsers.add_parser("status", help="check keylogger status")

    # live
    live_parser = subparsers.add_parser("live", help="spawn a live words per minute graph")

    # logs
    logs_parser = subparsers.add_parser("logs", help="create and dump .txt readable logs at ./logs")
    logs_parser.add_argument("--all", action="store_true", help="regenerate ALL logs")
    logs_parser.add_argument("--days", help="--days X: regenerate logs for X days")

    args = parser.parse_args()
    command = args.command
    kwargs = vars(args)

    print(kwargs)

    print(command)

if __name__ == "__main__":
    main()
