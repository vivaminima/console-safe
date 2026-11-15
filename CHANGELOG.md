# Changelog

## 1.0.0
First release.

- `consolesafe.py -- COMMAND`: runs a Python command once per encoding (default `utf-8`, `cp949`, `ascii`) by
  setting `PYTHONIOENCODING` with the output captured, and prints one table: exit code and OK / CRASH / DIFFERENT.
- The utf-8 run is the yardstick for the exit code.
- `--encodings` and `--timeout`. Exit code 1 when a run did not behave like the utf-8 run.
- Two sample tools in `examples/`: one that crashes, one with the fix.
- 20 tests.
