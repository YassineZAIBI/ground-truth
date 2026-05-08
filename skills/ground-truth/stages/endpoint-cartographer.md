# Stage — endpoint cartographer

Discover every HTTP endpoint in the project, group them by route prefix, attach each to the abstraction that owns its handler file, and produce the API tree.

## What to do

Run `python3 .claude/skills/ground-truth/scripts/endpoints.py` from the project root. It auto-detects the framework and writes `data.endpoints[]` and `data.endpoint_stats`.

Frameworks supported out of the box:
- Next.js App Router (`app/**/route.ts`)
- Next.js Pages Router (`pages/api/**`)
- FastAPI (`@app.get`, `@router.post`, etc)
- Flask (`@app.route`, `@bp.route`)
- Express (`app.get`, `router.post`, etc)

If none of these match the project, the script writes an empty `endpoints[]` and notes the gap in `unknowns[]`. The dashboard renders a "no API tree" placeholder. This is fine — many projects don't have HTTP APIs.

## On incremental runs

The script always re-runs (it's cheap). The endpoint set is recomputed from the current files. If a new file matches a route handler pattern, it appears in the next run automatically. Removed handlers disappear.

## When to invoke this stage manually

You can also call it at any time after Cartographer to refresh just the API tree. It does not depend on the LLM, so this is a free re-run.

## What to print

```
⏺ Endpoint cartographer · framework: next-app, fastapi
  ▸ 47 endpoints discovered
  ▸ 28 GET · 12 POST · 4 PATCH · 3 DELETE
```

Or, if no framework is detected:

```
⏺ Endpoint cartographer · no HTTP framework detected, skipping
```

## Linking endpoints to abstractions

After the Archaeologist runs (later in the pipeline), each endpoint's handler file is mapped to the abstraction that owns it. The script does this automatically — but on the first run, this mapping happens after both stages have run. The Renderer ensures consistency.
