# Stage 5 — triage medic

Tag every abstraction with one of five status values. This stage is mostly deterministic — call the Python script.

## What to do

Run `python3 .claude/skills/ground-truth/scripts/triage.py`. It reads `data.json`, runs static checks per abstraction, and writes the `status` field on each.

## The five statuses

| Status | Test | Color |
|---|---|---|
| `live` | Has callers, has passing tests, imports succeed | Green |
| `unverified` | Has callers, imports succeed, but zero tests | Amber |
| `half-built` | Imports succeed, but one or more of: only-stub functions, dominant TODO/FIXME density, abstraction referenced by feature flags that are never true, called by ≤1 caller despite being non-trivial | Coral |
| `broken` | Imports fail, syntax errors, references to deleted modules | Red |
| `dead` | Zero callers anywhere, zero CLI/HTTP entry-point markers, last commit older than 90 days | Gray |

Order matters: an abstraction can match multiple criteria; the first matching status (top to bottom in the table) wins. So a broken abstraction is `broken` even if it's also dead.

## What "imports succeed" means

For Python: `python -c "import <module>"` exits 0. The script handles this with subprocess; it does not actually run module-level side effects, just imports.

For TypeScript / JavaScript: `tsc --noEmit` or `node --check` reports no errors.

For Go / Rust / others: language-appropriate static check from the Cartographer.

If the project doesn't have a usable static check tool installed, fall back to: parse-only AST check + grep for known broken patterns.

## What "TODO density" means

The script walks each abstraction's files. If TODO/FIXME/XXX comments exceed 1 per 50 LOC averaged across the abstraction, it's flagged half-built. This is calibrated for typical projects; the heuristic can be tuned in `scripts/triage.py` constants.

## On incremental runs

Status only changes if files in the abstraction changed. The script checks the file hashes from Cartographer; unchanged abstractions skip re-triage entirely.

## Status flips trigger drift re-verification

If an abstraction flips from `half-built` to `live`, any drift findings referencing it get re-verified by the Drift Detector on the next run. The Triage Medic writes a `flipped: true` marker on the abstraction; the Drift Detector reads this on incremental runs and includes those claims in its scope.

## What to print

```
⏺ Triage medic (5/7) · runtime + static checks
  ▸ live: 5 · unverified: 2 · half-built: 3 · broken: 1 · dead: 1
```

Incremental, with changes:

```
⏺ Triage medic (5/7) · 3 abstractions re-checked
  ▸ billing meter: half-built → half-built (unchanged)
  ▸ throttle: half-built → live (status flip!)
  ▸ session memory: unverified → live (tests added)
```
