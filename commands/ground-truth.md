---
description: Run the Ground Truth audit — reverse-engineer the project's current state into a Business Mirror, Technical Atlas, and interactive dashboard
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# /ground-truth

Reverse-engineer this codebase into two audience-aware artifacts plus an interactive dashboard. The goal is faithful: what is actually here, what works, what doesn't, where the docs lie.

## Mode detection — DO THIS FIRST

Read `.ground-truth/data.json`. Three modes:

- **Missing** → first run. All stages execute.
- **Present + user passed `--rebuild`** → full re-run, but skip vocabulary confirmation if `voice.yaml` already exists.
- **Present + no `--rebuild`** → **INCREMENTAL** run. This is the cheap path. Only re-process what changed.

If the user passed `--since <ref>`, use that ref as the diff base. Otherwise use `data.last_commit`.

## Flags

- `--auto` — skip voice-harvester confirmation. Pipeline proceeds without waiting for user input.
- `--rebuild` — full re-run, ignore cache.
- `--since <ref>` — incremental from a specific git ref.
- `--no-screenshots` — skip the screenshot scanner.
- `--no-endpoints` — skip the endpoint cartographer.
- `--cheap` — strict token budget: skip drift detector, skip business outcomes, render only the Tech window. Useful for fast weekly checks.

## Token economics — HARD RULES, NOT GUIDELINES

These rules are non-negotiable. Violating them defeats the purpose of incremental mode.

**Rule 1 — Deterministic stages never use the LLM.** Cartographer, Endpoint Cartographer, Triage Medic, Risk Analyst (scoring step), Screenshot Scanner, and Renderer are Python scripts. Call them with `python3` and read their stdout. Do not regenerate, summarize, or reinterpret their output.

**Rule 2 — On incremental runs, compute the dirty set first.** Before any LLM stage, compute:
```
dirty_files = git diff --name-only <last_commit> HEAD
dirty_abstractions = abstractions where any member file is in dirty_files
dirty_docs = README.md, CLAUDE.md files in dirty_files
```
If `dirty_abstractions` is empty AND `dirty_docs` is empty, exit immediately after the renderer with the message: "No changes since <last_commit>. Re-rendered dashboard from cache."

**Rule 3 — Archaeologist re-runs are scoped.** Only re-evaluate abstractions whose files appear in `dirty_files`. For unchanged abstractions, the cached record is canonical — copy it forward verbatim.

**Rule 4 — Drift Detector re-runs are doubly scoped.** Re-verify a claim only if (a) the claim's target abstraction is dirty, OR (b) the doc the claim came from is dirty. If both conditions are false, copy the cached verdict forward.

**Rule 5 — Business Translator caches by signature.** A capability card is regenerated only if `(name, status, drift_count, purpose_oneline)` of the abstraction changed since last run. Otherwise reuse cached card.

**Rule 6 — Risk Analyst narration is incremental.** The Python script `risks.py` always re-runs (it's cheap). The LLM only writes `explanation` strings for risks whose `(name, status, centrality, drift_count)` tuple changed.

**Rule 7 — `--cheap` mode skips the most expensive LLM stages.** When `--cheap` is set, skip: drift-detector entirely, business outcomes (set them to empty), Risk Analyst narration. The Tech window still renders.

If you find yourself about to run a full LLM pass on an unchanged input, STOP. Re-read the rules.

## Pipeline stages

Read each stage prompt at `skills/ground-truth/stages/<stage>.md` and follow it. Stages share `.ground-truth/data.json`.

1. **voice-harvester** — first run only. LLM. Asks user unless `--auto`.
2. **cartographer** — `scripts/crawl.py`. Deterministic.
3. **endpoint-cartographer** — `scripts/endpoints.py`. Deterministic. Skipped with `--no-endpoints`.
4. **archaeologist** — LLM, scoped by Rule 3.
5. **drift-detector** — LLM, scoped by Rule 4. Skipped with `--cheap`.
6. **triage-medic** — `scripts/triage.py`. Deterministic.
7. **risk-analyst** — `scripts/risks.py` for scoring (deterministic) + LLM for narration scoped by Rule 6. Narration skipped with `--cheap`.
8. **business-translator** — LLM, cached by Rule 5. Outcomes skipped with `--cheap`.
9. **screenshot-scanner** — `scripts/screenshots.py`. Deterministic. Skipped with `--no-screenshots`.
10. **renderer** — `scripts/render.py`. Deterministic.

## Terminal output

One line per stage. Format:

```
⏺ <stage> (<n>/<total>) · <activity>
  ▸ <key result>
```

For incremental runs, prefix each cached stage with `⏺ <stage> · cached, no LLM call`.

## End-of-run summary — ALWAYS PRINT THIS LAST

After the renderer completes, print this exact summary block. The dashboard URL must be a clickable `file://` link.

```
──────────────────────────────────────────────────────────────
 Summary

 <N> abstractions · <X> of <N> fully working · <D> drift findings
 <E> endpoints discovered · <R> risks scored · critical path: <names>

 Top 3 to look at:
  1. <name> — <one-line problem>
  2. <name> — <one-line problem>
  3. <name> — <one-line problem>

 Open the dashboard (clickable):
   file:///<absolute-path-to-cwd>/.ground-truth/dashboard.html

 Share with non-technical: ./BUSINESS_MIRROR.md
 Engineer view:            ./GROUND_TRUTH.md
 Tokens used this run:     ~<estimate>
──────────────────────────────────────────────────────────────
```

To compute the absolute path, run `pwd` and concatenate `/.ground-truth/dashboard.html`. The leading `file://` makes it a clickable hyperlink in most modern terminals.

For the token estimate, sum the rough token counts you used in this run across all LLM calls. If you cannot estimate, omit that line silently.

## When something is unclear

If a stage cannot complete (no README, no recognized framework, no `CLAUDE.md`), do not invent. Record the gap in `data.unknowns[]` and continue. The dashboard surfaces unknowns as their own section.
