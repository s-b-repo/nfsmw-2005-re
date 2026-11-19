#!/usr/bin/env python3
"""bump-manifest.py — set the project's version string to match a release tag.

Usage:  python3 scripts/bump-manifest.py 1.2.3   (no leading 'v')

Best-effort and language-aware: updates whichever common manifests exist, prints
each file it changed (one per line), and exits 0 even when nothing matched so a
release is never blocked by a missing/unusual manifest. stdlib only.

Supported: Cargo.toml ([workspace.package] or [package]), package.json,
pyproject.toml ([project] or [tool.poetry]), pubspec.yaml, VERSION/VERSION.txt.
"""
import json
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit("usage: bump-manifest.py <version-without-v>")
version = sys.argv[1].lstrip("v").strip()
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    sys.exit(f"not a plain X.Y.Z version: {version!r}")

changed = []


def write(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8")
    changed.append(str(p))


def bump_table_version(text: str, headers: list[str]) -> str | None:
    """Set the first `version = "..."` inside the first matching TOML table."""
    for header in headers:
        hm = re.search(rf"(?m)^\[{re.escape(header)}\]\s*$", text)
        if not hm:
            continue
        start = hm.end()
        nxt = re.search(r"(?m)^\[", text[start:])
        end = start + nxt.start() if nxt else len(text)
        section = text[start:end]
        new_section, n = re.subn(
            r'(?m)^(\s*version\s*=\s*)"[^"]*"',
            rf'\g<1>"{version}"',
            section,
            count=1,
        )
        if n:
            return text[:start] + new_section + text[end:]
    return None


# --- Cargo.toml -----------------------------------------------------------
# Bumps [workspace.package]/[package] version, and re-pins internal path-deps
# (entries with both `path = "…"` and `version = "…"`) to the new MAJOR, so a
# release bump never makes the workspace unresolvable (e.g. the 0.x -> 1.0 jump).
p = Path("Cargo.toml")
if p.is_file():
    txt = p.read_text(encoding="utf-8")
    out = bump_table_version(txt, ["workspace.package", "package"]) or txt
    major = version.split(".")[0]

    def pin_pathdep(line: str) -> str:
        if re.search(r'\bpath\s*=\s*"', line) and re.search(r'\bversion\s*=\s*"', line):
            return re.sub(r'(\bversion\s*=\s*")[^"]*(")', rf"\g<1>{major}\g<2>", line, count=1)
        return line

    out = "\n".join(pin_pathdep(ln) for ln in out.split("\n"))
    if out != txt:
        write(p, out)

# --- package.json ---------------------------------------------------------
p = Path("package.json")
if p.is_file():
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("version") != version:
            data["version"] = version
            write(p, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    except json.JSONDecodeError:
        pass

# --- pyproject.toml -------------------------------------------------------
p = Path("pyproject.toml")
if p.is_file():
    txt = p.read_text(encoding="utf-8")
    out = bump_table_version(txt, ["project", "tool.poetry"])
    if out and out != txt:
        write(p, out)

# --- pubspec.yaml (Dart/Flutter) ------------------------------------------
p = Path("pubspec.yaml")
if p.is_file():
    txt = p.read_text(encoding="utf-8")
    out, n = re.subn(r"(?m)^(version:\s*).*$", rf"\g<1>{version}", txt, count=1)
    if n and out != txt:
        write(p, out)

# --- VERSION / VERSION.txt ------------------------------------------------
for name in ("VERSION", "VERSION.txt"):
    p = Path(name)
    if p.is_file():
        if p.read_text(encoding="utf-8").strip() != version:
            write(p, version + "\n")

for c in changed:
    print(c)
