import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skills", "readme-walk"))

import readme_check as rc  # noqa: E402


def write(text, files=()):
    d = tempfile.mkdtemp()
    for f in files:
        os.makedirs(os.path.dirname(os.path.join(d, f)) or d, exist_ok=True)
        open(os.path.join(d, f), "w").close()
    p = os.path.join(d, "README.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def rules(result):
    return sorted({f["rule"] for f in result["findings"]})


GOOD = """# demo

A tiny command line tool that prints the current weather for any city.

## Quick start

```bash
pip install demo
demo --city Berlin
```

See [the docs](docs/usage.md) and [Quick start](#quick-start).
"""


class CheckTests(unittest.TestCase):
    def test_clean_readme(self):
        r = rc.check(write(GOOD, ["docs/usage.md"]), use_which=False)
        self.assertEqual(r["findings"], [])
        self.assertEqual([s["command"] for s in r["steps"]], ["pip install demo", "demo --city Berlin"])

    def test_bad_example(self):
        r = rc.check(os.path.join(ROOT, "examples", "bad-README.md"), use_which=False)
        self.assertEqual(rules(r), ["broken-anchor", "broken-link", "long-quickstart", "machine-path",
                                    "no-intro", "placeholder", "prompt-in-command", "smart-quotes"])
        self.assertEqual(r["steps"][0]["command"], "git clone https://github.com/example/tinynotes")
        self.assertIn("tinynotes add “first note” --dir /Users/alice/notes", [s["command"] for s in r["steps"]])

    def test_console_output_lines_are_not_steps(self):
        text = "# x\n\nThis is a tool that does a useful thing for people.\n\n```console\n$ x --version\nx 1.0\n```\n"
        r = rc.check(write(text), use_which=False)
        self.assertEqual([s["command"] for s in r["steps"]], ["x --version"])
        self.assertNotIn("prompt-in-command", rules(r))

    def test_continuations_and_comments(self):
        text = GOOD + "\n```sh\n# comment\ndocker run \\\n  --rm demo\n```\n"
        r = rc.check(write(text, ["docs/usage.md"]), use_which=False)
        self.assertIn("docker run    --rm demo", [s["command"] for s in r["steps"]])

    def test_missing_tool(self):
        text = GOOD + "\n```bash\ndefinitely-not-a-real-tool-xyz --go\n```\n"
        r = rc.check(write(text, ["docs/usage.md"]))
        self.assertIn("missing-tool", rules(r))
        self.assertIn("definitely-not-a-real-tool-xyz", r["tools"])

    def test_first_tool(self):
        self.assertEqual(rc.first_tool("FOO=1 sudo npm i"), "npm")
        self.assertIsNone(rc.first_tool("cd x"))
        self.assertIsNone(rc.first_tool("./run.sh"))

    def test_slugify(self):
        self.assertEqual(rc.slugify("Quick start"), "quick-start")
        self.assertEqual(rc.slugify("What's `new` in v2.0?"), "whats-new-in-v20")
        self.assertEqual(rc.slugify("中文 说明"), "中文-说明")

    def test_nested_fences(self):
        text = "# x\n\nThis is a tool that does a useful thing for people.\n\n````md\n```bash\nnot-a-step\n```\n````\n"
        r = rc.check(write(text), use_which=False)
        self.assertEqual(r["steps"], [])

    def test_cli_exit_and_json(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = rc.main([os.path.join(ROOT, "examples", "bad-README.md"), "--json", "--no-which"])
        self.assertEqual(code, 1)
        self.assertIn("findings", json.loads(out.getvalue()))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(rc.main([write(GOOD, ["docs/usage.md"]), "--no-which"]), 0)
            self.assertEqual(rc.main(["/nonexistent/README.md"]), 2)


if __name__ == "__main__":
    unittest.main()
