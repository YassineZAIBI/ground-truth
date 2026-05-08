#!/usr/bin/env python3
"""
Cartographer — inventory, classify, and build the dependency graph.

Pure Python, no LLM dependency. Idempotent. Supports incremental
mode via --since <git ref>.

Reads:  the project tree from cwd
Writes: .ground-truth/data.json (creating or merging)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

GROUND_TRUTH_DIR = Path(".ground-truth")
DATA_JSON = GROUND_TRUTH_DIR / "data.json"

LANGUAGE_BY_EXT = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".jsx": "javascript", ".go": "go", ".rs": "rust", ".java": "java",
    ".rb": "ruby", ".php": "php", ".cs": "csharp", ".kt": "kotlin",
    ".swift": "swift", ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
    ".sh": "shell", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".json": "json", ".md": "markdown", ".html": "html", ".css": "css",
    ".scss": "scss", ".sql": "sql",
}

CONFIG_FILES = {
    "package.json", "tsconfig.json", "pyproject.toml", "Cargo.toml", "go.mod",
    "Dockerfile", "docker-compose.yml", "Makefile", ".env.example",
    "requirements.txt", "Pipfile", "Gemfile", "pom.xml", "build.gradle",
}

EXCLUDED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", "target", ".cargo", "vendor",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "coverage", ".nyc_output", ".gradle", "bin", "obj",
    ".ground-truth",
}


@dataclass
class FileRecord:
    path: str
    loc: int
    language: str
    category: str
    hash: str
    imports: list[str] = field(default_factory=list)
    imported_by_count: int = 0
    last_modified_days_ago: int = 0


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def loc_of(p: Path) -> int:
    try:
        with p.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def days_since_mtime(p: Path) -> int:
    try:
        return int((time.time() - p.stat().st_mtime) / 86400)
    except Exception:
        return 0


def is_test_path(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    if any(part in {"tests", "test", "__tests__", "spec", "__specs__"} for part in parts):
        return True
    name = parts[-1]
    return bool(re.search(r"\.(test|spec)\.[a-zA-Z]+$|_test\.[a-zA-Z]+$", name))


def is_config_path(path: str) -> bool:
    name = Path(path).name
    if name in CONFIG_FILES:
        return True
    ext = Path(path).suffix
    return ext in {".yaml", ".yml", ".toml", ".ini", ".cfg"} and "src/" not in path


def is_scaffold(path: str, content: str | None = None) -> bool:
    name = Path(path).name
    if name == "__init__.py" and content is not None:
        stripped = "\n".join(
            line for line in content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ).strip()
        if stripped == "" or all(l.startswith(("from ", "import ", "__all__")) for l in stripped.splitlines() if l):
            return True
    if "migrations/" in path.replace("\\", "/") and re.search(r"\d{4}", name):
        return True
    return False


PY_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([a-zA-Z_][\w\.]*)\s+import|import\s+([a-zA-Z_][\w\.]*))",
    re.MULTILINE,
)
JS_IMPORT_RE = re.compile(
    r"""(?:^|\s)(?:import\s+[^'"]*from\s+|require\s*\(\s*)['"]([^'"]+)['"]""",
    re.MULTILINE,
)
GO_IMPORT_RE = re.compile(r'import\s+(?:"([^"]+)"|\((.*?)\))', re.DOTALL)


def extract_imports(path: Path, language: str) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    imports: list[str] = []
    if language == "python":
        for m in PY_IMPORT_RE.finditer(text):
            imp = m.group(1) or m.group(2)
            if imp:
                imports.append(imp.split(".")[0])
    elif language in ("javascript", "typescript"):
        imports.extend(m.group(1) for m in JS_IMPORT_RE.finditer(text))
    elif language == "go":
        for m in GO_IMPORT_RE.finditer(text):
            single, group = m.group(1), m.group(2)
            if single:
                imports.append(single)
            elif group:
                for line in group.splitlines():
                    g = re.search(r'"([^"]+)"', line)
                    if g:
                        imports.append(g.group(1))
    return list(dict.fromkeys(imports))


def changed_files_since(ref: str) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", ref, "HEAD"],
            capture_output=True, text=True, check=True,
        )
        files = {line.strip() for line in result.stdout.splitlines() if line.strip()}
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, check=True,
        )
        files.update(line.strip() for line in untracked.stdout.splitlines() if line.strip())
        return files
    except subprocess.CalledProcessError:
        return set()


