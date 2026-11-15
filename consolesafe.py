#!/usr/bin/env python3
"""Console Safe - run a Python command-line tool under several console encodings and see where it dies.

  consolesafe.py -- python mytool.py --report
  consolesafe.py --encodings cp949,cp1252,ascii,utf-8 --timeout 30 -- python mytool.py

A Python program that prints a character its output encoding cannot hold - an em dash, a check
mark, a non-English name - stops with UnicodeEncodeError. On your own screen you may never see
it; it happens when the output is redirected, piped into another program, or captured by a CI
job or an agent on a Windows machine with a legacy code page. This runs the command once per
encoding (by setting PYTHONIOENCODING, with the output captured) and prints one table.

It only runs the command you give it. Standard library only. No network.
"""
from __future__ import annotations

import argparse
import codecs
import os
import re
import subprocess
import sys

VERSION = "1.0.0"
TOOL = "Console Safe"
DEFAULT_ENCODINGS = ("utf-8", "cp949", "ascii")
BASELINE = "utf-8"
UNICODE_ERROR = re.compile(r"^(Unicode(?:Encode|Decode|Translate)?Error): (.*)$", re.M)
LOOKUP_ERROR = re.compile(r"^LookupError: unknown encoding: (.*)$", re.M)


def normalise(name):
    """The codec's own name for an encoding, or None when Python does not know it."""
    try:
        return codecs.lookup(name.strip()).name
    except (LookupError, TypeError):
        return None


def run_once(command, encoding, timeout, cwd=None, stdin_bytes=None):
    """Run the command with its standard streams in one encoding. Returns what happened, as a dict."""
    env = dict(os.environ, PYTHONIOENCODING=encoding, PYTHONUTF8="0")
    env.pop("PYTHONLEGACYWINDOWSSTDIO", None)
    try:
        done = subprocess.run(command, capture_output=True, env=env, timeout=timeout, cwd=cwd,
                              input=stdin_bytes if stdin_bytes is not None else b"")
    except FileNotFoundError:
        return {"encoding": encoding, "exit": None, "result": "NOT STARTED", "detail": "command not found: %s" % command[0],
                "stderr": "", "stdout_bytes": 0}
    except subprocess.TimeoutExpired:
        return {"encoding": encoding, "exit": None, "result": "TIMEOUT", "detail": "no answer after %g s" % timeout,
                "stderr": "", "stdout_bytes": 0}
    except OSError as exc:
        return {"encoding": encoding, "exit": None, "result": "NOT STARTED", "detail": type(exc).__name__,
                "stderr": "", "stdout_bytes": 0}
    try:                                                  # the child wrote its errors in the encoding under test
        stderr = done.stderr.decode(encoding, "replace")
    except LookupError:
        stderr = done.stderr.decode("utf-8", "replace")
    crash = UNICODE_ERROR.findall(stderr)
    lookup = LOOKUP_ERROR.search(stderr)
    if crash:
        result, detail = "CRASH", "%s: %s" % crash[-1]
    elif lookup:
        result, detail = "CRASH", "LookupError: unknown encoding: %s" % lookup.group(1)
    else:
        result, detail = "OK", ""
    return {"encoding": encoding, "exit": done.returncode, "result": result, "detail": detail, "stderr": stderr,
            "stdout_bytes": len(done.stdout)}


def check(command, encodings=DEFAULT_ENCODINGS, timeout=60.0, cwd=None, stdin_bytes=None):
    """Run the command under every encoding. The utf-8 run is the yardstick for the exit code."""
    names = []
    for name in encodings:
        if name not in names:
            names.append(name)
    if BASELINE not in names:
        names.insert(0, BASELINE)
    runs = [run_once(command, name, timeout, cwd, stdin_bytes) for name in names]
    base = [r for r in runs if r["encoding"] == BASELINE][0]
    for r in runs:
        if r is base:
            r["detail"] = r["detail"] or "yardstick"
        elif r["result"] == "OK" and r["exit"] != base["exit"]:
            r["result"] = "DIFFERENT"
            r["detail"] = "exit code %s, but %s with utf-8" % (r["exit"], base["exit"])
    bad = [r for r in runs if r["result"] != "OK"]
    return {"tool": TOOL, "version": VERSION, "command": list(command), "runs": runs,
            "crashed": sum(1 for r in runs if r["result"] == "CRASH"), "not_ok": len(bad), "total": len(runs)}


