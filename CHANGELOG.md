# Changelog

## v1.0.0 — 2026-05-08

First public release.

### Pipeline (10 stages)
- **voice-harvester** — mines and confirms project vocabulary on first run
- **cartographer** — file inventory and dependency graph
- **endpoint-cartographer** — extracts HTTP API tree (Next.js App + Pages, FastAPI, Flask, Express)
- **archaeologist** — extracts core abstractions in project voice
- **drift-detector** — verifies doc claims against code
- **triage-medic** — assigns live/unverified/half-built/broken/dead
- **risk-analyst** — computes critical path + ranks top 5 risks
- **business-translator** — capability cards + business outcomes
- **screenshot-scanner** — embeds optional visual assets
- **renderer** — produces all artifacts

### Outputs
- `BUSINESS_MIRROR.md` — plain language for non-technical stakeholders
- `GROUND_TRUTH.md` — technical atlas with file citations
- `.ground-truth/dashboard.html` — interactive single-file dashboard with three tabs
- `.ground-truth/drift-report.md` — deep dive on doc-vs-code mismatches
- `.ground-truth/data.json` — shared state (versioned in `history/`)

### Dashboard features
- Three tabs: Business / Technical / API tree
- Zoom and pan on the Mermaid architecture diagram
- Critical path highlighted on the diagram
- Top 5 risks panel with score, centrality, fragility breakdown
- Optional embedded screenshots per abstraction
- Storybook story detection and linking
- Drift findings inline on each abstraction
- Dark mode support

### Flags
- `--auto` skips the vocabulary confirmation
- `--rebuild` forces full re-run
- `--since <ref>` for incremental from a specific git ref
- `--no-screenshots` and `--no-endpoints` for opt-out

### Performance
- Incremental runs typically 15-25% of first-run cost
- All deterministic stages (Cartographer, Endpoint Cartographer, Triage, Risk Analyst, Screenshot Scanner, Renderer) run without LLM calls
