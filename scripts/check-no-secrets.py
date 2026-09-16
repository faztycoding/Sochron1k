#!/usr/bin/env python3
"""Reject credential material in source and configured secrets in env examples."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".venv", "node_modules", "tmp", "dist", "__pycache__"}
TEXT_SUFFIXES = {
    ".env",
    ".example",
    ".js",
    ".json",
    ".md",
    ".mq5",
    ".mqh",
    ".py",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
KNOWN_SECRET = re.compile(
    r"(?i)(?:sk_(?:live|test)_[A-Za-z0-9]{16,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})"
)
ENV_ASSIGNMENT = re.compile(
    r"^(MT5_PASSWORD|SUPABASE_SERVICE_ROLE_KEY|ZAI_API_KEY)=(.+)$", re.MULTILINE
)


def candidate_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
            continue
        if path.name.startswith(".env") or path.suffix in TEXT_SUFFIXES:
            files.append(path)
    return sorted(files)


def main() -> int:
    findings: list[str] = []
    for path in candidate_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(ROOT)
        if PRIVATE_KEY.search(text):
            findings.append(f"{relative}: private key material")
        if KNOWN_SECRET.search(text):
            findings.append(f"{relative}: probable unrestricted token")
        for match in ENV_ASSIGNMENT.finditer(text):
            value = match.group(2).strip()
            if value and not value.startswith(("<", "${")):
                findings.append(f"{relative}: configured {match.group(1)}")
    if findings:
        for finding in findings:
            print(f"FAIL {finding}")
        return 1
    print(f"PASS secret scan: {len(candidate_files())} text files checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
