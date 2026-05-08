# Stage — screenshot scanner

Find optional visual assets the user has dropped into known locations, embed them into the dashboard so engineers and non-technical readers can see the actual UI for each capability.

## What to do

Run `python3 .claude/skills/ground-truth/scripts/screenshots.py`. The script looks for:

- `docs/screenshots/<abstraction_id>.{png,jpg,jpeg,gif,webp}`
- `public/screenshots/<abstraction_id>.{png,jpg,jpeg,gif,webp}`
- `.ground-truth/screenshots/<abstraction_id>.{png,jpg,jpeg,gif,webp}`

If a match exists, the image is base64-encoded and embedded into `data.json`. The Renderer picks it up and shows it inline on each capability card.

Files over 1.5 MB are skipped to keep `dashboard.html` reasonable. The script tells the user.

## Storybook

The script also detects `*.stories.{tsx,jsx,js,ts}` files and matches them by name to abstractions. When a match is found, the dashboard adds a "Storybook stories" link list to that abstraction's drawer.

## Why no auto-screenshotting

Generating screenshots automatically would require: a working dev server, route discovery, headless browser, working auth, environment setup. On most projects this is brittle or impossible. This stage stays simple and deterministic — the user controls what visuals appear.

## On incremental runs

Always re-run; it's cheap. Newly added screenshots appear automatically on the next run.

## When to invoke manually

After dropping a new screenshot into `docs/screenshots/`, you can re-run just this stage + the renderer to refresh the dashboard:

```
python3 .claude/skills/ground-truth/scripts/screenshots.py
python3 .claude/skills/ground-truth/scripts/render.py
```

No LLM calls, no token cost.

## What to print

```
⏺ Screenshot scanner · scanning visual assets
  ▸ 4 screenshots embedded
  ▸ 7 Storybook stories linked
```

If nothing found:

```
⏺ Screenshot scanner · scanning visual assets
  ▸ 0 screenshots embedded
  ▸ tip: put PNG/JPG files in docs/screenshots/<abstraction_id>.png to embed them
```