def command_line(command, show_paths=False):
    """The command as it is written in a report. A full path in it is cut down to its last part, so
    that a report does not carry folder names; show_paths keeps it as typed."""
    if show_paths:
        return " ".join(command)
    return " ".join(re.split(r"[\\/]", part)[-1] if os.path.isabs(part) else part for part in command)


def shorten(text, width):
    text = " ".join(text.split())
    return text if len(text) <= width else text[:width - 3] + "..."


def closing_line(report):
    """One closing line with the real numbers. Nothing when nothing crashed."""
    if not report["crashed"]:
        return None
    return ("%d of %d encodings crashed. The file and line of each crash, three fixes and a CI example are in Pro."
            % (report["crashed"], report["total"]))


def render_text(report, closing=True):
    lines = ["%s %s" % (TOOL, VERSION), "Command: %s" % command_line(report["command"], report.get("show_paths")), "",
             "%-10s %5s  %-11s %s" % ("encoding", "exit", "result", "detail")]
    for r in report["runs"]:
        lines.append("%-10s %5s  %-11s %s" % (r["encoding"], "-" if r["exit"] is None else r["exit"], r["result"],
                                              shorten(r["detail"], 100)))
    lines.append("")
    if report["not_ok"]:
        lines.append("%d of %d runs did not behave like the utf-8 run." % (report["not_ok"], report["total"]))
    else:
        lines.append("All %d runs behaved the same. That covers these encodings with captured output - nothing more."
                     % report["total"])
    line = closing_line(report) if closing else None
    if line:
        lines += ["", line]
    return "\n".join(lines)


def safe_stdio():
    """Practise what this tool preaches: never crash on a console that cannot show a character."""
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is not None and (stream.encoding or "").lower().replace("-", "").replace("_", "") != "utf8":
                stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def parse_encodings(text):
    """Comma-separated names -> (codec names, names Python does not know)."""
    good, unknown = [], []
    for raw in text.split(","):
        if not raw.strip():
            continue
        name = normalise(raw)
        if name is None:
            unknown.append(raw.strip())
        elif name not in good:
            good.append(name)
    return good, unknown


def build_parser(prog="consolesafe", version=None):
    parser = argparse.ArgumentParser(
        prog=prog, usage="%(prog)s [options] -- COMMAND [ARG ...]",
        description="Run a Python command under several console encodings and report where it crashes.")
    parser.add_argument("--encodings", default=",".join(DEFAULT_ENCODINGS),
                        help="comma-separated encodings to try (default: %s); utf-8 is always run as the yardstick"
                        % ",".join(DEFAULT_ENCODINGS))
    parser.add_argument("--timeout", type=float, default=60.0, help="seconds to wait for each run (default 60)")
    parser.add_argument("--version", action="version", version=version or "%s %s" % (TOOL, VERSION))
    parser.add_argument("command", nargs=argparse.REMAINDER, help="the command to run, after --")
    return parser


def read_command(args, parser):
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.print_usage(sys.stderr)
        print("ERROR: give the command to run after --, for example:  consolesafe.py -- python mytool.py",
              file=sys.stderr)
        return None, None
    encodings, unknown = parse_encodings(args.encodings)
    if unknown:
        print("ERROR: Python does not know the encoding %s" % ", ".join(unknown), file=sys.stderr)
        return None, None
    return command, encodings


def main(argv=None):
    safe_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    command, encodings = read_command(args, parser)
    if command is None:
        return 2
    report = check(command, encodings, args.timeout)
    print(render_text(report))
    if all(r["result"] == "NOT STARTED" for r in report["runs"]):
        return 2
    return 1 if report["not_ok"] else 0


if __name__ == "__main__":
    sys.exit(main())
