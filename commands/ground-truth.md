---
description: Run the Ground Truth audit — produce a Business Mirror, Technical Atlas, and the official three-tab interactive dashboard.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
---

# /ground-truth

You are running a deterministic, multi-stage audit pipeline. Most of the heavy lifting is done by Python scripts and a fixed HTML template that ship with this skill. **Your job is to invoke them in order, not to invent your own dashboard or markdown.**

## NON-NEGOTIABLE CONTRACTS — READ FIRST

These are not suggestions. Violating any of them produces a broken dashboard and defeats the whole skill.

### Contract 1: NEVER WRITE THE DASHBOARD YOURSELF

The dashboard is produced by **exactly one** path:
```
python3 skills/ground-truth/scripts/render.py
```
That script reads `.ground-truth/data.json` and the template at `skills/ground-truth/templates/dashboard.html`, then writes `.ground-truth/dashboard.html`.

**You are forbidden from writing HTML to `.ground-truth/dashboard.html`, `BUSINESS_MIRROR.md`, `GROUND_TRUTH.md`, or `.ground-truth/drift-report.md` yourself.** Even if you think you can do better. Even if the user asks. Even if the script appears to fail. If the script fails, fix the script and re-run it — do not bypass it.

### Contract 2: VERIFY THE TEMPLATE WAS USED

After running the renderer, run this verification:
```
grep -q "ground-truth-template-v2.2" .ground-truth/dashboard.html && grep -q "id=\"window-biz\"" .ground-truth/dashboard.html && grep -q "id=\"window-tech\"" .ground-truth/dashboard.html && grep -q "id=\"window-api\"" .ground-truth/dashboard.html && echo "OK" || echo "TEMPLATE_LOST"
```
If the result is `TEMPLATE_LOST`, the renderer did not use the official template. Re-run `render.py`. If it still fails, abort with an error — do not "help" by hand-writing the dashboard.

### Contract 3: EVERY DETERMINISTIC STAGE IS A PYTHON CALL

These six stages are Python scripts. You must run them with `python3 <path>` and read stdout/stderr. You must not summarize, regenerate, or replace their output:
- `scripts/crawl.py`
- `scripts/endpoints.py`
- `scripts/triage.py`
- `scripts/risks.py`
- `scripts/screenshots.py`
- `scripts/render.py`

If you find yourself about to write Python output yourself, STOP. Run the script.

### Contract 4: DATA.JSON IS THE ONLY SHARED STATE

All stages read from and write to `.ground-truth/data.json`. You don't pass data between stages by remembering it — you read the file. This is what makes incremental runs work.

---

## Mode detection — DO THIS FIRST

```
test -f .ground-truth/data.json && echo "INCREMENTAL" || echo "FIRST_RUN"
```

- **First run** → all stages execute, voice harvester confirms with user (unless `--auto`).
- **Incremental + no `--rebuild`** → only re-process what `git diff` says changed.
- **Incremental + `--rebuild`** → full re-run, skip vocabulary confirmation if `voice.yaml` exists.

If user passed `--since <ref>`, use that as the diff base.

## Flags

- `--auto` — skip voice-harvester confirmation
- `--rebuild` — full re-run, ignore cache
- `--since <ref>` — incremental from a specific git ref
- `--no-screenshots` — skip screenshot scanner
- `--no-endpoints` — skip endpoint cartographer
- `--cheap` — skip drift-detector and business-outcome generation; render Tech window only

## Token economics — HARD RULES

**Rule 1.** Deterministic stages never use the LLM. Period.

**Rule 2.** On incremental runs, before any LLM call, compute:
```
git diff --name-only <last_commit> HEAD
```
If empty AND no doc files (README, CLAUDE.md) changed, skip directly to renderer with the message: "No changes since <commit>. Re-rendered dashboard from cache."

**Rule 3.** Archaeologist re-runs only on dirty abstractions. Cache the rest.

**Rule 4.** Drift Detector re-verifies a claim only if its target abstraction is dirty OR the doc it came from is dirty.

**Rule 5.** Business Translator caches by signature `(name, status, drift_count, purpose_oneline)`. Regenerate only when this changes.

**Rule 6.** Risk Analyst narration regenerates only for risks whose `(name, status, centrality, drift_count)` changed.

**Rule 7.** With `--cheap`: skip drift-detector + business-outcomes + risk narration entirely.

---

## Pipeline — execute in this order

