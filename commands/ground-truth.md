---
description: Run the Ground Truth audit — reverse-engineer the project's current state into a Business Mirror and a Technical Atlas with an interactive dashboard
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /ground-truth

You are running the Ground Truth pipeline on this codebase. The goal: produce a faithful, audience-aware reverse-engineering of what is actually here, what works, what doesn't, and where the docs lie.

## Mode detection

Look at `.ground-truth/data.json`:

- **Missing** → first run. Run all stages.
- **Present, and the user passed `--rebuild`** → full re-run. Treat as first run, but skip vocabulary confirmation (use existing `voice.yaml` if present).
- **Present, no `--rebuild`** → incremental run. Only re-process abstractions whose files changed since `last_commit` in `data.json`.

If the user passed `--since <ref>`, use that ref instead of cached `last_commit`.

## Flags

- `--auto` — skip the voice-harvester user confirmation. The harvester writes `voice.yaml` and the pipeline proceeds without waiting for input. Useful for CI, demo runs, or users who want to inspect the YAML afterward instead of confirming up front.
- `--rebuild` — full re-run, ignores cache.
- `--since <ref>` — incremental from a specific git ref.
- `--no-screenshots` — skip the screenshot scanner stage.
- `--no-endpoints` — skip the endpoint cartographer stage (for projects with no HTTP API).

## Pipeline stages

For each stage, read the stage prompt at `.claude/skills/ground-truth/stages/<stage>.md` and follow it. Stages share state through `.ground-truth/data.json`.

1. **voice-harvester** — first run only. Mines vocabulary from README/CLAUDE.md/manifests. Writes `.ground-truth/voice.yaml`. **Confirms with user unless `--auto` was passed.**

2. **cartographer** — `scripts/crawl.py`. File inventory + dependency graph. Deterministic.

3. **endpoint-cartographer** — `scripts/endpoints.py`. HTTP API tree: every endpoint, its method, handler file, and inferred purpose. Auto-detects framework (Next.js, FastAPI, Flask, Express). Skipped with `--no-endpoints`.

4. **archaeologist** — extracts 8–15 core abstractions named in project voice. LLM stage.

5. **drift-detector** — verifies every doc claim against the code. LLM stage.

6. **triage-medic** — `scripts/triage.py`. Status assignment per abstraction. Deterministic.

7. **risk-analyst** — computes critical path from the dep graph + ranks risks by (blast radius × fragility). Mostly deterministic, LLM-assisted for naming the risk in plain language.

8. **business-translator** — capability cards in project voice, plus `business_outcome` per abstraction. LLM stage.

9. **screenshot-scanner** — `scripts/screenshots.py`. Looks for `docs/screenshots/<abstraction_id>.{png,jpg}` and `public/screenshots/<abstraction_id>.{png,jpg}`. Embeds matches into the dashboard. Skipped with `--no-screenshots`.

10. **renderer** — `scripts/render.py`. Produces all artifacts.

## Terminal output

Print one line per stage with `⏺ <stage> (<n>/N) · <one-liner>` plus 1-3 sub-bullets. After all stages, print the summary block with top 3 issues and pointers to the artifacts.

## Token discipline

- Cartographer, Endpoint Cartographer, Triage, Screenshot scanner are deterministic — never re-derive their output with the LLM.
- On incremental runs, never re-translate an abstraction whose files haven't changed.
- Drift Detector only re-verifies claims whose targets changed OR claims from changed docs.
- Risk Analyst recomputes only if the graph topology or any status changed.

## When something is unclear

If a stage cannot complete (no README, no CLAUDE.md, framework not recognized for endpoints), do not invent. Record the gap in `data.json` under `unknowns[]` and continue.
