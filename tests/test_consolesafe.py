"""Tests for Console Safe. Run:  python -m unittest discover -s tests"""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
ENGINE = PKG / "engine" if (PKG / "engine" / "consolesafe.py").is_file() else PKG
sys.path.insert(0, str(ENGINE))
import consolesafe as cs

PY = sys.executable
BAD = 'print("report \\u2014 done \\u2713")\n'                       # an em dash and a check mark
GOOD = 'print("report - done OK")\n'
KOREAN = 'print("\\ud55c\\uae00 \\ubcf4\\uace0\\uc11c")\n'            # fine in cp949, not in ascii
SAFE = 'import sys\nsys.stdout.reconfigure(errors="replace")\n' + BAD
EXIT3 = 'import sys\nprint("plain")\nsys.exit(3)\n'
PICKY = ('import sys\nprint("plain")\n'
         'sys.exit(0 if (sys.stdout.encoding or "").lower().replace("-", "") == "utf8" else 5)\n')
SLOW = 'import time\ntime.sleep(30)\n'
DECODE = 'b"\\xff\\xfe\\xfa".decode("utf-8")\n'


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "tool 도구"
        self.root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def script(self, text, name="tool.py"):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return [PY, str(path)]

    def results(self, command, **kw):
        report = cs.check(command, **kw)
        return report, {r["encoding"]: (r["result"], r["exit"]) for r in report["runs"]}

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cs.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()


class Check(Base):
    def test_character_the_encoding_cannot_hold_is_a_crash(self):
        report, by = self.results(self.script(BAD))
        self.assertEqual(by, {"utf-8": ("OK", 0), "cp949": ("CRASH", 1), "ascii": ("CRASH", 1)})
        self.assertEqual((report["crashed"], report["not_ok"], report["total"]), (2, 2, 3))
        detail = [r["detail"] for r in report["runs"] if r["encoding"] == "cp949"][0]
        self.assertIn("UnicodeEncodeError: 'cp949' codec can't encode character '\\u2014'", detail)

    def test_plain_ascii_output_passes_everywhere(self):
        report, by = self.results(self.script(GOOD))
        self.assertEqual(set(by.values()), {("OK", 0)})
        self.assertEqual(report["not_ok"], 0)

    def test_korean_text_passes_cp949_and_crashes_ascii(self):
        _report, by = self.results(self.script(KOREAN))
        self.assertEqual((by["cp949"], by["ascii"]), (("OK", 0), ("CRASH", 1)))

    def test_program_that_reconfigures_its_output_passes(self):
        _report, by = self.results(self.script(SAFE))
        self.assertEqual(set(by.values()), {("OK", 0)})

    def test_exit_code_is_compared_with_the_utf8_run_not_with_zero(self):
        _report, by = self.results(self.script(EXIT3))
        self.assertEqual(set(by.values()), {("OK", 3)})                         # same everywhere: fine
        report, by = self.results(self.script(PICKY))
        self.assertEqual((by["utf-8"], by["cp949"]), (("OK", 0), ("DIFFERENT", 5)))
        self.assertEqual((report["crashed"], report["not_ok"]), (0, 2))
        self.assertIn("exit code 5, but 0 with utf-8", [r["detail"] for r in report["runs"] if r["encoding"] == "cp949"][0])

    def test_decode_errors_are_crashes_too(self):
        _report, by = self.results(self.script(DECODE))
        self.assertEqual(by["utf-8"], ("CRASH", 1))

    def test_chosen_encodings_and_utf8_is_always_added(self):
        report, by = self.results(self.script(BAD), encodings=["cp1252", "latin-1", "cp1252"])
        self.assertEqual([r["encoding"] for r in report["runs"]], ["utf-8", "cp1252", "latin-1"])
        self.assertEqual((by["cp1252"][0], by["latin-1"][0]), ("CRASH", "CRASH"))  # the check mark is in neither

    def test_timeout_and_missing_command(self):
        _report, by = self.results(self.script(SLOW), timeout=0.5, encodings=["utf-8"])
        self.assertEqual(by["utf-8"], ("TIMEOUT", None))
        report, by = self.results(["no-such-program-xyz", "--help"], encodings=["utf-8", "ascii"])
        self.assertEqual(set(by.values()), {("NOT STARTED", None)})

    def test_the_command_gets_its_arguments_and_its_folder_is_not_changed(self):
        self.script('import sys\nprint(" ".join(sys.argv[1:]))\nsys.exit(len(sys.argv) - 1)\n')
        before = sorted((p.name, p.read_bytes()) for p in self.root.iterdir())
        _report, by = self.results([PY, str(self.root / "tool.py"), "a b", "--flag"])
        self.assertEqual(set(by.values()), {("OK", 2)})
        self.assertEqual(before, sorted((p.name, p.read_bytes()) for p in self.root.iterdir() if p.name != "__pycache__"))


