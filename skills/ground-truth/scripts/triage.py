#!/usr/bin/env python3
"""
Triage medic — assign live/unverified/half-built/broken/dead per abstraction.

Reads:  .ground-truth/data.json (must contain abstractions[] from Archaeologist)
Writes: same file, with status field set on each abstraction
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

DATA_JSON = Path(".ground-truth/data.json")

TODO_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b", re.IGNORECASE)
STUB_RE = re.compile(r"^\s*(?:pass|raise\s+NotImplementedError|return\s+(?:None|0|\[\]|\{\}|\"\"|''))\s*(?:#.*)?$", re.MULTILINE)

TODO_DENSITY_THRESHOLD = 1 / 50


def python_imports_succeed(file_path: str) -> bool:
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"import ast; ast.parse(open('{file_path}').read())"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def ts_imports_succeed(file_path: str) -> bool:
    try:
        result = subprocess.run(
            ["node", "--check", file_path],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return True
    except Exception:
        return False


def imports_succeed(file_path: str, language: str) -> bool:
    if language == "python":
        return python_imports_succeed(file_path)
    if language in ("javascript", "typescript"):
        return ts_imports_succeed(file_path)
    return True


def count_todos_and_loc(files: list[str]) -> tuple[int, int]:
    total_todos = 0
    total_loc = 0
    for f in files:
        try:
            text = Path(f).read_text(encoding="utf-8", errors="ignore")
            total_todos += len(TODO_RE.findall(text))
            total_loc += sum(1 for _ in text.splitlines())
        except Exception:
            continue
    return total_todos, total_loc


def is_mostly_stubs(files: list[str]) -> bool:
    stub_lines = 0
    body_lines = 0
    for f in files:
        try:
            text = Path(f).read_text(encoding="utf-8", errors="ignore")
            stub_lines += len(STUB_RE.findall(text))
            body_lines += sum(
                1 for line in text.splitlines()
                if line.strip() and not line.strip().startswith(("#", "//", "/*"))
            )
        except Exception:
            continue
    return body_lines > 0 and stub_lines / max(body_lines, 1) > 0.3


def triage_one(abstraction: dict[str, Any], file_lookup: dict[str, dict]) -> dict[str, Any]:
    files = abstraction.get("files", [])
    file_records = [file_lookup.get(f) for f in files if file_lookup.get(f)]

    total_callers = sum(fr.get("imported_by_count", 0) for fr in file_records)

    languages = {fr.get("language", "other") for fr in file_records}
    primary_lang = next(iter(languages), "other") if languages else "other"
    all_imports_ok = all(imports_succeed(fr["path"], fr.get("language", "other")) for fr in file_records)

    todos, loc = count_todos_and_loc(files)
    todo_density = todos / max(loc, 1)
    mostly_stubs = is_mostly_stubs(files)

    has_tests = bool(abstraction.get("test_files")) or any(
        "test" in f.lower() or "spec" in f.lower() for f in files
    )

    days_oldest = max(
        (fr.get("last_modified_days_ago", 0) for fr in file_records),
        default=0,
    )

    if not all_imports_ok:
        status = "broken"
        reason = "imports fail or syntax errors"
    elif total_callers == 0 and days_oldest > 90:
        status = "dead"
        reason = f"zero callers, last touched {days_oldest} days ago"
    elif mostly_stubs or todo_density > TODO_DENSITY_THRESHOLD:
        status = "half-built"
        reason = f"todo density {todo_density:.3f}, stub-heavy={mostly_stubs}"
    elif has_tests:
        status = "live"
        reason = f"{total_callers} callers, has tests"
    elif total_callers > 0:
        status = "unverified"
        reason = f"{total_callers} callers, no tests"
    else:
        status = "dead"
        reason = "no callers, no tests"

    prev_status = abstraction.get("status")
    return {
        **abstraction,
        "status": status,
        "status_reason": reason,
        "callers_total": total_callers,
        "todo_density": round(todo_density, 4),
        "flipped": prev_status is not None and prev_status != status,
    }


def main() -> int:
    if not DATA_JSON.exists():
        print("ERROR: .ground-truth/data.json not found. Run cartographer first.", file=sys.stderr)
        return 1

    data = json.loads(DATA_JSON.read_text())
    file_lookup = {fr["path"]: fr for fr in data.get("files", [])}
    abstractions = data.get("abstractions", [])

    if not abstractions:
        print("⏺ Triage medic · no abstractions found yet (run archaeologist first)")
        return 0

    counts = {"live": 0, "unverified": 0, "half-built": 0, "broken": 0, "dead": 0}
    flips = []

    new_abstractions = []
    for a in abstractions:
        triaged = triage_one(a, file_lookup)
        new_abstractions.append(triaged)
        counts[triaged["status"]] += 1
        if triaged["flipped"]:
            flips.append((triaged["name"], a.get("status"), triaged["status"]))

    data["abstractions"] = new_abstractions
    DATA_JSON.write_text(json.dumps(data, indent=2))

    parts = " · ".join(f"{counts[k]} {k}" for k in ("live", "unverified", "half-built", "broken", "dead") if counts[k])
    print(f"⏺ Triage medic · runtime + static checks")
    print(f"  ▸ {parts}")
    if flips:
        print(f"  ▸ {len(flips)} status flips:")
        for name, old, new in flips:
            print(f"     - {name}: {old} → {new}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
