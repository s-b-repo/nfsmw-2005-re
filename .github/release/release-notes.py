#!/usr/bin/env python3
"""release-notes.py <prev-tag|none> — emit grouped Markdown release notes for the
commits in prev..HEAD (or all history when prev is 'none'), classified by
Conventional-Commit type. Works with direct-to-main commits, not just PRs.

Release-bump commits (`chore(release): ...`) and bot authors are excluded.
"""
import re
import subprocess
import sys

prev = sys.argv[1] if len(sys.argv) > 1 else "none"
rng = [] if prev in ("", "none") else [f"{prev}..HEAD"]

raw = subprocess.run(
    ["git", "log", "--no-merges", "--format=%H%x1f%h%x1f%s%x1f%an", *rng],
    capture_output=True, text=True,
).stdout

GROUPS = [
    ("🚀 Features", re.compile(r"^feat(\([^)]*\))?!?:", re.I)),
    ("🐛 Fixes", re.compile(r"^fix(\([^)]*\))?!?:", re.I)),
    ("🔒 Security", re.compile(r"^(sec|security)(\([^)]*\))?!?:", re.I)),
    ("⚡ Performance", re.compile(r"^perf(\([^)]*\))?!?:", re.I)),
    ("📚 Documentation", re.compile(r"^docs(\([^)]*\))?!?:", re.I)),
    ("♻️ Refactoring", re.compile(r"^refactor(\([^)]*\))?!?:", re.I)),
]
OTHER = "🧰 Other changes"

buckets: dict[str, list[str]] = {t: [] for t, _ in GROUPS}
buckets[OTHER] = []
breaking: list[str] = []

for line in raw.splitlines():
    if not line.strip():
        continue
    parts = line.split("\x1f")
    if len(parts) != 4:
        continue
    _full, short, subject, author = parts
    if re.match(r"^chore\(release\)", subject):
        continue
    if re.search(r"github-actions|dependabot", author, re.I):
        continue
    entry = f"- {subject} (`{short}`)"
    if re.match(r"^[a-zA-Z]+(\([^)]*\))?!:", subject):
        breaking.append(entry)
    placed = False
    for title, rx in GROUPS:
        if rx.match(subject):
            buckets[title].append(entry)
            placed = True
            break
    if not placed:
        buckets[OTHER].append(entry)

out: list[str] = []
if breaking:
    out.append("### ⚠️ BREAKING CHANGES")
    out.extend(breaking)
    out.append("")
for title, _ in GROUPS:
    if buckets[title]:
        out.append(f"### {title}")
        out.extend(buckets[title])
        out.append("")
if buckets[OTHER]:
    out.append(f"### {OTHER}")
    out.extend(buckets[OTHER])
    out.append("")

if not any(buckets.values()) and not breaking:
    out.append("_No notable changes._")
    out.append("")

print("\n".join(out).rstrip() + "\n")
