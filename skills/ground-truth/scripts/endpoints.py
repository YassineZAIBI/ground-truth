#!/usr/bin/env python3
"""
Endpoint cartographer — discover all HTTP endpoints in the project.

Auto-detects framework and extracts:
- Next.js App Router (app/**/route.ts, route.js)
- Next.js Pages Router (pages/api/**)
- FastAPI (@app.get/post/etc, @router.*)
- Flask (@app.route, @blueprint.route)
- Express (app.get, router.post, etc)

Reads:  .ground-truth/data.json (must contain files[] from cartographer)
Writes: same file, with endpoints[] appended
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

DATA_JSON = Path(".ground-truth/data.json")

NEXT_APP_ROUTE_RE = re.compile(r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)")
NEXT_PAGES_HANDLER_RE = re.compile(r"export\s+default\s+(?:async\s+)?function|export\s+default\s+\(")
NEXT_METHOD_GUARD_RE = re.compile(r"req\.method\s*[=!]==?\s*['\"](\w+)['\"]")

FASTAPI_DECORATOR_RE = re.compile(
    r"@(?:app|router|api)\.(get|post|put|patch|delete|head|options)\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

FLASK_ROUTE_RE = re.compile(
    r"@(?:app|bp|blueprint|\w+_bp|\w+_blueprint)\.route\s*\(\s*[\"']([^\"']+)[\"'](?:[^)]*methods\s*=\s*\[([^\]]+)\])?",
    re.IGNORECASE,
)
FLASK_METHOD_DECORATOR_RE = re.compile(
    r"@(?:app|bp|blueprint|\w+_bp)\.(get|post|put|patch|delete)\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

EXPRESS_RE = re.compile(
    r"(?:app|router|\w+Router)\.(get|post|put|patch|delete|head|options|all)\s*\(\s*[\"'`]([^\"'`]+)[\"'`]",
    re.IGNORECASE,
)

DOCSTRING_RE = re.compile(r'"""(.*?)"""', re.DOTALL)
JSDOC_RE = re.compile(r'/\*\*(.*?)\*/', re.DOTALL)


def detect_frameworks(files: list[dict]) -> set[str]:
    paths = {f["path"] for f in files}
    found = set()

    if any("app/" in p and (p.endswith("route.ts") or p.endswith("route.js") or p.endswith("route.tsx") or p.endswith("route.jsx")) for p in paths):
        found.add("next-app")
    if any("/api/" in p and ("pages/" in p or p.startswith("pages/")) for p in paths):
        found.add("next-pages")
    if any(p.endswith(("requirements.txt", "pyproject.toml")) for p in paths):
        for p in paths:
            if p.endswith(".py"):
                try:
                    txt = Path(p).read_text(encoding="utf-8", errors="ignore")[:8000]
                    if "from fastapi" in txt or "import fastapi" in txt or "FastAPI(" in txt:
                        found.add("fastapi")
                    if "from flask" in txt or "import flask" in txt or "Flask(" in txt:
                        found.add("flask")
                except Exception:
                    pass
    for p in paths:
        if p.endswith((".js", ".ts", ".mjs", ".cjs")):
            try:
                txt = Path(p).read_text(encoding="utf-8", errors="ignore")[:4000]
                if "require('express')" in txt or 'require("express")' in txt or "from 'express'" in txt or 'from "express"' in txt:
                    found.add("express")
                    break
            except Exception:
                pass
    return found


def first_doc_line(text: str, position: int) -> str:
    """Find the nearest preceding doc/comment for an endpoint declaration."""
    before = text[:position]
    last_double = before.rfind('"""')
    last_jsdoc = before.rfind("*/")
    last_line_comment = before.rfind("// ")
    candidates = [c for c in (last_double, last_jsdoc, last_line_comment) if c > 0]
    if not candidates:
        return ""
    nearest = max(candidates)
    snippet = text[nearest:position]
    line = ""
    for raw in snippet.splitlines():
        cleaned = raw.strip().lstrip("#/* \t").strip()
        if cleaned and not cleaned.startswith(("@", "import", "from", "const", "function", "export")):
            line = cleaned
            break
    return line[:140]


def extract_next_app(file_path: Path) -> list[dict]:
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    rel = str(file_path).split("app/", 1)[-1]
    route_path = "/" + rel.rsplit("/", 1)[0].replace("[", ":").replace("]", "")
    if route_path.endswith("/route.ts") or route_path.endswith("/route.tsx") or route_path.endswith("/route.js"):
        route_path = route_path.rsplit("/", 1)[0]
    if route_path == "/" or route_path == "":
        route_path = "/"

    out = []
    for m in NEXT_APP_ROUTE_RE.finditer(text):
        method = m.group(1)
        purpose = first_doc_line(text, m.start())
        out.append({
            "method": method,
            "path": route_path,
            "handler_file": str(file_path),
            "purpose_doc": purpose,
            "framework": "next-app",
        })
    return out


def extract_next_pages(file_path: Path) -> list[dict]:
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    s = str(file_path)
    after_api = s.split("/api/", 1)[-1]
    route_path = "/api/" + after_api.rsplit(".", 1)[0]
    route_path = route_path.replace("[", ":").replace("]", "")
    if route_path.endswith("/index"):
        route_path = route_path[:-6] or "/"

    methods = set(NEXT_METHOD_GUARD_RE.findall(text))
    if not methods:
        if NEXT_PAGES_HANDLER_RE.search(text):
            methods = {"ANY"}
        else:
            return []

    purpose = first_doc_line(text, len(text) - len(text.lstrip()))
    return [
        {"method": m, "path": route_path, "handler_file": s, "purpose_doc": purpose, "framework": "next-pages"}
        for m in methods
    ]


