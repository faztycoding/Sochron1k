#!/usr/bin/env python3
"""Read-only check of installed skills against the reviewed source inventory.

This verifies file integrity and presence, not model behavior or external tools.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {"__pycache__", ".DS_Store", ".pytest_cache"}


def tree_digest(folder: Path) -> tuple[str, int]:
    if not (folder / "SKILL.md").is_file():
        raise ValueError("missing SKILL.md")
    digest = hashlib.sha256()
    count = 0
    for item in sorted(folder.rglob("*")):
        relative = item.relative_to(folder)
        if any(part in IGNORED for part in relative.parts):
            continue
        if item.is_symlink():
            raise ValueError(f"unexpected symbolic link: {relative}")
        if item.is_file():
            digest.update(relative.as_posix().encode("utf-8") + b"\0")
            digest.update(hashlib.sha256(item.read_bytes()).digest())
            count += 1
    return digest.hexdigest(), count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"
    parser.add_argument("--skills-root", type=Path, default=default_root)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "docs/tooling/skills-lock.json").read_text())
    failed = False
    for entry in manifest["skills"]:
        name = entry["name"]
        if Path(name).name != name or name in {".", ".."}:
            raise ValueError("invalid skill name in lock file")
        targets = [("installed", args.skills_root / name)]
        if entry.get("local_source"):
            targets.append(("repository source", ROOT / entry["local_source"]))
        for kind, target in targets:
            try:
                actual, count = tree_digest(target)
                if (actual, count) != (entry["tree_sha256"], entry["file_count"]):
                    raise ValueError("content drift; review changes before updating lock")
                print(f"PASS {name} ({kind}, {count} files)")
            except (OSError, ValueError) as error:
                print(f"FAIL {name} ({kind}): {error}")
                failed = True
    print("Integrity only: this does not verify model selection, broker actions, or remote services.")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
