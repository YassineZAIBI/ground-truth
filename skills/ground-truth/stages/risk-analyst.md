# Stage — risk analyst

Compute the critical path through the system and shortlist the top 5 risks, then narrate each risk in plain language.

## Step 1 — deterministic scoring

Run `python3 .claude/skills/ground-truth/scripts/risks.py`. It reads the dependency graph and triage statuses, computes:

- **Critical path** — the chain from an entry-point abstraction (no inbound edges) through the highest-centrality nodes to a leaf "must-work" piece. Drawn highlighted on the dashboard's diagram.

- **Top 5 risks** — each abstraction scored on `centrality × fragility`. High score means many things rely on this AND it's not in great shape.

The script writes `data.critical_path[]` (list of abstraction ids) and `data.risks[]` (top 5 with score, centrality, fragility, drift count) into `data.json`. Each risk has an empty `explanation` field — you fill that in next.

## Step 2 — narrate each risk

For each entry in `data.risks[]`, write a 1–2 sentence `explanation` that an engineer can read and act on. The explanation must:

- Name the concrete failure mode ("if X breaks, all of Y stops working").
- Cite the evidence from the score: how many things depend on it, what its current status is, whether there are open drift findings.
- Avoid generic phrases like "this is risky" or "needs attention." Be specific.

Examples of good explanations:

> "Auth gateway sits on the critical path with 28 dependents and 0 tests. A regression here silently breaks every authed flow — front door through tool execution."

> "Billing meter is half-built and 2 abstractions depend on it. The README still claims usage-based billing — until this lands, you cannot truthfully invoice anyone."

> "Admin panel is broken on import. It has zero dependents (so nothing else fails when it crashes), but CLAUDE.md calls it production-ready, which is the highest-trust risk in the docs right now."

Examples of bad explanations:

> "This component is critical and should be reviewed." ❌ generic

> "We recommend adding tests." ❌ doesn't name the failure mode

## Step 3 — write back

Update `data.risks[]` with the explanations. Print the result:

```
⏺ Risk analyst · graph + risk scoring
  ▸ critical path: front door → traffic cop → the hands → stream out
  ▸ top risk: auth gateway (28 dependents, 0 tests)
  ▸ 5 risks shortlisted with explanations
```

## On incremental runs

Re-run the deterministic scoring every time (it's cheap). Re-narrate only risks whose `(name, status, centrality, drift_count)` tuple changed since the last run. Cache existing explanations otherwise.

## Where this surfaces

- The critical path is highlighted on the Tech window's diagram (yellow border on path nodes).
- The top 5 risks appear in a dedicated "Critical path & risks" panel in the Tech window, ranked.
- The single highest risk is also surfaced in the Business window's "most urgent" callout if it's more urgent than the broken-status finding.
