# Stage 3 — archaeologist

Extract the 8–15 core abstractions from the codebase and how they relate. This stage uses the LLM (you, Claude). It is the most expensive non-drift stage — manage tokens carefully.

## Inputs

- `data.json` (cartographer output)
- `voice.yaml` (project vocabulary)

## What an "abstraction" means here

A coherent unit of behavior that a reader could name in one short noun phrase using the project's vocabulary. Not a class, not a file, not a layer — a *capability* in the project's language.

Good examples (using a project's own words):
- "front door" — auth and request validation, spans 3 files
- "the hands" — tool execution sandbox, spans 5 files
- "throttle" — rate limiting

Bad examples:
- "utils" — too generic, not a capability
- "AuthGateway class" — too literal, fails the noun-phrase test
- "everything in src/auth/" — directory, not a capability

## Method

1. Read `data.json` and group `features` by import clusters (files that import each other). The Cartographer's `imports` field gives you this for free.

2. For each cluster of >50 LOC, ask: what does this cluster *do* for the user? If you can name it in 1-3 words using the project's vocabulary, it's an abstraction.

3. Aim for 8–15 abstractions total. If you find 30, you're slicing too fine — merge clusters. If you find 4, you're slicing too coarse — split.

4. For each abstraction, write:

```yaml
id: <stable_slug>            # e.g. "front_door"
name: <project_voice_name>   # e.g. "front door"  (uses voice.yaml naming pattern)
literal_name: <tech_name>    # e.g. "auth gateway"
files: [<paths>]
loc: <sum>
purpose_oneline: <one sentence in the project's voice>
relationships:
  - target: <other_abstraction_id>
    verb: <"calls" | "reads" | "writes" | "checks" | "emits" | etc>
    flow: <"runtime" | "auxiliary" | "broken">
```

5. Write the result to `data.json` under `abstractions[]`.

## On incremental runs

For each abstraction, check whether any of its `files` appears in the changed-file list. If none changed, **reuse the cached abstraction record verbatim**. Do not re-prompt the LLM.

For abstractions whose files changed, ask: has the *role* of this abstraction changed, or just its implementation? If only implementation changed, keep the existing `name`, `purpose_oneline`, and `relationships`. Only update `loc` and `files`.

If the role genuinely changed (new files joined the cluster, the cluster's responsibility expanded), regenerate the record.

## When to add or remove abstractions

- New cluster appeared with significant LOC → propose a new abstraction.
- Abstraction's files all moved into another cluster → merge.
- Abstraction's LOC dropped to near-zero → mark it dead in the triage stage rather than removing it here.

## What to print

```
⏺ Archaeologist (3/7) · extracting core abstractions
  ▸ 12 abstractions identified
  ▸ 31 inter-abstraction relationships mapped
```

Incremental:

```
⏺ Archaeologist (3/7) · re-evaluating 3 dirty abstractions
  ▸ "billing meter" purpose updated
  ▸ "throttle" unchanged, cached
  ▸ "session memory" relationships expanded
```
