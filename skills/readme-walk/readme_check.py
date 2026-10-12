#!/usr/bin/env python3
"""readme_check: static first pass over a README before an agent (or a person) tries to follow it.

Extracts the runnable steps in order and flags the things newcomers trip on: prompts pasted into
commands, unexplained placeholders, smart quotes, broken relative links and anchors, tools that
aren't installed, machine-specific paths, a missing "what is this" sentence, a long quick start.

Usage: python3 readme_check.py [README.md] [--json] [--root DIR] [--no-which]
Exit status: 0 no errors, 1 at least one error-level finding, 2 usage error.
"""
import argparse
import json
import os
import re
import shutil
import sys
import unicodedata

__version__ = "0.1.0"

SHELL_LANGS = {"bash", "sh", "shell", "zsh", "console", "terminal", "shell-session", "powershell", "ps1", "cmd", "fish"}
FENCE_RE = re.compile(r"^(\s*)(```+|~~~+)\s*([\w+-]*)[^\n]*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|!\[[^\]]*\]\(([^)\s]+)\)")
PLACEHOLDER_RE = re.compile(
    r"<(?:your|my|insert|path|token|api|key|user|username|name|project|repo|org|host|port|version|id|password|secret|email|url|dir)[\w\- ]*>"
    r"|\b(?:YOUR|MY)_[A-Z0-9_]+\b|\bxxx+\b|\bchangeme\b|\bTODO\b",
    re.I,
)
SMART_RE = re.compile(r"[\u2018\u2019\u201c\u201d\u2013\u2014\u00a0]")
ABS_PATH_RE = re.compile(r"(?:/Users/[\w.-]+|/home/[\w.-]+|C:\\Users\\[\w.-]+)")
PROMPT_RE = re.compile(r"^\s*(?:\$|>|PS [^>]*>|%|❯|➜)\s+")
QUICKSTART_RE = re.compile(r"quick\s*-?start|getting started|install|usage|setup|快速", re.I)
SHELL_BUILTINS = {
    "cd", "export", "echo", "source", ".", "set", "unset", "alias", "exit", "if", "then", "fi", "for", "do", "done",
    "while", "case", "esac", "true", "false", "test", "[", "eval", "exec", "read", "printf", "pwd", "type", "ulimit",
    "umask", "wait", "trap", "shift", "local", "function", "return", "else", "elif", "time", "env", "sudo", "\\",
}