### Stage 1 — voice-harvester (LLM, first run only)

Read `skills/ground-truth/stages/voice-harvester.md` and follow it. Mines vocabulary from README, CLAUDE.md, manifests. Writes `.ground-truth/voice.yaml`. Confirms with user unless `--auto`.

### Stage 2 — cartographer (deterministic)

```bash
python3 skills/ground-truth/scripts/crawl.py
```
Print stdout. Do not interpret. Move on.

### Stage 3 — endpoint-cartographer (deterministic, skip with `--no-endpoints`)

```bash
python3 skills/ground-truth/scripts/endpoints.py
```

### Stage 4 — archaeologist + drift-detector + business-translator (LLM, IN PARALLEL)

These three LLM stages share the same input (`data.json` after triage) but produce independent outputs. Run them in parallel using the `Task` tool with three subagents.

**Read this carefully**: dispatch three `Task` calls in a SINGLE message (parallel execution). Each subagent reads its stage prompt and writes only its own slice of `data.json`:

- Subagent A: read `skills/ground-truth/stages/archaeologist.md`, populate `data.abstractions[]`
- Subagent B: read `skills/ground-truth/stages/drift-detector.md`, populate `data.drift_findings[]` (skip if `--cheap`)
- Subagent C: read `skills/ground-truth/stages/business-translator.md`, populate `purpose_oneline` and `business_outcome` per abstraction (skip business_outcome if `--cheap`)

Wait, B and C need A's output. So actually:

**Phase 4a (sequential):** Archaeologist alone — populates `abstractions[]`.

**Phase 4b (parallel via Task):** Drift Detector + Business Translator dispatched together in one message.

When you dispatch them in parallel, each subagent must:
1. Re-read `data.json` fresh
2. Modify only its assigned fields
3. Write back atomically (read, modify, write)

Use file locking pattern: each subagent reads the full file, computes its changes against a deep copy, writes back. The renderer at the end is the source of truth — if there's a write conflict, the last writer wins, but since the fields are disjoint this should not corrupt data.

If parallel dispatch is unavailable in your runtime, run them sequentially — but always use the `Task` tool to keep each in its own context window, which avoids polluting the orchestrator's context with stage details.

### Stage 5 — triage-medic (deterministic)

```bash
python3 skills/ground-truth/scripts/triage.py
```

### Stage 6 — risk-analyst (mixed)

First the deterministic scoring:
```bash
python3 skills/ground-truth/scripts/risks.py
```

Then, unless `--cheap`, narrate each risk per `skills/ground-truth/stages/risk-analyst.md` (1-2 sentence explanation per risk, written into `data.risks[i].explanation`).

### Stage 7 — screenshot-scanner (deterministic, skip with `--no-screenshots`)

```bash
python3 skills/ground-truth/scripts/screenshots.py
```

### Stage 8 — renderer (deterministic, MANDATORY)

```bash
python3 skills/ground-truth/scripts/render.py
```

**Then immediately run the verification from Contract 2.** If `TEMPLATE_LOST`, re-run the renderer. Do not proceed past this stage with a broken dashboard.

---

## Final summary block — print exactly this

```
──────────────────────────────────────────────────────────────
 Summary

 <N> abstractions · <X> of <N> fully working · <D> drift findings
 <E> endpoints · <R> risks scored · critical path: <names or "n/a">

 Top 3 to look at:
  1. <name> — <one-line problem>
  2. <name> — <one-line problem>
  3. <name> — <one-line problem>

 Open the dashboard (cmd-click on Mac, ctrl-click on Windows):
   file:///<absolute-path-to-cwd>/.ground-truth/dashboard.html

 Share with non-technical: ./BUSINESS_MIRROR.md
 Engineer view:            ./GROUND_TRUTH.md
──────────────────────────────────────────────────────────────
```

Compute the absolute path with `pwd` and concatenate `/.ground-truth/dashboard.html`. The `file://` prefix is what makes the link clickable in modern terminals.

If the verification in Contract 2 ever returned `TEMPLATE_LOST` and you couldn't recover, instead print:

```
ERROR: Dashboard template was not used. Run /ground-truth --rebuild.
The renderer at skills/ground-truth/scripts/render.py exists; do not bypass it.
```

---

## When something is unclear

If a stage cannot complete (no README, no recognized framework, no `CLAUDE.md`), record the gap in `data.unknowns[]` and continue. The dashboard surfaces unknowns in their own section. Do not fabricate.
