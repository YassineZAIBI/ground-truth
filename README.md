# Ground Truth — a Claude Code plugin

> Reverse-engineer your codebase into a Business Mirror, a Technical Atlas, and an interactive dashboard that any non-technical stakeholder can read in 3 seconds.

## What it does

After a long agentic dev session, your codebase, your `CLAUDE.md`, and your README all start drifting from each other. Ground Truth reconciles them.

It produces three artifacts every time you run it:

- **`BUSINESS_MIRROR.md`** — for non-technical stakeholders. Plain language. "9 of 12 features work. Here's the most urgent thing."
- **`GROUND_TRUTH.md`** — for engineers. File-cited table, drift report, risk shortlist, critical path.
- **`.ground-truth/dashboard.html`** — single self-contained interactive page with three tabs: Business / Technical / API tree. Zoom, pan, persona toggle.

## What makes it different

Other tools (DeepWiki, PocketFlow's tutorial generator, vanilla code-explainers) describe what's there. Ground Truth tells you what's **wrong**:

| Capability | Other tools | Ground Truth |
|---|---|---|
| Documentation | ✅ | ✅ |
| Diagram | ✅ | ✅ |
| Two audiences | ❌ | ✅ |
| Project's own vocabulary | ❌ | ✅ |
| Status (live/half/broken) | ❌ | ✅ |
| Drift detection (docs vs code) | ❌ | ✅ |
| Critical path + risks | ❌ | ✅ |
| Incremental token-efficient runs | ❌ | ✅ |
| API tree with endpoint details | ❌ | ✅ |
| Screenshot embedding | ❌ | ✅ |

## Install

```
/plugin install ground-truth
```

Or, from a marketplace:

```
/plugin marketplace add YassineZAIBI/ground-truth
/plugin install ground-truth
```

Or manually — drop the contents of this folder into `.claude/` in your project root.

## Use

```
/ground-truth                  # auto-detects: first run if no data, else incremental
/ground-truth --auto           # skip the vocabulary confirmation step (CI-friendly)
/ground-truth --rebuild        # full re-run, ignore cache
/ground-truth --since HEAD~10  # incremental from a specific git ref
/ground-truth --no-screenshots # skip visual asset scanning
/ground-truth --no-endpoints   # skip API tree (for non-HTTP projects)
```

First run takes 30-90 seconds and asks you to confirm the project vocabulary unless you pass `--auto`. Subsequent runs are incremental and typically finish in 10-20 seconds.

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

## Pipeline (10 stages)

1. **voice-harvester** (LLM, first run only, asks user) — mines project vocabulary
2. **cartographer** (deterministic) — file inventory + dependency graph
3. **endpoint-cartographer** (deterministic) — extracts every HTTP endpoint
4. **archaeologist** (LLM) — extracts 8-15 core abstractions in project voice
5. **drift-detector** (LLM) — verifies every doc claim against code
6. **triage-medic** (deterministic) — assigns live/unverified/half-built/broken/dead
7. **risk-analyst** (mixed) — computes critical path + ranks risks
8. **business-translator** (LLM) — capability cards + business outcomes
9. **screenshot-scanner** (deterministic) — embeds optional visual assets
10. **renderer** (deterministic) — produces all artifacts

## Adding screenshots

Drop PNG/JPG files into one of these locations, named after abstractions:

- `docs/screenshots/<abstraction_id>.png`
- `public/screenshots/<abstraction_id>.png`
- `.ground-truth/screenshots/<abstraction_id>.png`

The renderer base64-embeds them so `dashboard.html` stays a single file.

## Editing the project's voice

After the first run, `.ground-truth/voice.yaml` exists. Edit any field, save, run `/ground-truth --rebuild`. Both windows will speak your nouns from then on.

## Frameworks supported (endpoint discovery)

- Next.js App Router (`app/**/route.ts`)
- Next.js Pages Router (`pages/api/**`)
- FastAPI (`@app.get`, `@router.post`, etc)
- Flask (`@app.route`, `@bp.route`)
- Express (`app.get`, `router.post`)

To add a new framework, edit `skills/ground-truth/scripts/endpoints.py` — one regex.

## Limitations

- **Static analysis only.** Triage checks imports + tests + TODO density. Doesn't run your code.
- **Mermaid layout has limits.** Beyond ~20 abstractions, the auto-layout gets cramped. The skill caps at 15 by design.
- **Drift detection is only as good as your docs.** Empty README means nothing to drift from. Skill notes the gap in `unknowns[]`.
- **Project's vocabulary requires consistency.** If your code has no naming pattern (random `Manager`, `Service`, `Helper`), the skill falls back to literal class names.

## License

MIT. Fork it, modify it, ship it.

## Contributing

Bugs and feature requests welcome. The pipeline is intentionally modular: each stage is a single SKILL.md prompt + (optionally) one Python script. Add new stages by editing `commands/ground-truth.md` and dropping a new file in `skills/ground-truth/stages/`.
