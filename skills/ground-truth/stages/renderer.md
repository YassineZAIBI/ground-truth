# Stage 7 — renderer

Produce the three deliverables from `data.json`. This stage is fully deterministic — call the Python script.

## What to do

Run `python3 .claude/skills/ground-truth/scripts/render.py`. It reads `data.json` and `voice.yaml`, and writes:

- `GROUND_TRUTH.md` (technical atlas)
- `BUSINESS_MIRROR.md` (plain language)
- `.ground-truth/dashboard.html` (interactive, single self-contained file)
- `.ground-truth/drift-report.md` (deep dive on drift findings)
- `.ground-truth/history/<timestamp>.json` (snapshot of `data.json` for trend tracking)

## What the dashboard looks like

The dashboard has two windows, switched by a toggle at the top.

**Business window** — designed for the 3-second test:

- Big number: "9 / 12 features are working"
- Three colored cards: working / half-finished / broken
- One red callout: the most urgent thing
- Three grouped lists: ✓ Working, ⊘ Half-finished, ✕ Broken
- Click any item → small drawer with the analogy

No graph, no filters, no jargon. The non-technical persona must understand the headline within 3 seconds.

**Tech window** — designed for an engineer doing a code review:

- KPI strip (total / health score / drift / stale CLAUDE.md / trend sparkline)
- Change banner (incremental runs only — what flipped since last run)
- C4-style component diagram (Mermaid, auto-laid-out, status colors baked in)
- Side rail: filters + top issues
- Detail drawer: file paths, LOC, callers, tests, drift findings, history timeline

The Mermaid source is exposed via "copy diagram source" so the engineer can paste into draw.io / Excalidraw / Notion.

## Vocabulary application

The renderer reads `voice.yaml` and substitutes vocabulary throughout. Both windows use:

- Project name (from `voice.project.name`) instead of folder name
- Project nouns (from `voice.vocabulary`) instead of generic terms
- Abstraction names (from `data.abstractions[].name`) — the project's own labels, with `literal_name` as subtitle in the Tech window only

If `voice.yaml` is missing or marks fields as `unknown`, the renderer falls back to literal class names + generic terms, and prints a warning.

## What to print

```
⏺ Renderer (7/7) · writing artifacts
  ▸ GROUND_TRUTH.md (4.2 KB)
  ▸ BUSINESS_MIRROR.md (2.8 KB)
  ▸ .ground-truth/dashboard.html (87 KB)
  ▸ .ground-truth/drift-report.md (3.1 KB)
```

After this stage, the orchestrator prints the summary block. The renderer's job is just to write files.

## Idempotency

Re-running the renderer alone (without re-running prior stages) should produce byte-identical output if `data.json` and `voice.yaml` haven't changed. This is useful for tweaking the templates without re-doing the analysis.
