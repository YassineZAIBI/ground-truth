#!/usr/bin/env python3
"""
verify.py — confirm the dashboard came from render.py, not a hallucinated rewrite.

Exit codes:
  0 — dashboard is the official template, all sections present
  1 — dashboard.html doesn't exist (renderer wasn't run)
  2 — dashboard exists but is missing one or more required markers
       (the orchestrator wrote it from scratch, bypassing render.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

DASHBOARD = Path(".ground-truth/dashboard.html")

REQUIRED_MARKERS = [
    ("ground-truth-template-v2.2", "official template signature"),
    ('id="window-biz"', "Business window"),
    ('id="window-tech"', "Technical window"),
    ('id="window-api"', "API tree window"),
    ('onclick="show(\'biz\')"', "persona toggle: business"),
    ('onclick="show(\'tech\')"', "persona toggle: technical"),
    ('onclick="show(\'api\')"', "persona toggle: API"),
    ('id="risks-panel-mount"', "risks panel"),
    ('id="api-mount"', "API tree mount"),
    ("setupPanZoom", "diagram zoom/pan"),
    ("mermaid", "Mermaid diagram"),
    ('id="diagram-mount"', "Mermaid mount point"),
]


def main() -> int:
    if not DASHBOARD.exists():
        print("ERROR: .ground-truth/dashboard.html not found.", file=sys.stderr)
        print("Run /ground-truth or python3 skills/ground-truth/scripts/render.py", file=sys.stderr)
        return 1

    text = DASHBOARD.read_text()
    missing = []
    for marker, label in REQUIRED_MARKERS:
        if marker not in text:
            missing.append(label)

    if missing:
        print("⚠ Dashboard verification FAILED.\n")
        print("The dashboard at .ground-truth/dashboard.html is NOT the official Ground Truth template.")
        print("Either it was hand-written by an agent that bypassed render.py, or the renderer was")
        print("called against an older template.\n")
        print("Missing sections:")
        for m in missing:
            print(f"  - {m}")
        print("\nFix: rerun the renderer:")
        print("  python3 skills/ground-truth/scripts/render.py\n")
        print("If the renderer fails, do not hand-write the dashboard. Check that the template")
        print("at skills/ground-truth/templates/dashboard.html is intact.")
        return 2

    cwd = Path.cwd().absolute()
    print("✓ Dashboard verified — all required sections present.")
    print(f"  Open: file://{cwd}/.ground-truth/dashboard.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