def slugify(text):
    """GitHub-style heading anchor."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[`*_~]|\[([^\]]*)\]\([^)]*\)", r"\1", text).strip().lower()
    out = []
    for ch in text:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch == " ":
            out.append("-")
        elif unicodedata.category(ch).startswith("L") or unicodedata.category(ch).startswith("N"):
            out.append(ch)
    return "".join(out)


def parse(text):
    """Return (blocks, headings, prose_lines). blocks: dicts with lang, code, line, section."""
    blocks, headings, prose = [], [], []
    lines = text.split("\n")
    i, section = 0, ""
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if m:
            fence, lang, start = m.group(2), m.group(3).lower(), i + 1
            body = []
            i += 1
            close = re.compile(r"^\s*" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*$")
            while i < len(lines) and not close.match(lines[i]):
                body.append(lines[i])
                i += 1
            blocks.append({"lang": lang, "code": "\n".join(body), "line": start, "section": section})
            i += 1
            continue
        h = HEADING_RE.match(lines[i])
        if h:
            section = h.group(2)
            headings.append({"level": len(h.group(1)), "text": section, "line": i + 1})
        else:
            prose.append((i + 1, lines[i]))
        i += 1
    return blocks, headings, prose


def is_shell(block):
    if block["lang"] in SHELL_LANGS:
        return True
    if block["lang"] == "":
        code_lines = [ln for ln in block["code"].split("\n") if ln.strip()]
        if not code_lines:
            return False
        if PROMPT_RE.match(code_lines[0]):
            return True
        # untagged block under an install/usage heading that looks like command lines
        looks_cmd = all(re.match(r"^\s*[\w./~-]+(\s|$)", ln) and not ln.rstrip().endswith((":", "{", ";", ","))
                        for ln in code_lines)
        return bool(QUICKSTART_RE.search(block["section"] or "")) and looks_cmd and len(code_lines) <= 10
    return False


def commands(block):
    """Split a shell block into commands, joining backslash continuations, dropping comments and output."""
    cmds, cur, has_prompts = [], "", any(PROMPT_RE.match(ln) for ln in block["code"].split("\n"))
    for ln in block["code"].split("\n"):
        if has_prompts and not cur and not PROMPT_RE.match(ln):
            continue  # console output line
        ln = PROMPT_RE.sub("", ln, count=1) if not cur else ln
        if ln.rstrip().endswith("\\"):
            cur += ln.rstrip()[:-1] + " "
            continue
        cur += ln
        stripped = cur.strip()
        if stripped and not stripped.startswith("#"):
            cmds.append(stripped)
        cur = ""
    return cmds


def first_tool(cmd):
    tokens = re.split(r"\s+", re.sub(r"^(?:[A-Z_][A-Z0-9_]*=\S*\s+)+", "", cmd.strip()))
    while tokens and tokens[0] in ("sudo", "env", "time", "exec", "nohup", "command"):
        tokens = tokens[1:]
    if not tokens:
        return None
    tool = tokens[0]
    if tool in SHELL_BUILTINS or tool.startswith(("./", "/", "~", "$", "(", "{")) or "=" in tool:
        return None
    return tool


def check(path, root=None, use_which=True):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    root = root or os.path.dirname(os.path.abspath(path))
    blocks, headings, prose = parse(text)
    findings, steps = [], []

    def add(level, line, rule, msg):
        findings.append({"level": level, "line": line, "rule": rule, "message": msg})

    # what is it? some prose before the first code block / second heading
    first_code = blocks[0]["line"] if blocks else 10 ** 9
    intro = [ln for n, ln in prose if n < first_code and ln.strip() and not ln.strip().startswith(("!", "[!", "<", "|", "---"))
             and len(re.sub(r"\[[^\]]*\]\([^)]*\)|[*_`>#-]", "", ln).split()) >= 6]
    if not intro:
        add("error", 1, "no-intro", "no sentence explaining what this is before the first code block")

    anchors = {slugify(h["text"]) for h in headings}
    seen_tools = {}
    for b in blocks:
        if not is_shell(b):
            continue
        if any(PROMPT_RE.match(ln) for ln in b["code"].split("\n") if ln.strip()) and b["lang"] not in ("console", "shell-session"):
            add("warn", b["line"], "prompt-in-command",
                "command lines start with a prompt ($, >, %); copy-paste will fail. Drop the prompt or tag the block `console`")
        for offset, ln in enumerate(b["code"].split("\n")):
            n = b["line"] + offset + 1
            if SMART_RE.search(ln):
                add("error", n, "smart-quotes", f"typographic quote/dash or non-breaking space in a command: {ln.strip()[:60]!r}")
            for ph in PLACEHOLDER_RE.findall(ln):
                add("warn", n, "placeholder", f"placeholder {ph!r}: say where the value comes from, or give a working default")
            if ABS_PATH_RE.search(ln):
                add("warn", n, "machine-path", f"machine-specific path: {ABS_PATH_RE.search(ln).group(0)}")
            if re.search(r"curl[^|]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b", ln):
                add("info", n, "pipe-to-shell", "curl | sh: offer a way to inspect or verify the script")
        for cmd in commands(b):
            steps.append({"n": len(steps) + 1, "line": b["line"], "section": b["section"], "command": cmd})
            tool = first_tool(cmd)
            if tool:
                seen_tools.setdefault(tool, b["line"])

    if use_which:
        own = {slugify(h["text"]) for h in headings if h["level"] == 1}
        for tool, line in seen_tools.items():
            if tool.lower() not in own and shutil.which(tool) is None:
                add("warn", line, "missing-tool", f"`{tool}` is not installed here; is it listed as a prerequisite?")

    # links
    for n, ln in enumerate(text.split("\n"), 1):
        for m in LINK_RE.finditer(ln):
            target = m.group(2) or m.group(3)
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                continue
            if target.startswith("#"):
                if target[1:].lower() not in anchors:
                    add("error", n, "broken-anchor", f"link to #{target[1:]} but no such heading")
                continue
            rel = target.split("#")[0].split("?")[0]
            if rel and not os.path.exists(os.path.join(root, rel.lstrip("/"))):
                add("error", n, "broken-link", f"relative link to {rel} but the file does not exist")

    # quick start length
    qs = [s for s in steps if QUICKSTART_RE.search(s["section"] or "")]
    if len(qs) > 5:
        add("info", qs[0]["line"], "long-quickstart", f"quick start has {len(qs)} commands; consider a shorter happy path")
    if not steps:
        add("warn", 1, "no-steps", "no shell code blocks found: how does someone run this?")

    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return {"file": os.path.basename(path), "steps": steps, "tools": sorted(seen_tools), "findings": findings}


def render(result, color):
    c = (lambda code, s: f"\x1b[{code}m{s}\x1b[0m") if color else (lambda code, s: s)
    lvl = {"error": "31;1", "warn": "33", "info": "36"}
    out = [c("1", f"readme_check {result['file']}") + f"  ·  {len(result['steps'])} steps  ·  tools: {', '.join(result['tools']) or '-'}", ""]
    out.append(c("1", "Steps a newcomer will run, in order"))
    for s in result["steps"]:
        out.append(f"  {s['n']:>2}. {s['command'][:96]}" + c("90", f"   (L{s['line']} · {s['section'] or 'top'})"))
    out.append("")
    out.append(c("1", "Findings"))
    if not result["findings"]:
        out.append("  none")
    for f in result["findings"]:
        tag = c(lvl[f["level"]], f["level"].ljust(5))
        out.append(f"  {tag} L{f['line']:<4} {f['rule']:<18} {f['message']}")
    counts = {k: sum(1 for f in result["findings"] if f["level"] == k) for k in ("error", "warn", "info")}
    out.append("")
    out.append(f"{counts['error']} errors · {counts['warn']} warnings · {counts['info']} notes")
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(prog="readme_check", description=__doc__.split("\n\n")[0])
    p.add_argument("readme", nargs="?", default="README.md")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--root", help="directory relative links resolve against (default: the README's directory)")
    p.add_argument("--no-which", action="store_true", help="don't check whether tools are installed")
    p.add_argument("--color", action="store_true", help="force colour")
    p.add_argument("--version", action="version", version=f"readme_check {__version__}")
    a = p.parse_args(argv)
    if not os.path.isfile(a.readme):
        print(f"readme_check: no such file: {a.readme}", file=sys.stderr)
        return 2
    result = check(a.readme, a.root, use_which=not a.no_which)
    if a.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render(result, a.color or (sys.stdout.isatty() and not os.environ.get("NO_COLOR"))))
    return 1 if any(f["level"] == "error" for f in result["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
