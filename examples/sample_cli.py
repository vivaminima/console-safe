#!/usr/bin/env python3
"""A tiny report tool with the classic mistake: it prints characters that some consoles cannot hold.
Used as the sample for Console Safe. Run it by itself and it looks fine."""
import sys


def render(done, total):
    print("Weekly report \u2014 Acme Studio")          # an em dash
    print("Files checked: %d of %d" % (done, total))
    print("Status: all good \u2713")                    # a check mark


def main():
    render(12, 12)
    return 0


if __name__ == "__main__":
    sys.exit(main())
