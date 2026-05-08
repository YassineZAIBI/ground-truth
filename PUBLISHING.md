# Publishing Ground Truth

Three ways to ship this so others can install it.

## Option 1 — your own GitHub repo as a marketplace (simplest)

1. **Create a public repo** on GitHub, e.g. `YassineZAIBI/ground-truth`. Push the contents of this directory to its root.

2. **Add a marketplace manifest** at the repo root, named `.claude-plugin/marketplace.json`:

```json
{
  "name": "YassineZAIBI-marketplace",
  "owner": {
    "name": "Your Name",
    "url": "https://github.com/YassineZAIBI"
  },
  "plugins": [
    {
      "name": "ground-truth",
      "source": ".",
      "description": "Reverse-engineer your codebase into a Business Mirror, Technical Atlas, and interactive dashboard.",
      "version": "1.0.0",
      "category": "audit",
      "tags": ["audit", "documentation", "drift", "non-technical"],
      "license": "MIT",
      "homepage": "https://github.com/YassineZAIBI/ground-truth",
      "strict": true
    }
  ]
}
```

3. **Anyone can now install it** by running these commands in their Claude Code session:

```
/plugin marketplace add YassineZAIBI/ground-truth
/plugin install ground-truth@YassineZAIBI-marketplace
```

That's the whole publishing flow for a self-hosted marketplace. No registration, no review, no central registry. The user's Claude Code clones your repo, reads the manifest, copies the plugin into their project's `.claude/`.

## Option 2 — submit to the official Anthropic marketplace

If/when Anthropic launches a curated marketplace, the submission process will likely be a pull request to a registry repo. Track this at https://docs.claude.com/en/docs/claude-code/plugins-marketplaces. As of writing, the recommended path is option 1.

## Option 3 — direct file distribution

For users who don't want to use any marketplace at all, package the plugin as a zip and let them drop it into `.claude/`:

```bash
zip -r ground-truth-1.0.0.zip commands/ skills/ README.md LICENSE
```

Users unzip and merge with their existing `.claude/`. This is what your `INSTALL.md` already documents.

## Versioning

Stick to semver. The `version` field appears in three places — keep them in sync:

- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json` (if you maintain your own marketplace)
- A `CHANGELOG.md` in the repo root (recommended)

## Pre-publish checklist

Before pushing v1.0.0:

- [ ] Run `/ground-truth` against at least 3 real projects of different sizes/stacks. Confirm no crashes.
- [ ] Test `--auto` flag works.
- [ ] Test the dashboard zoom/pan in Chrome, Safari, Firefox.
- [ ] Test on a project with no HTTP API (endpoint cartographer should skip cleanly).
- [ ] Test on a project with no `CLAUDE.md` (drift detector should skip cleanly with note).
- [ ] Confirm `dashboard.html` renders in dark mode.
- [ ] Verify the LICENSE file is in place.
- [ ] Make sure no `.ground-truth/` directories are committed.

## Tagging a release

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub will create a release page; users with `/plugin marketplace add` pinned to a tag will get that exact version.

## Bumping versions

When you ship v1.1.0 with a new feature:

1. Update `version` in `plugin.json` and `marketplace.json`.
2. Add an entry to `CHANGELOG.md`.
3. Tag and push.

Users will see the update via `/plugin marketplace update`.

## Questions you'll get from users

- **"Why didn't it find my endpoints?"** — Framework not in the supported list. Open `skills/ground-truth/scripts/endpoints.py` and add a regex. Pull requests welcome.
- **"Why is everything tagged 'dead'?"** — Your project has no inbound imports the cartographer can resolve. Likely you're using monorepo path aliases (`@/lib/*`) that the static parser doesn't unwind. Workaround: hand-edit `voice.yaml` and accept the false positives, or extend `crawl.py` to handle your aliasing scheme.
- **"It's too slow on first run."** — Run with `--no-screenshots --no-endpoints` for a faster baseline, then re-run with them later. Or split the LLM stages into two slash commands.
- **"How do I change the dashboard styling?"** — `templates/dashboard.html` is a single self-contained file. Edit the CSS at the top.

## Telemetry

This plugin sends nothing anywhere. All processing is local. The only network call is the dashboard's runtime import of Mermaid from esm.sh — that happens in the user's browser when they open the dashboard, not during the audit run.