def current_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def walk_project(root: Path) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")]
        for fn in filenames:
            if fn.startswith("."):
                continue
            p = Path(dirpath) / fn
            if p.suffix in LANGUAGE_BY_EXT or p.name in CONFIG_FILES:
                out.append(p)
    return out


def classify(path: str, language: str, loc: int, days_old: int, imported_by: int, content: str | None) -> str:
    if is_test_path(path):
        return "test"
    if is_config_path(path):
        return "config"
    if is_scaffold(path, content):
        return "scaffold"
    if imported_by == 0 and days_old > 90 and language not in ("yaml", "json", "toml", "markdown"):
        return "dead"
    if loc > 0:
        return "feature"
    return "unclear"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="git ref for incremental mode")
    parser.add_argument("--full", action="store_true", help="force full crawl")
    args = parser.parse_args()

    GROUND_TRUTH_DIR.mkdir(exist_ok=True)
    root = Path(".")

    existing: dict[str, Any] = {}
    if DATA_JSON.exists() and not args.full:
        try:
            existing = json.loads(DATA_JSON.read_text())
        except json.JSONDecodeError:
            existing = {}

    incremental = bool(args.since or existing.get("last_commit"))
    since_ref = args.since or existing.get("last_commit")
    changed = changed_files_since(since_ref) if incremental and since_ref else set()

    all_files = walk_project(root)
    file_records: dict[str, FileRecord] = {}

    for fr in existing.get("files", []):
        file_records[fr["path"]] = FileRecord(**{
            k: v for k, v in fr.items() if k in FileRecord.__dataclass_fields__
        })

    for p in all_files:
        rel = str(p.relative_to(root)).replace("\\", "/")
        if incremental and changed and rel not in changed and rel in file_records:
            continue

        ext = p.suffix
        language = LANGUAGE_BY_EXT.get(ext, "other")
        if p.name in CONFIG_FILES and language == "other":
            language = "config"

        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            content = None

        loc = loc_of(p)
        h = sha256_of(p)
        days_old = days_since_mtime(p)
        imports = extract_imports(p, language) if content else []

        file_records[rel] = FileRecord(
            path=rel,
            loc=loc,
            language=language,
            category="feature",
            hash=h,
            imports=imports,
            imported_by_count=0,
            last_modified_days_ago=days_old,
        )

    valid_paths = {str(p.relative_to(root)).replace("\\", "/") for p in all_files}
    for stale in list(file_records.keys()):
        if stale not in valid_paths:
            del file_records[stale]

    module_to_path: dict[str, str] = {}
    for path, fr in file_records.items():
        if fr.language == "python":
            module = path.replace("/", ".").rsplit(".", 1)[0]
            module_to_path[module] = path
            module_to_path[module.rsplit(".", 1)[-1]] = path

    for fr in file_records.values():
        for imp in fr.imports:
            target = module_to_path.get(imp)
            if target and target != fr.path:
                file_records[target].imported_by_count += 1

    for path, fr in file_records.items():
        try:
            content = (root / path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            content = None
        fr.category = classify(
            path, fr.language, fr.loc, fr.last_modified_days_ago, fr.imported_by_count, content
        )

    by_category: dict[str, int] = {}
    by_language: dict[str, int] = {}
    for fr in file_records.values():
        by_category[fr.category] = by_category.get(fr.category, 0) + 1
        by_language[fr.language] = by_language.get(fr.language, 0) + 1

    data = existing.copy() if existing else {}
    data["last_commit"] = current_commit()
    data["scanned_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    data["files"] = [asdict(fr) for fr in file_records.values()]
    data["stats"] = {
        "total_files": len(file_records),
        "by_category": by_category,
        "by_language": by_language,
        "edges": sum(fr.imported_by_count for fr in file_records.values()),
    }
    data.setdefault("unknowns", [])

    DATA_JSON.write_text(json.dumps(data, indent=2))

    cat = by_category
    if incremental and changed:
        print(f"⏺ Cartographer · diff since {since_ref[:7] if since_ref else '?'}")
        print(f"  ▸ {len(changed)} changed files re-classified")
    else:
        print(f"⏺ Cartographer · full scan")
        print(f"  ▸ {len(file_records)} source files across {len({Path(p).parent for p in file_records})} directories")
        cats = " · ".join(f"{cat.get(k, 0)} {k}" for k in ("feature", "test", "config", "dead", "scaffold") if cat.get(k))
        print(f"  ▸ classified: {cats}")
        print(f"  ▸ dependency graph: {data['stats']['edges']} edges")

    return 0


if __name__ == "__main__":
    sys.exit(main())
