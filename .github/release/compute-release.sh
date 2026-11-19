#!/usr/bin/env bash
# compute-release.sh — derive the next SemVer tag from Conventional Commits made
# since the most recent vX.Y.Z tag. Language-agnostic; needs only git.
#
# Usage:   scripts/compute-release.sh [force]
#   force (optional): major | minor | patch | none | vX.Y.Z
#
# Prints three KEY=VALUE lines on stdout (consumed by the Release workflow):
#   next_version=<vX.Y.Z or empty>
#   bump=<major|minor|patch|explicit|none>
#   prev=<vX.Y.Z or none>
#
# Bump rules (highest wins across all commits since the last tag):
#   BREAKING CHANGE footer, or "type!:"      -> major
#   feat:                                    -> minor
#   fix|perf|refactor|build|chore|docs|...   -> patch
#   any other / non-conventional subject     -> patch  (every change ships)
# "[skip release]" (or "[release skip]") in the HEAD commit suppresses a release.
set -euo pipefail

force="${1:-}"

# Most recent STRICT semver tag (ignores vX.Y.Z-rc1 / -base / prereleases).
prev="$(git tag --list 'v[0-9]*' --sort=-v:refname \
         | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -n1 || true)"

if [ -n "$prev" ]; then
  base="${prev#v}"
  range="${prev}..HEAD"
else
  base="0.0.0"
  range=""
fi

IFS='.' read -r major minor patch <<EOF
$base
EOF
major="${major:-0}"; minor="${minor:-0}"; patch="${patch:-0}"

if [ -n "$range" ]; then
  mapfile -t subjects < <(git log --format='%s' "$range")
  bodies="$(git log --format='%B' "$range")"
else
  mapfile -t subjects < <(git log --format='%s')
  bodies="$(git log --format='%B')"
fi

# Escape hatch on the HEAD commit.
head_msg="$(git log -1 --format='%B')"
if printf '%s' "$head_msg" | grep -qiE '\[skip release\]|\[release skip\]'; then
  echo "next_version="; echo "bump=none"; echo "prev=${prev:-none}"; exit 0
fi

bump="none"
rank() { case "$1" in major) echo 3;; minor) echo 2;; patch) echo 1;; *) echo 0;; esac; }
raise() { if [ "$(rank "$1")" -gt "$(rank "$bump")" ]; then bump="$1"; fi; }

if printf '%s' "$bodies" | grep -qE 'BREAKING[ -]CHANGE'; then
  raise major
fi

for s in "${subjects[@]:-}"; do
  [ -z "$s" ] && continue
  if printf '%s' "$s" | grep -qE '^[a-zA-Z]+(\([^)]*\))?!:'; then raise major; fi
  t="$(printf '%s' "$s" | sed -nE 's/^([a-zA-Z]+)(\([^)]*\))?!?:.*/\1/p' | tr '[:upper:]' '[:lower:]')"
  case "$t" in
    feat)  raise minor ;;
    fix|perf|refactor|revert|build|chore|docs|style|test|ci) raise patch ;;
    "")    : ;;
    *)     raise patch ;;
  esac
done

# Any commit at all since the last tag counts as a change -> patch floor.
if [ "${#subjects[@]}" -gt 0 ] && [ "$bump" = "none" ]; then
  bump="patch"
fi

case "$force" in
  major|minor|patch|none) bump="$force" ;;
  v[0-9]*.[0-9]*.[0-9]*)  echo "next_version=${force}"; echo "bump=explicit"; echo "prev=${prev:-none}"; exit 0 ;;
  "") : ;;
  *) echo "invalid force value: $force" >&2; exit 2 ;;
esac

if [ "$bump" = "none" ]; then
  echo "next_version="; echo "bump=none"; echo "prev=${prev:-none}"; exit 0
fi

if [ -z "$prev" ]; then
  case "$bump" in
    major) next="v1.0.0" ;;
    *)     next="v0.1.0" ;;   # debut release
  esac
else
  case "$bump" in
    major) major=$((major+1)); minor=0; patch=0 ;;
    minor) minor=$((minor+1)); patch=0 ;;
    patch) patch=$((patch+1)) ;;
  esac
  next="v${major}.${minor}.${patch}"
fi

echo "next_version=${next}"
echo "bump=${bump}"
echo "prev=${prev:-none}"
