# Stage 2 — cartographer

Inventory every file, classify it, and build the dependency graph. This stage is mostly deterministic.

## What to do

Run `python3 .claude/skills/ground-truth/scripts/crawl.py` in the project root. It produces the inventory section of `data.json`.

If `data.json` already exists (incremental run), pass `--since <commit>` to limit work to changed files. The script handles the diff internally.

The script outputs:

```json
{
  "last_commit": "<sha>",
  "scanned_at": "<iso8601>",
  "files": [
    {
      "path": "src/auth/gateway.py",
      "loc": 312,
      "language": "python",
      "category": "feature",
      "hash": "<sha256>",
      "imports": ["src.utils", "fastapi"],
      "imported_by_count": 28
    }
  ],
  "stats": {
    "total_files": 247,
    "by_category": {"feature": 178, "test": 39, "config": 18, "dead": 8, "scaffold": 4},
    "by_language": {"python": 198, "typescript": 39, "yaml": 10}
  }
}
```

## Classification rubric

The script applies these rules in order. First match wins.

- **test** — file path contains `tests/`, `__tests__/`, `*.test.*`, `*_test.*`, `*.spec.*`
- **config** — file is `*.yaml`, `*.toml`, `*.json`, `*.ini`, `Dockerfile`, `*.cfg` and not in a feature directory
- **scaffold** — file matches the project's known scaffolding patterns (auto-generated migrations, `__init__.py` with only re-exports, etc.)
- **dead** — file has zero `imported_by` references AND zero CLI/HTTP entry-point markers AND last modified > 90 days ago
- **feature** — everything else

If a file's classification is ambiguous, the script tags it `unclear` and lists it under `data.unknowns[]` — the renderer will surface this to the user.

## What to print

```
⏺ Cartographer (2/7) · scanning workspace
  ▸ 247 source files across 12 directories
  ▸ classified: 178 feature · 39 test · 18 config · 8 dead · 4 scaffold
  ▸ dependency graph: 412 edges
```

If incremental, instead:

```
⏺ Cartographer (2/7) · diff since 8a3f2c1
  ▸ 12 changed files re-classified
  ▸ no shifts in graph topology
```
