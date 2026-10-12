# README walk: port-diff (2026-10-12, macOS, Python 3.14, Node 22, git 2.x)

*A real walk, done with this skill on the README of [thinx-pro/port-diff](https://github.com/thinx-pro/port-diff)
as first published. The README was fixed afterwards based on finding 2.*

**Verdict:** reached the promised outcome (the demo report, exit status 1) in 4 steps, 1 guess, 0 blockers.
**What I understood from the first screen:** "Runs an old and a new build of a CLI on the same inputs and
reports behavior differences, for agent-driven ports." (accurate)

| # | README step | result | what happened |
|---|---|---|---|
| 1 | `pipx install git+https://github.com/thinx-pro/port-diff` | guess | `pipx: command not found`. The same line offers `pip install git+…` in a comment; used it inside a fresh venv. Installed fine, `port-diff --help` works. |
| 2 | `port-diff run --old "python3 old/tool.py {case}" --new "./target/release/tool {case}" --cases cases/` | skip | `old/tool.py`, `./target/release/tool` and `cases/` are hypothetical, but nothing says so; a newcomer may run it as-is and get a confusing failure. |
| 3 | `git clone https://github.com/thinx-pro/port-diff && cd port-diff` | ok | |
| 4 | `python3 -m port_diff run --old "python3 demo/old/wordfreq.py …" --new "node demo/new/wordfreq.js …" --cases demo/cases --norm json:files --repeat 3` | ok | Output matches the README's sample (timings differ by a few ms). Exit status 1, which the README says is expected. |

## Static check (`readme_check.py`)

```text
warn  L31   missing-tool       `pipx` is not installed here; is it listed as a prerequisite?
0 errors · 1 warnings · 0 notes
```

## Suggested README fixes (most impact first)

1. Mark the second Quick start command as a template, e.g. append
   `# replace with your old and new commands and your folder of inputs`.
2. Put the `pip` alternative on its own line instead of a trailing comment, so people without
   `pipx` see it as a first-class option.