class Cli(Base):
    def test_table_and_exit_code_1_when_something_crashes(self):
        code, out, _ = self.run_main("--", *self.script(BAD))
        self.assertEqual(code, 1)
        lines = out.split("\n")
        self.assertEqual(lines[0], "Console Safe 1.0.0")
        self.assertRegex(out, r"utf-8\s+0\s+OK\s+yardstick")
        self.assertRegex(out, r"cp949\s+1\s+CRASH\s+UnicodeEncodeError: 'cp949' codec")
        self.assertRegex(out, r"ascii\s+1\s+CRASH\s+UnicodeEncodeError: 'ascii' codec")
        self.assertIn("2 of 3 runs did not behave like the utf-8 run.", out)

    def test_closing_line_has_the_real_numbers_and_only_when_something_crashed(self):
        code, out, _ = self.run_main("--", *self.script(BAD))
        self.assertTrue(out.rstrip().endswith("2 of 3 encodings crashed. The file and line of each crash, three fixes "
                                              "and a CI example are in Pro."))
        code, out, _ = self.run_main("--", *self.script(GOOD))
        self.assertEqual(code, 0)
        self.assertNotIn("are in Pro", out)
        self.assertTrue(out.rstrip().endswith("nothing more."))
        code, out, _ = self.run_main("--", *self.script(PICKY))                  # different exit code, no crash
        self.assertEqual(code, 1)
        self.assertNotIn("are in Pro", out)

    def test_command_is_shown_without_folder_names(self):
        code, out, _ = self.run_main("--", *self.script(GOOD))
        self.assertIn("Command: %s tool.py" % Path(PY).name, out)
        self.assertNotIn(self._tmp.name, out)

    def test_clean_run_does_not_claim_more_than_it_tested(self):
        code, out, _ = self.run_main("--encodings", "cp949", "--", *self.script(GOOD))
        self.assertIn("All 2 runs behaved the same. That covers these encodings with captured output - nothing more.", out)
        for claim in ("safe on Windows", "works everywhere", "all consoles"):
            self.assertNotIn(claim, out)

    def test_usage_errors(self):
        code, out, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("give the command to run after --", err)
        code, out, err = self.run_main("--encodings", "cp949,klingon", "--", *self.script(GOOD))
        self.assertEqual(code, 2)
        self.assertIn("Python does not know the encoding klingon", err)
        self.assertEqual(self.run_main("--", "no-such-program-xyz")[0], 2)

    def test_command_without_the_double_dash_also_works(self):
        code, out, _ = self.run_main(*self.script(GOOD))
        self.assertEqual(code, 0)

    def test_the_tool_itself_survives_cp949_and_ascii_consoles(self):
        command = self.script(BAD, "보고서 도구.py")
        for enc in ("cp949", "ascii"):
            env = dict(os.environ, PYTHONIOENCODING=enc, PYTHONUTF8="0")
            r = subprocess.run([PY, str(ENGINE / "consolesafe.py"), "--"] + command, capture_output=True, env=env)
            self.assertEqual(r.returncode, 1, r.stderr)
            self.assertIn(b"2 of 3 encodings crashed.", r.stdout)
            self.assertNotIn(b"Traceback", r.stderr)

    def test_checking_itself_passes(self):
        code, out, _ = self.run_main("--", PY, str(ENGINE / "consolesafe.py"), "--version")
        self.assertEqual(code, 0, out)


class Package(unittest.TestCase):
    def test_tool_is_ascii_standard_library_and_offline(self):
        import ast
        source = (ENGINE / "consolesafe.py").read_text(encoding="utf-8")
        self.assertTrue(all(ord(c) < 128 for c in source))
        allowed = {"__future__", "argparse", "codecs", "os", "re", "subprocess", "sys"}
        for node in ast.walk(ast.parse(source)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module] if isinstance(node, ast.ImportFrom) else []
            for name in names:
                self.assertIn(name.split(".")[0], allowed)

    def test_sample_gives_the_output_the_readme_shows(self):
        if ENGINE != PKG:
            self.skipTest("free package README (this is the Pro copy)")
        r = subprocess.run([PY, str(PKG / "consolesafe.py"), "--", "python", "examples/sample_cli.py"],
                           capture_output=True, cwd=str(PKG), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        text, code = r.stdout.decode("utf-8").replace("\r\n", "\n"), r.returncode
        self.assertEqual(code, 1)
        readme = (PKG / "README.md").read_text(encoding="utf-8")
        for line in text.split("\n"):
            if line.strip():
                self.assertIn(line.rstrip(), readme, line)
        fixed = subprocess.run([PY, str(PKG / "consolesafe.py"), "--", PY, "examples/sample_cli_fixed.py"],
                               capture_output=True, cwd=str(PKG))
        self.assertEqual(fixed.returncode, 0)

    def test_readme_starts_with_the_beginner_block_and_names_only_what_was_tested(self):
        if ENGINE != PKG:
            self.skipTest("free package README (this is the Pro copy)")
        text = (PKG / "README.md").read_text(encoding="utf-8")
        first_section = next(l for l in text.splitlines() if l.startswith("## "))   # title, tagline and picture may sit above it
        self.assertEqual(first_section, "## New to this? Start here")
        for phrase in ("Who it is for", "The problem", "Code tab", "Say this to Claude", "What you get back",
                       "What we ran it on", "Windows 11", "cp949", "ascii", "utf-8", "captured"):
            self.assertIn(phrase, text)
        low = text.lower()
        for claim in ("works on all", "safe on every", "any windows", "all windows", "guarantee"):
            self.assertNotIn(claim, low)
        for word in ("re" + "fund", "money" + " back", "buy now"):         # links and prices of other tools are allowed
            self.assertNotIn(word, low)


if __name__ == "__main__":
    unittest.main()
