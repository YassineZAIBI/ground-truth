# Changelog

## v2.1.0 — 2026-05-08

### Added
- Three-tab dashboard: Business / Technical / API tree
- Zoom + pan on the architecture diagram (mouse wheel, click-drag, +/− buttons)
- Critical path computation with highlighted nodes on the diagram
- Top-5 risks panel with score, centrality, fragility breakdown
- HTTP API endpoint discovery for Next.js (App + Pages), FastAPI, Flask, Express
- Optional screenshot embedding from `docs/screenshots/<id>.png`
- Storybook story detection per abstraction
- `business_outcome` field on every abstraction (what the business loses if it breaks)
- `--auto` flag to skip vocabulary confirmation
- `--cheap` flag for strict-budget runs (skips drift detector + business outcomes)
- `--no-screenshots` and `--no-endpoints` opt-outs
- Clickable `file://` link to the dashboard at end of every run

### Token economics — hard rules
- Deterministic stages never re-derived by LLM
- Incremental runs scope LLM work to dirty abstractions only
- Drift detector doubly scoped: re-verifies only claims with dirty target OR dirty doc
- Business translator caches by signature `(name, status, drift_count, purpose_oneline)`
- Risk narration only regenerates for risks whose tuple changed

### Fixed
- `marketplace.json` schema: removed `$schema` URL, changed `source` to object form
- `plugin.json` author and homepage now point to YassineZAIBI

## v1.0.0 — 2026-05-07
First public release. Two-window dashboard (Business / Technical only).
