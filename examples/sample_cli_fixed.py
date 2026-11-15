#!/usr/bin/env python3
"""The same tool with fix 2 applied: one reconfigure call at the start, and nothing can crash on output."""
import sys


def render(done, total):
    print("Weekly report \u2014 Acme Studio")
    print("Files checked: %d of %d" % (done, total))
    print("Status: all good \u2713")


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    render(12, 12)
    return 0


if __name__ == "__main__":
    sys.exit(main())
