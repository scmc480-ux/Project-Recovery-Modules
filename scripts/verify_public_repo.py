from __future__ import annotations

import re
import sys
from pathlib import Path


FORBIDDEN_PATH_PARTS = {
    "intake",
    "jobs",
    "workspace",
    "outputs",
}

PUBLIC_TEXT_SUFFIXES = {".md", ".json", ".txt", ".csv"}
TEXT_SUFFIXES = PUBLIC_TEXT_SUFFIXES | {".py", ".toml"}

FORBIDDEN_TEXT = [
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"www\.", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b\d{3}-\d{3}-\d{4}\b"),
    re.compile(r"\b\d{1,5}\s+[A-Za-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr)\b", re.IGNORECASE),
]

PUBLIC_TEXT_ONLY = [
    re.compile(r"@[A-Za-z][A-Za-z0-9_]{2,}"),
]


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    findings: list[str] = []
    for path in root.rglob("*"):
        rel_parts = set(path.relative_to(root).parts)
        if rel_parts & FORBIDDEN_PATH_PARTS and ".git" not in rel_parts:
            findings.append(f"forbidden public path: {path.relative_to(root)}")
        if not path.is_file() or ".git" in rel_parts:
            continue
        suffix = path.suffix.lower()
        if suffix not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_TEXT:
            if pattern.search(text):
                findings.append(f"forbidden text pattern {pattern.pattern!r} in {path.relative_to(root)}")
        if suffix in PUBLIC_TEXT_SUFFIXES:
            for pattern in PUBLIC_TEXT_ONLY:
                if pattern.search(text):
                    findings.append(f"forbidden public text pattern {pattern.pattern!r} in {path.relative_to(root)}")
    if findings:
        print("Public repository check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Public repository check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
