---
name: readme-walk
description: Walk a project's README like a first-time user in a clean scratch copy, execute every step literally, and write a friction log (worked / had to guess / blocked) with concrete README fixes. Use when asked to test, review or "dogfood" a README, docs, install instructions or a quick start, or before publishing/releasing a project.
---

# readme-walk

You are a newcomer who has never seen this project. Your only knowledge is the README. The goal is to
find where a real person would get stuck, not to prove the project works.

## Rules

1. **Only the README.** Do not read source files, scripts, Makefiles, CI configs or other docs unless
   the README links to them and tells the reader to read them. If you need knowledge the README does
   not give, that is a finding.
2. **Literal execution.** Copy commands exactly as written, including their mistakes. If a command
   fails, you may make *one* obvious newcomer-level fix (the kind a person would find in a minute of
   searching) and record it as a guess. Never fix it using knowledge from the source code.
3. **Clean copy, never the original.** Work in a scratch directory. Never modify the user's checkout.
4. **No side effects outside the scratch dir.** Don't publish, push, deploy, send email, create
   accounts, enter real credentials or spend money. If a step needs a secret, an account or paid API
   access, stop that path and record it as `blocked: needs <what>`. Ask before installing anything
   globally (system packages, global npm/pip installs); prefer a local venv / `npx` / project-local
   install if the README allows it.
5. **Time-box.** Stop a step after ~3 minutes of trying or 2 failed guesses. Mark it blocked and move on
   to the next step if it is independent.

## Procedure

1. **Static pass.** Run the bundled checker (it lives next to this file):
   `python3 <this skill's directory>/readme_check.py README.md`
   It lists the runnable steps in order and flags prompts in commands, placeholders, smart quotes,
   broken links/anchors, missing tools, machine-specific paths and a missing intro. Keep its output.
2. **Scratch copy.** Create a temp dir and get the project the way a newcomer would:
   - if the README says `git clone <url>` and the repo is local, clone the local checkout instead
     (`git clone <path-to-repo> <scratch>/<name>`), so only committed files are present;
   - otherwise copy the committed tree (`git archive HEAD | tar -x -C <scratch>/<name>`).
   Run every later step from there.
3. **Read the top like a stranger.** Before running anything, write down in one sentence what you think
   the project does and who it is for, using only the first screen of the README. If you can't, that is
   the first finding.
4. **Walk.** For each step in README order, run it and record:
   - `ok` it worked as written;
   - `guess` it worked only after you changed something or inferred something unstated (say what);
   - `blocked` you could not get past it (say why and what you tried);
   - `skip` it doesn't apply (other OS, optional) — say why.
   Note anything confusing even when the step worked: unexplained output, unstated wait times,
   which directory you're supposed to be in, files the README assumes exist.
5. **Verify the promise.** If the README claims an outcome ("you should see…", a screenshot, "open
   localhost:3000"), check you actually got it.
6. **Clean up** the scratch directory and any processes you started.

## Output: write `README-FRICTION.md` in the scratch dir, then show it to the user

```markdown
# README walk: <project> (<date>, <OS>, <tool versions that mattered>)

**Verdict:** <reached the promised outcome? yes / partly / no> in <N> steps, <M> guesses, <K> blockers.
**What I understood from the first screen:** <one sentence> (<accurate / wrong / couldn't tell>)

| # | README step | result | what happened |
|---|---|---|---|
| 1 | `git clone …` | ok | |
| 2 | `npm install` | guess | needed Node ≥ 20, README doesn't say; used 22 |
| 3 | `cp env.example .env` | blocked | env.example isn't in the repo |

## Static check
<paste the readme_check findings, or "none">

## Suggested README fixes (most impact first)
1. <concrete edit, with the exact text to add or change>
2. …
```

Do not edit the real README unless the user asks; offer the fixes as a patch instead.
