# Stage 6 — business translator

Write one capability card per abstraction, in the project's voice, for the non-technical persona. This is the "explain to a 14-year-old" layer.

## Inputs

- `data.json` (after Cartographer + Archaeologist + Drift + Triage)
- `voice.yaml`

## What goes in a capability card

```yaml
- abstraction_id: front_door
  display_name: front door         # from voice.yaml naming convention
  status_simplified: working       # one of: working, half-finished, broken
  one_liner: |
    The bouncer at the entrance. Checks who you are before letting
    you do anything.
  business_outcome: |              # NEW — what does this mean for the business?
    Without this, anyone could call any of our APIs without identifying
    themselves. Every paid feature relies on knowing which operator is
    making the request.
  why_it_matters: |
    Quietly does its job for every single request. Over 28 places
    in the code rely on it.
  what_to_watch_for: null          # only set if status != working
```

The `business_outcome` field answers "if this stops working, what does the user/business lose?" It's deliberately distinct from the analogy:

- `one_liner` is *what it is* (the bouncer at the entrance)
- `business_outcome` is *what it's for* (without it, anyone could access paid features)

A non-technical reader needs both. The analogy makes them understand the thing exists; the business outcome makes them understand why they should care if it breaks.

## Status simplification

The dashboard Business window uses three buckets, not five:

- `working` ← `live` and `unverified`
- `half-finished` ← `half-built`
- `broken` ← `broken`
- (`dead` is excluded from the Business Mirror entirely — non-technical readers don't need to know about safely dormant code)

For `unverified` abstractions, set `what_to_watch_for` to a one-line caveat ("works, but nobody has tested it — could be forgetting things it shouldn't").

For `half-finished` abstractions, set `what_to_watch_for` to one line on what's missing ("function exists but always reports zero — billing isn't real yet").

For `broken` abstractions, set `what_to_watch_for` to one line on what's wrong AND any drift finding ("can't even start. The CLAUDE.md still says 'production-ready' — it isn't").

## Voice rules

Read `voice.yaml`. Match the project's tone exactly:

- If `voice.contractions: yes`, use them ("don't", "we've").
- If `voice.capitalization: lowercase`, write headings in lowercase too.
- If `voice.style.jargon_to_avoid` lists "abstraction", never write that word.
- Use the project's own nouns from `voice.vocabulary` ("operator" not "user" if that's the project's word).

## Analogy quality bar

Every `one_liner` should pass two tests:

1. **The 14-year-old test.** A non-technical reader understands what the thing *does for them* without knowing what code is. "The bouncer at the entrance" passes. "OAuth2 middleware with JWT validation" fails.

2. **The honest test.** The analogy doesn't make the thing sound better than it is. "The bouncer that mostly works" is better than "The trusted gatekeeper" if the abstraction is `unverified`.

Avoid these specific traps:

- Don't anthropomorphize unless the project's voice already does. Some projects are dry — match that.
- Don't say "robust", "powerful", "seamless" — these are marketing words. The Business Mirror is an internal audit, not a brochure.
- If you can't find a good analogy in 10 seconds, write a literal sentence instead. A clear literal beats a forced metaphor.

## On incremental runs

For each abstraction, check whether its `purpose_oneline` changed in this run, OR its status changed, OR a drift finding referencing it changed. If none of those, **reuse the cached business card verbatim**. This is the biggest token saver.

## What to print

```
⏺ Business translator (6/7) · capability rewrite
  ▸ 12 capability cards generated
  ▸ one-paragraph product summary written
```

Incremental:

```
⏺ Business translator (6/7) · 3 cards regenerated, 9 cached
  ▸ "billing meter" rewritten (status flip)
  ▸ "doorbell" rewritten (drift finding closed)
  ▸ "control room" rewritten (still broken, evidence updated)
```

## Also write the one-paragraph summary

In addition to per-abstraction cards, write one paragraph (3-5 sentences) at `data.business_summary` that describes what the system *is* in the project's voice. This goes at the top of `BUSINESS_MIRROR.md` and the dashboard Business window.

Template:

> You've built [what kind of thing] where [primary actor] can [primary capability]. Around that core, [supporting capabilities, named in project voice]. [If anything significant is broken or half-built:] Right now, [the thing], which means [user-facing consequence].
