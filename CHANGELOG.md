# Changelog

## v2.2.0 — 2026-05-09

### Critical fix: agent-bypass prevention
- **Renderer is now NON-BYPASSABLE.** The orchestrator prompt has hard "Contract" rules forbidding the agent from writing the dashboard, BUSINESS_MIRROR.md, or GROUND_TRUTH.md by hand.
- **Template lock marker.** The dashboard template carries `ground-truth-template-v2.2` signature; renderer fails fast if the template is missing or corrupted.
- **Post-render verification.** New `scripts/verify.py` confirms the rendered dashboard is the official template with all three tabs, the Mermaid diagram mount, and the risks panel.
- **Renderer self-checks.** After writing dashboard.html, render.py reads back the file and exits non-zero if any required marker is missing.

### Added
- **Parallel LLM stages via subagents.** Drift Detector and Business Translator now dispatch in parallel through the Task tool, halving wait time on first runs.

### Why this version exists
v2.1 had a subtle bug: the orchestrator prompt instructed the agent to "run the renderer" but did not forbid hand-writing the dashboard. Some agent runtimes interpreted the renderer as a suggestion and improvised a fresh dashboard each time, producing different-shaped outputs (6-tab, 7-tab, no-Mermaid). v2.2 closes this hole with hard contracts and post-write verification.

## v2.1.0 — 2026-05-08
- Three-tab dashboard, zoom + pan, risks panel, API tree
- Hard token-budget rules
- Clickable file:// link at end of run

## v1.0.0 — 2026-05-07
First public release.
