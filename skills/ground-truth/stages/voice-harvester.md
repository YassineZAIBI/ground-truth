# Stage 1 — voice harvester

You are extracting the project's own vocabulary and tone so every later stage can speak the project's language instead of generic engineering jargon.

## Inputs

- `README.md` (top-level, plus any `docs/README.md`)
- `CLAUDE.md` files (any depth)
- `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod` — for the official project name
- The first 30 lines of any landing page or marketing copy if present
- Top-level class and function names from the dependency graph (already in `data.json` after Cartographer — but this stage runs first, so you'll do a quick read yourself)

## What to extract

Produce a YAML file at `.ground-truth/voice.yaml` with this shape:

```yaml
project:
  name: <official name from manifest, fallback to repo folder name>
  tagline: <one line from README hero, or null>
  voice: <2-4 word characterization: "practical, slightly playful" / "formal, regulatory" / "technical, terse">

vocabulary:
  unit_of_work: <e.g. "run", "session", "request", "task" — pick what the project uses>
  primary_actor: <e.g. "operator", "user", "developer", "agent">
  capability: <e.g. "playbook", "module", "feature", "skill" — what they call top-level pieces>
  data_record: <e.g. "session", "thread", "context", "trace">

style:
  capitalization: <"sentence" | "lowercase" | "title">
  contractions: <"yes" | "no">
  jargon_to_avoid:
    - <list of generic terms the project deliberately doesn't use>

abstraction_naming:
  pattern: <"character" | "literal" | "mixed">
  examples:
    - <"the hands" → "tool executor"> # if the project uses character names
    - <"Router" → "Router">           # if the project uses literal class names
```

## How to extract

1. **Project name + tagline.** Read the manifest first, then the README. The tagline is the first sentence after the title that isn't a badge or a TOC.

2. **Voice characterization.** Read 200-300 words of README prose. Ask yourself: would this read more like a thoughtbot blog post (practical, slightly playful) or like an AWS service description (formal, technical) or like a hacker README (terse, in-jokes)? Pick 2-4 adjectives.

3. **Vocabulary.** Count occurrences in README + CLAUDE.md of candidate terms. The winner is whatever the project uses most consistently. If "session" appears 40 times and "context" appears 6 times, the unit is "session." If neither dominates, mark it `unknown` — that's a real signal.

4. **Capitalization + contractions.** Sample 5 sentences. If the README writes "we" and "don't" and lowercase headings, that's lowercase + contractions yes. If everything is "We will not" and Title Case Headings, that's the opposite.

5. **Abstraction naming.** Look at top-level class names. If you see `AuthGateway`, `ToolExecutor`, `AgentRouter` — that's a literal pattern. If the README or comments refer to them as "the front door", "the hands", "the traffic cop" — that's a character pattern. If both — mixed.

## The confirmation step

After writing `voice.yaml`, behavior depends on whether the user passed `--auto`:

**Without `--auto` (default):** Print this to the terminal exactly:

```
──────────────────────────────────────────────────────────────
 Project vocabulary detected

 Name:           <project.name>
 Voice:          <project.voice>

 Unit of work:   <vocabulary.unit_of_work>
 Primary actor:  <vocabulary.primary_actor>
 Capability:     <vocabulary.capability>
 Data record:    <vocabulary.data_record>

 Naming pattern: <abstraction_naming.pattern>

 The Business Mirror and the Technical Atlas will use this
 vocabulary throughout. Open .ground-truth/voice.yaml to edit.

 Press Enter to continue, or edit voice.yaml first then continue.
──────────────────────────────────────────────────────────────
```

Then **wait for user input**. The user may:

- Send empty input → proceed.
- Edit `voice.yaml` and send empty input → re-read the file, proceed with edits.
- Send instructions to change something → apply edits to `voice.yaml`, re-print the summary, wait again.

**With `--auto`:** Skip the wait. Print this instead:

```
──────────────────────────────────────────────────────────────
 Project vocabulary written to .ground-truth/voice.yaml
 (--auto: proceeding without confirmation)

 Name:           <project.name>
 Voice:          <project.voice>
 Unit of work:   <vocabulary.unit_of_work>
 Primary actor:  <vocabulary.primary_actor>
 Capability:     <vocabulary.capability>

 Edit voice.yaml and re-run /ground-truth --rebuild to apply changes.
──────────────────────────────────────────────────────────────
```

Then proceed immediately.

This step happens **only on first run**. On subsequent runs, the existing `voice.yaml` is loaded silently regardless of flags.

## When to flag a gap

If the README is empty, missing, or only contains badges and a title, mark `project.voice: unknown` and ask the user once: "I can't find a strong voice signal. Want to give me a sentence describing how the project sounds, or should I default to neutral technical?" Their answer goes into `voice.yaml`.

If class names follow no consistent pattern (mixed `Manager`, `Service`, `Helper`, random nouns), set `abstraction_naming.pattern: mixed` and offer the user the choice described in the master skill: "I see no consistent naming pattern. Take 5 minutes to give them character names, or use literal class names in the dashboard?"