def extract_fastapi(file_path: Path) -> list[dict]:
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    out = []
    for m in FASTAPI_DECORATOR_RE.finditer(text):
        method = m.group(1).upper()
        path = m.group(2)
        purpose = first_doc_line(text, m.start())
        out.append({
            "method": method, "path": path, "handler_file": str(file_path),
            "purpose_doc": purpose, "framework": "fastapi",
        })
    return out


def extract_flask(file_path: Path) -> list[dict]:
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    out = []
    for m in FLASK_ROUTE_RE.finditer(text):
        path = m.group(1)
        methods_raw = m.group(2)
        if methods_raw:
            methods = [x.strip().strip("'\"").upper() for x in methods_raw.split(",")]
        else:
            methods = ["GET"]
        purpose = first_doc_line(text, m.start())
        for method in methods:
            out.append({
                "method": method, "path": path, "handler_file": str(file_path),
                "purpose_doc": purpose, "framework": "flask",
            })
    for m in FLASK_METHOD_DECORATOR_RE.finditer(text):
        method = m.group(1).upper()
        path = m.group(2)
        purpose = first_doc_line(text, m.start())
        out.append({
            "method": method, "path": path, "handler_file": str(file_path),
            "purpose_doc": purpose, "framework": "flask",
        })
    return out


def extract_express(file_path: Path) -> list[dict]:
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    out = []
    for m in EXPRESS_RE.finditer(text):
        method = m.group(1).upper()
        path = m.group(2)
        if method == "ALL":
            method = "ANY"
        purpose = first_doc_line(text, m.start())
        out.append({
            "method": method, "path": path, "handler_file": str(file_path),
            "purpose_doc": purpose, "framework": "express",
        })
    return out


def attach_to_abstractions(endpoints: list[dict], abstractions: list[dict]) -> None:
    file_to_abs: dict[str, str] = {}
    for a in abstractions:
        for f in a.get("files", []):
            file_to_abs[f] = a["id"]

    for ep in endpoints:
        ep["abstraction_id"] = file_to_abs.get(ep["handler_file"])


def main() -> int:
    if not DATA_JSON.exists():
        print("ERROR: .ground-truth/data.json not found. Run cartographer first.", file=sys.stderr)
        return 1

    data = json.loads(DATA_JSON.read_text())
    files = data.get("files", [])

    frameworks = detect_frameworks(files)

    if not frameworks:
        data["endpoints"] = []
        data.setdefault("unknowns", []).append("No HTTP framework detected — endpoint cartographer skipped.")
        DATA_JSON.write_text(json.dumps(data, indent=2))
        print(f"⏺ Endpoint cartographer · no HTTP framework detected, skipping")
        return 0

    endpoints: list[dict] = []

    for f in files:
        path = Path(f["path"])
        if not path.exists():
            continue

        if "next-app" in frameworks and (path.name in ("route.ts", "route.js", "route.tsx", "route.jsx")):
            endpoints.extend(extract_next_app(path))

        if "next-pages" in frameworks and "/api/" in str(path) and path.suffix in (".ts", ".tsx", ".js", ".jsx"):
            endpoints.extend(extract_next_pages(path))

        if path.suffix == ".py":
            if "fastapi" in frameworks:
                endpoints.extend(extract_fastapi(path))
            if "flask" in frameworks:
                endpoints.extend(extract_flask(path))

        if "express" in frameworks and path.suffix in (".js", ".ts", ".mjs", ".cjs"):
            endpoints.extend(extract_express(path))

    seen = set()
    deduped = []
    for ep in endpoints:
        key = (ep["method"], ep["path"], ep["handler_file"])
        if key not in seen:
            seen.add(key)
            deduped.append(ep)
    endpoints = deduped

    attach_to_abstractions(endpoints, data.get("abstractions", []))

    by_framework: dict[str, int] = {}
    for ep in endpoints:
        by_framework[ep["framework"]] = by_framework.get(ep["framework"], 0) + 1

    by_method: dict[str, int] = {}
    for ep in endpoints:
        by_method[ep["method"]] = by_method.get(ep["method"], 0) + 1

    data["endpoints"] = endpoints
    data["endpoint_stats"] = {
        "total": len(endpoints),
        "by_framework": by_framework,
        "by_method": by_method,
        "frameworks_detected": sorted(frameworks),
    }
    DATA_JSON.write_text(json.dumps(data, indent=2))

    fw_str = ", ".join(sorted(frameworks))
    print(f"⏺ Endpoint cartographer · framework: {fw_str}")
    print(f"  ▸ {len(endpoints)} endpoints discovered")
    method_summary = " · ".join(f"{c} {m}" for m, c in sorted(by_method.items(), key=lambda x: -x[1]))
    if method_summary:
        print(f"  ▸ {method_summary}")
    unattached = sum(1 for ep in endpoints if not ep.get("abstraction_id"))
    if unattached:
        print(f"  ▸ {unattached} endpoints not yet linked to an abstraction (will link after archaeologist)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
