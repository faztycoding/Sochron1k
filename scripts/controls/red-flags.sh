#!/usr/bin/env bash
# Red-flag scan (Handbook v5, Appendix A), adapted for Sochron1k.
# Lists changes that need an explanation. A hit is not automatically wrong, but every hit must be
# explained in the completion report or the PR.
# Scans committed and uncommitted changes to tracked files since the merge-base with BASE.
# Untracked files are listed, not scanned: `git add` them first.
# Usage: bash scripts/controls/red-flags.sh [BASE]   (default BASE: main)
set -u
BASE="${1:-main}"
MB=$(git merge-base "$BASE" HEAD 2>/dev/null) || { echo "Cannot find merge-base with $BASE"; exit 2; }
NAMES=$(git -c core.quotePath=false diff --name-status "$MB")
ADDED=$(git -c core.quotePath=false diff -U0 --no-color "$MB" | awk '
  /^\+\+\+ b\// { f = substr($0, 7); next }
  /^\+\+\+ /    { f = ""; next }
  /^\+/         { print f ": " substr($0, 2) }')
TESTPATH='(^|/)(tests?|__tests__|spec|e2e)/|\.(test|spec)\.|(^|/)conftest\.py'
HITS=0

section() { echo; echo "== $1 =="; }

# check LABEL REGEX [all|code] [grep-flag]
#   code: skip test files and Markdown docs, which legitimately mention these words.
check() {
  local label="$1" re="$2" scope="${3:-all}" flag="${4:-}"
  local lines="$ADDED"
  if [ "$scope" = "code" ]; then
    lines=$(printf '%s\n' "$ADDED" | grep -Ev "^[^:]*($TESTPATH)" | grep -Ev '^[^:]*\.md: ' || true)
  fi
  local out
  if [ -n "$flag" ]; then
    out=$(printf '%s\n' "$lines" | grep -E "$flag" -- "$re" || true)
  else
    out=$(printf '%s\n' "$lines" | grep -E -- "$re" || true)
  fi
  if [ -n "$out" ]; then
    HITS=$((HITS + 1)); section "!! $label"; printf '%s\n' "$out" | head -n 25
  fi
}

section "Files changed since merge-base with $BASE (${MB:0:7})"
printf '%s\n' "${NAMES:-(none)}"

section "Deleted or renamed test files"
printf '%s\n' "$NAMES" | grep -E '^(D|R)' | grep -E "$TESTPATH" || echo "(none)"

section "Untracked files (not scanned; git add them first)"
UNTRACKED=$(git -c core.quotePath=false ls-files --others --exclude-standard)
printf '%s\n' "${UNTRACKED:-(none)}" | head -n 25

check "Skipped or focused tests" '\.(skip|only)\(|(^|[^a-zA-Z])x(it|describe)\(|pytest\.mark\.(skip|xfail)|unittest\.skip'
check "Type checks disabled" '@ts-ignore|@ts-expect-error|as any([^a-zA-Z]|$)|type: *ignore|pyright: *ignore'
check "Lint disabled" 'eslint-disable|noqa|nolint'
check "Placeholder or mock in production code" '(TODO|FIXME|HACK|XXX|placeholder|dummy|fake|mock|stub)' code -i
check "Swallowed errors" 'catch *(\([^)]*\))? *\{ *\}|except[^:]*: *(pass|\.\.\.) *$'
# Two literals are split with '' (bash joins the pieces) so this definition line does not match
# itself; the pattern the scanner uses is unchanged (review BOOT-001 F6).
check "Possible secrets" '(sk_(live|test)_|pk_''live_|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{20,}|service''_role|BEGIN [A-Z ]*PRIVATE KEY)'
check "Secret-like value assigned" '[A-Z0-9_]*(PASSWORD|PASSWD|SECRET|TOKEN|API_KEY)[A-Z0-9_]*=[^ #$<]{4,}'
check "Destructive or bypass commands" '(--force|--no-verify|reset --hard|DROP (TABLE|DATABASE|SCHEMA)|TRUNCATE )'
check "Client-exposed variable with secret-like name" '(NEXT_PUBLIC_|EXPO_PUBLIC_|VITE_)[A-Z0-9_]*(SECRET|PRIVATE|SERVICE|PASSWORD)'
check "Order or account mutation surface (Demo-only rule)" '(order_send|order_check|TRADE_ACTION_|ACCOUNT_TRADE_MODE_REAL|OrderSend|PositionClose)' code

section "Control files touched (need owner review)"
printf '%s\n' "$NAMES" | awk '{print $NF}' | grep -Ei '(^\.github/|^\.claude/|^\.agents/|^\.codex/|(^|/)AGENTS\.md$|(^|/)CLAUDE\.md$|^tests/(acceptance|golden|architecture)/|^docs/HANDBOOK-CORE\.md$|^docs/hypotheses/|^research/registry/|^scripts/controls/|^\.gitattributes$|^\.gitignore$|(^|/)(uv|poetry|package-lock|pnpm-lock|yarn)\.lock$|lock(file)?(\.json|\.yaml)?$|pyproject\.toml$|package\.json$|auth|security|polic(y|ies)|migrations?/)' || echo "(none)"

echo
echo "Pattern groups with hits: $HITS. Every hit needs an explanation; a hit is not automatically wrong."
