# Ground Truth — a Claude Code plugin

> Reverse-engineer your codebase into a Business Mirror, a Technical Atlas, and an interactive three-tab dashboard. Detects drift between docs and code, ranks risks, maps the API tree.

## What it does

After a long agentic dev session, your codebase, your `CLAUDE.md`, and your README all start drifting from each other. Ground Truth reconciles them into three artifacts:

- **`BUSINESS_MIRROR.md`** — for non-technical stakeholders. "9 of 12 features work. Here's the most urgent thing."
- **`GROUND_TRUTH.md`** — for engineers. File-cited table, drift report, risk shortlist, critical path.
- **`.ground-truth/dashboard.html`** — single self-contained interactive page with three tabs: **Business / Technical / API tree**, a zoomable Mermaid architecture diagram, a top-risks panel, and screenshot embedding for each capability.

## Install

In any Claude Code session:

```
/plugin marketplace add YassineZAIBI/ground-truth
/plugin install ground-truth
```

## Use

```
/ground-truth                  # auto-detects: first run if no data, else incremental
/ground-truth --auto           # skip vocabulary confirmation (CI-friendly)
/ground-truth --rebuild        # full re-run, ignore cache
/ground-truth --since HEAD~10  # incremental from a specific git ref
/ground-truth --no-screenshots # skip visual asset scanning
/ground-truth --no-endpoints   # skip API tree (for non-HTTP projects)
/ground-truth --cheap          # skip the most expensive LLM stages (Tech window only)
```

First run takes 30-90 seconds; subsequent incremental runs typically finish in 10-20 seconds.

At the end of every run, the orchestrator prints a clickable `file://` link to your dashboard. **Cmd-click on Mac, Ctrl-click on Windows** opens it directly in your browser.

## Verifying your dashboard is the real one

If your dashboard doesn't have three tabs (Business / Technical / API tree), or is missing the Mermaid diagram, it means an agent bypassed the official renderer. Run:

```
python3 .claude/plugins/ground-truth/skills/ground-truth/scripts/verify.py
```

This exits non-zero with a list of missing sections if the dashboard isn't the official template. To regenerate:

```
python3 .claude/plugins/ground-truth/skills/ground-truth/scripts/render.py
```

Or just `/ground-truth --rebuild`.

## What gets written

```
your-project/
├── GROUND_TRUTH.md              ← commit this
├── BUSINESS_MIRROR.md           ← share this
└── .ground-truth/               ← gitignored
    ├── data.json                shared state across runs
    ├── voice.yaml               project vocabulary (edit by hand)
    ├── dashboard.html           open in any browser
    ├── drift-report.md          deep dive on drift
    └── history/<timestamp>.json archived runs
```

## Pipeline (8 stages, parallel where possible)

1. **voice-harvester** (LLM, first run only, asks user) — mines project vocabulary
2. **cartographer** (deterministic) — file inventory + dependency graph
3. **endpoint-cartographer** (deterministic) — extracts every HTTP endpoint
4. **archaeologist + drift-detector + business-translator** (LLM, **parallel via subagents**)
5. **triage-medic** (deterministic) — assigns live/unverified/half-built/broken/dead
6. **risk-analyst** (mixed) — computes critical path + ranks top 5 risks
7. **screenshot-scanner** (deterministic) — embeds optional visual assets
8. **renderer** (deterministic) — produces all artifacts using the locked template

## Adding screenshots

Drop PNG/JPG files into one of these locations, named after abstractions:

- `docs/screenshots/<abstraction_id>.png`
- `public/screenshots/<abstraction_id>.png`
- `.ground-truth/screenshots/<abstraction_id>.png`

The renderer base64-embeds them into `dashboard.html` so it stays a single self-contained file.

## Editing the project's voice

After the first run, `.ground-truth/voice.yaml` exists. Edit any field, save, run `/ground-truth --rebuild`. Both windows will speak your nouns from then on.

## Frameworks supported (endpoint discovery)

- Next.js App Router (`app/**/route.ts`)
- Next.js Pages Router (`pages/api/**`)
- FastAPI (`@app.get`, `@router.post`, etc)
- Flask (`@app.route`, `@bp.route`)
- Express (`app.get`, `router.post`)

To add a new framework, edit `skills/ground-truth/scripts/endpoints.py` — one regex per framework.

## Token economics

The pipeline is designed for cheap weekly runs:

- **Deterministic stages never call the LLM.** Cartographer, Endpoint Cartographer, Triage, Risk scoring, Screenshot scanner, Renderer are all Python.
- **LLM stages are scoped to dirty data only.** On incremental runs, only abstractions and docs that changed since the last commit are re-evaluated. Cached records are reused verbatim.
- **Parallel subagents.** Drift Detector and Business Translator run concurrently via the Task tool, since they share input but produce disjoint outputs.
- **`--cheap` flag** skips the drift detector and business outcomes for ultra-fast runs (~5-10% of full first-run cost).

## Limitations

- **Static analysis only.** Triage checks imports + tests + TODO density. Doesn't run your code.
- **Mermaid layout has limits.** Beyond ~20 abstractions, the auto-layout gets cramped. The skill caps at 15 by design.
- **Drift detection is only as good as your docs.** Empty README means nothing to drift from. Skill notes the gap in `unknowns[]`.

## License

MIT. Fork it, modify it, ship it.

## Contributing

Bugs and feature requests welcome. The pipeline is intentionally modular: each stage is a single SKILL.md prompt + (optionally) one Python script.
