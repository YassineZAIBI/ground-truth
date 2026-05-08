# Stage 4 — drift detector

Cross-reference every claim in CLAUDE.md, README, and module docstrings against what the code actually does. This is the original contribution of Ground Truth — no other tool surveyed does this systematically.

## Inputs

- `data.json` (after Cartographer + Archaeologist)
- All `CLAUDE.md` files (any depth)
- `README.md` (top-level + any nested)
- Top-level docstrings of files in active feature abstractions

## Step 1 — Extract claims

A claim is any factual assertion the documentation makes about the system. Categories to extract:

- **Capability claims** — "the system supports X", "users can Y"
- **Status claims** — "production-ready", "stable", "in beta"
- **Configuration claims** — "set X env var to enable Y"
- **Persistence claims** — "X is persistent across restarts", "X is cached for Y minutes"
- **Architectural claims** — "X is implemented using Y", "X talks to Y over Z protocol"
- **Path claims** — "see src/foo.py for X" (these go stale fast)

Walk every doc. For each claim, record:

```yaml
- id: claim_001
  source_file: docs/CLAUDE.md
  source_line: 42
  category: status
  claim_text: "admin panel: production-ready"
  references: [admin_panel]   # which abstractions it touches
```

Aim for 20-80 claims on a typical project. If you find more than 150, you're being too granular — merge similar claims about the same abstraction.

## Step 2 — Verify each claim

For each claim, compare against the code. Produce a verdict:

- **CONFIRMED** — the code does what the claim says
- **PARTIAL** — partially true, with caveats (e.g. "persistent" but only for 30 min)
- **CONTRADICTED** — the code does the opposite, or the named feature doesn't work
- **ABSENT** — the claim references something that doesn't exist (deleted file, removed feature)

Verification methods, in order of preference:

1. **Static check** — for path claims, just check whether the file exists and has the named symbol. Cheap.
2. **Triage check** — if the claim is "X is production-ready" and the triage status of X is `broken` or `half-built`, that's contradicted. Cheap.
3. **Code reading** — read the relevant files and judge. Expensive but unavoidable for capability claims.

For each verdict, record evidence:

```yaml
- claim_id: claim_001
  verdict: CONTRADICTED
  evidence: "src/admin/app.py imports from src.legacy.* which was deleted in 8a3f2c1; build fails"
  recommended_fix: "edit CLAUDE.md to mark admin panel as broken-pending-rewrite"
```

## Step 3 — Detect omissions

The reverse of drift: features that exist in the code but are never mentioned in the docs. For each abstraction, check if any documentation references it. If none do, record:

```yaml
- type: undocumented_capability
  abstraction: <id>
  severity: medium
  note: "<abstraction.name> has <N> callers but is not mentioned in README or any CLAUDE.md"
```

## On incremental runs

Re-verify only:

1. Claims whose target files appear in the git diff.
2. All claims from any doc file (CLAUDE.md, README.md) that itself changed.
3. Claims previously marked PARTIAL or CONTRADICTED — they may have been fixed.

Skip re-verification of CONFIRMED claims whose targets didn't change. Reuse the cached verdict.

## What to print

```
⏺ Drift detector (4/7) · cross-referencing docs vs code
  ▸ parsed: 4 CLAUDE.md · 2 README.md · 14 module docstrings
  ▸ extracted 47 documented claims
  ▸ verdicts: 28 confirmed · 5 partial · 9 contradicted · 5 absent
```

## Output

Append to `data.json`:

```json
"drift_findings": [
  {
    "claim_id": "claim_001",
    "source": "docs/CLAUDE.md:42",
    "claim": "admin panel: production-ready",
    "references": ["admin_panel"],
    "verdict": "CONTRADICTED",
    "evidence": "...",
    "recommended_fix": "..."
  }
],
"undocumented_capabilities": [...]
```

Also write a human-readable `.ground-truth/drift-report.md` with the full findings, grouped by verdict, sorted by severity. The Renderer links to it from both Mirror and Atlas.
