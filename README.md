# Console Safe

Run a Python command-line tool under several console encodings and see where it dies.

## New to this? Start here

**Who it is for.** You wrote a Python command-line tool (or Claude wrote it for you) and other people will run
it - on Windows, in a CI job, or from inside another program.

**The problem.** Your tool prints an em dash, a check mark or a name with an accent. On your screen it looks
fine. On a Windows machine with a legacy code page (Korean cp949, Western cp1252 ...), the moment the output
is redirected, piped or captured by another program, Python stops with `UnicodeEncodeError` and your tool
exits with an error after doing half its work. You find out from a user.

**Four steps in the Claude desktop app, Code tab.**

1. Unpack this ZIP. In the Code tab, choose the unpacked `console-safe` folder as the working folder.
2. Type the sentence below.
3. Claude asks to run one `python` command. Allow it. (Python 3.8 or newer must be installed; nothing else.)
4. Claude tells you under which encodings the sample tool crashes. Then point it at your own tool.

**Say this to Claude.**

> Run `python consolesafe.py -- python examples/sample_cli.py` and tell me under which encodings the sample crashes.

**What you get back.** This is what that command printed (the sample prints an em dash and a check mark):

```
Console Safe 1.0.0
Command: python examples/sample_cli.py

encoding    exit  result      detail
utf-8          0  OK          yardstick
cp949          1  CRASH       UnicodeEncodeError: 'cp949' codec can't encode character '\u2014' in position 14: illegal multiby...
ascii          1  CRASH       UnicodeEncodeError: 'ascii' codec can't encode character '\u2014' in position 14: ordinal not in ...

2 of 3 runs did not behave like the utf-8 run.

2 of 3 encodings crashed. The file and line of each crash, three fixes and a CI example are in Pro.
```

`examples/sample_cli_fixed.py` is the same tool with one line added at the start; run the command on it and
all three rows say `OK`.

## Use

```
python consolesafe.py -- python mytool.py --report
python consolesafe.py --encodings cp949,cp1252,ascii --timeout 30 -- python mytool.py
```

(`python3` on macOS and Linux.) Everything after `--` is the command, run as it is - no shell.

```
--encodings LIST   comma-separated encodings to try (default: utf-8,cp949,ascii)
--timeout SECONDS  how long to wait for each run (default 60)
```

| Result | Meaning |
|---|---|
| `OK` | The run ended like the utf-8 run: same exit code, no encoding error |
| `CRASH` | Python printed `UnicodeEncodeError` (or another Unicode error) |
| `DIFFERENT` | No encoding error, but the exit code is not the one the utf-8 run gave |
| `TIMEOUT`, `NOT STARTED` | The run did not finish, or the command could not be started |

The utf-8 run is the yardstick, so a tool that exits `1` on purpose is not reported as a problem.

Exit codes: `0` every run behaved like the utf-8 run, `1` at least one did not, `2` bad usage or the command
could not be started.

## How it works, and what that means

For each encoding the command is started with `PYTHONIOENCODING` set to it and with its output captured.
That is the situation in which these crashes happen in real life: output that goes to a file, a pipe, a CI
log or another program on a machine whose code page is that encoding.

- It only affects **Python** programs. A command that is not Python ignores `PYTHONIOENCODING`.
- It runs your command for real, once per encoding. Do not point it at a command that deletes or sends things.
- A program that sets its own output encoding (`sys.stdout.reconfigure(...)`) passes - that is the fix.
- It finds crashes on output. It does not check that the characters *look* right on a screen.

## What was tested

Exactly this, and nothing wider is claimed:

- Windows 11, Python 3.10.11.
- Encodings `utf-8`, `cp949`, `ascii`, `cp1252` and `latin-1`, set through `PYTHONIOENCODING`, with the
  command's output captured through a pipe.
- 20 tests, including running this tool itself under cp949 and ascii.

Not tested: a real console window with a legacy code page, PowerShell and cmd redirection as such, macOS,
Linux, other Python versions. A clean table means "no crash in these runs" - not "works on every console".

## Limits

- One command per call. To cover several commands (`--help`, an error path, a report), call it for each.
- A crash that only happens with certain input is found only if your command prints that input.
- `DIFFERENT` can be a real problem or a tool that is meant to behave differently; read the row.

MIT licence. See CHANGELOG.md.

## More from Vivaminima

- **Token Audit Kit ($19)** — see how many tokens your CLAUDE.md and its @imports cost before your first prompt, and a step-by-step guide to split it. Free script: https://github.com/vivaminima/context-file-audit · Paid kit: https://vivaminima.lemonsqueezy.com/checkout/buy/57973270-94ea-4cc7-bcb4-294693714087
- Free tools: [skill-audit-kit](https://github.com/vivaminima/skill-audit-kit) · [secret-map](https://github.com/vivaminima/secret-map) · [inbox-ledger](https://github.com/vivaminima/inbox-ledger) · [release-gate](https://github.com/vivaminima/release-gate) · [skill-install-gate](https://github.com/vivaminima/skill-install-gate) · [console-safe](https://github.com/vivaminima/console-safe) · [checklist-stop](https://github.com/vivaminima/checklist-stop) · [handoff-check](https://github.com/vivaminima/handoff-check) · [llm-budget-router-lite](https://github.com/vivaminima/llm-budget-router-lite) · [go-no-go-verdict-skill](https://github.com/vivaminima/go-no-go-verdict-skill) · [ai-company-starter-kit](https://github.com/vivaminima/ai-company-starter-kit) · [beginner-readme-section](https://github.com/vivaminima/beginner-readme-section)

Vivaminima is not affiliated with, endorsed by or sponsored by Anthropic.
