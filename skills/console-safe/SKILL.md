---
name: console-safe
description: Runs a CLI under other console encodings (cp949, cp1252, ascii) and shows where it crashes or prints garbage. Use when the user asks, for example, "will my CLI break on Windows", "test console encodings", "console safe", "다른 콘솔에서 깨지는지 봐 줘".
---

# console-safe

Runs a CLI under other console encodings (cp949, cp1252, ascii) and shows where it crashes or prints garbage. A small Python tool shipped in this plugin: standard library only, nothing to install, runs locally.

## Run

Use `python` (Windows: `py -3` also works; macOS/Linux: `python3`). On Windows add `-X utf8` if the console shows broken characters.

    python "${CLAUDE_PLUGIN_ROOT}/consolesafe.py" -- <command and args>
    python "${CLAUDE_PLUGIN_ROOT}/consolesafe.py" --encodings cp949,cp1252,ascii --timeout 30 -- <command>

Run it from the user's project folder and pass the path they mean. If no path is given, ask which folder or file to check.

## Read the result

List each encoding with OK or the first crash line, then the likely fix (encoding= on open, or reconfigure stdout).

Show the tool's own output (shortened if long) and then a two- or three-line summary. Do not change the user's files unless they ask.
