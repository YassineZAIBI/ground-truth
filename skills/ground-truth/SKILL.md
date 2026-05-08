---
name: ground-truth
description: Reverse-engineer a codebase into a Business Mirror (for non-technical stakeholders) and a Technical Atlas (for engineers), with an interactive dashboard that shows what works, what's half-built, what's broken, and where the docs disagree with the code. Use when the user runs /ground-truth, asks to audit a project, asks "what did I actually build", or wants to understand what's working vs what's not in their codebase.
---

# Ground Truth

A reverse-engineering pipeline that produces three coupled artifacts:

- `GROUND_TRUTH.md` — the technical atlas, file-cited
- `BUSINESS_MIRROR.md` — plain-language capability summary
- `.ground-truth/dashboard.html` — single self-contained HTML, interactive, both views toggleable

The pipeline runs in 7 stages. The orchestrator lives in `.claude/commands/ground-truth.md`. Stage prompts live in this skill's `stages/` folder. Deterministic helpers live in `scripts/`. Output templates live in `templates/`.

## Design principles

**Two audiences, one dataset.** Business Mirror and Technical Atlas read from the same `data.json`. They never disagree — they only differ in what they show and how they say it.

**The project's vocabulary, not ours.** Both views speak the project's own nouns (mined from README, CLAUDE.md, class names, UI strings, confirmed by the user on first run). No generic "abstraction", "component", "module".

**Drift is a first-class output.** Promises in the docs that don't match the code are surfaced explicitly. No tool today does this — it is the original contribution.

**Incremental by default.** First run is full. Subsequent runs only re-analyze what git says changed. Token budget on weekly runs should be roughly 15–25% of the first run.

**Status, not just structure.** Every part is tagged `live`, `unverified`, `half-built`, `broken`, or `dead`. The dashboard's primary signal is health, not architecture.

## Files written

```
your-project/
├── GROUND_TRUTH.md              ← commit this
├── BUSINESS_MIRROR.md           ← share this
└── .ground-truth/               ← gitignored
    ├── data.json                ← the shared state
    ├── voice.yaml               ← project vocabulary, edit by hand
    ├── dashboard.html           ← open in any browser
    ├── drift-report.md          ← deep dive on every drift finding
    └── history/                 ← previous runs, archived
```

## When to invoke

Trigger via `/ground-truth` slash command. Direct skill invocation also works for sub-tasks ("re-run drift detection only", "regenerate the dashboard from the existing data.json").
