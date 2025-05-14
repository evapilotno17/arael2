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
            pid_text = PID_FILE.read_text().strip()
            
            # Special case for verbose mode
            if pid_text == "verbose_mode":
                # We can't easily check the status, so we assume it's running
                # if the PID file contains our special marker
                return True
                
            pid = int(pid_text)
            os.kill(pid, 0)  # check signal 0  
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
            PID_FILE.unlink(missing_ok=True)
            return 0
    return 0


def compile_linux_binary():
    """Compile the Linux binary if it doesn't exist."""
    bin_path = LINUX_BIN
    src_dir = bin_path.parent
    
    print(f"Compiling binary at {bin_path}...")
    try:
        # Try using the Makefile first
        result = subprocess.run(
            ["make"], 
            cwd=str(src_dir),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # If make fails, try direct gcc compilation
            print("Makefile compilation failed, trying direct gcc command...")
            compile_cmd = [
                "gcc",
                "-O2",
                "-std=c11",
                "-DDEBUG",
                "-lsqlite3",
                "keylog.c",
                "-o",
                "keylog.exe"
            ]
            result = subprocess.run(
                compile_cmd,
                cwd=str(src_dir),
                capture_output=True,
                text=True
            )
            
        if result.returncode != 0:
            print(f"Compilation failed: {result.stderr}")
            return False
            
        return bin_path.exists()
    except Exception as e:
        print(f"Error during compilation: {e}")
        return False

def start(verbose=False):
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

    # Check if binary exists, if not try to compile it
    if not bin_path.exists():
        print(f"Binary not found at {bin_path}")
        if os_type == "linux" and compile_linux_binary():
            print("Successfully compiled binary")
        else:
            sys.exit(f"Failed to compile or find binary at {bin_path}")

    if sudo:
        cmd.insert(0, "sudo")

    print(f"Starting keylogger with command: {' '.join(cmd)}")
    
    # Make a decision if we're running in directly attached (foreground) mode
    # or in background mode
    if verbose:
        # For verbose mode, run it directly as a foreground process, without Python's management
        # This is the most reliable way to see real-time output
        print("Running in verbose mode - press Ctrl+C to stop")
        print(f"Command: {' '.join(cmd)}")
        
        # Write a dummy PID file so status check works
        # We're relying on the direct process, not something we manage
        PID_FILE.write_text("verbose_mode")
        
        # Execute the command directly, replacing the current process
        # This allows output to flow directly to the terminal
        try:
            # Use os.execvp which replaces the current process with the new one
            os.execvp(cmd[0], cmd)
        except Exception as e:
            PID_FILE.unlink(missing_ok=True)
            sys.exit(f"Failed to start keylogger: {e}")
    else:
        # Non-verbose mode: run in background with no output
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # decouple from this tty
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
    
    pid_text = PID_FILE.read_text().strip()
    
    # Handle the special case for verbose mode
    if pid_text == "verbose_mode":
        print("Keylogger was started in verbose mode and is running in foreground.")
        print("Please stop it manually with Ctrl+C in the terminal where it's running.")
        return
        
    try:
        pid = int(pid_text)
        os.kill(pid, signal.SIGINT)
    except ValueError:
        print("Invalid PID format in pidfile")
    except ProcessLookupError:
        print("Process already gone")
    
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

    # Execute the appropriate function based on command
    if command == "start":
        verbose = kwargs.get("verbose", False)
        start(verbose=verbose)
    elif command == "stop":
        stop()
    elif command == "status":
        status()
    elif command == "help":
        help()
    elif command == "live":
        print("Live monitoring not implemented yet")
    elif command == "logs":
        print("Log generation not implemented yet")

if __name__ == "__main__":
    main()
