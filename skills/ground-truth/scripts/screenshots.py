#!/usr/bin/env python3
"""
Screenshot scanner — find optional screenshots tied to each abstraction.

The user puts screenshots in either:
  docs/screenshots/<abstraction_id>.{png,jpg,jpeg,gif,webp}
  public/screenshots/<abstraction_id>.{png,jpg,jpeg,gif,webp}
  .ground-truth/screenshots/<abstraction_id>.{png,jpg,jpeg,gif,webp}

The renderer embeds matches as base64-encoded data URIs so the
dashboard remains a single self-contained HTML file.

This script also recognizes Storybook stories (*.stories.tsx, *.stories.jsx)
and links them so the engineer can open them externally.

Reads:  .ground-truth/data.json
Writes: same file, with screenshots[] and storybook_stories[] per abstraction
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

DATA_JSON = Path(".ground-truth/data.json")

SCREENSHOT_DIRS = [
    Path("docs/screenshots"),
    Path("public/screenshots"),
    Path(".ground-truth/screenshots"),
]
EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp")
MIME = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp",
}
MAX_BYTES = 1_500_000


def find_screenshot_for(abstraction_id: str) -> Path | None:
    for d in SCREENSHOT_DIRS:
        if not d.exists():
            continue
        for ext in EXTENSIONS:
            p = d / f"{abstraction_id}{ext}"
            if p.exists():
                return p
    return None


def encode_data_uri(p: Path) -> str | None:
    try:
        size = p.stat().st_size
        if size > MAX_BYTES:
            return None
        data = p.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{MIME.get(p.suffix.lower(), 'image/png')};base64,{b64}"
    except Exception:
        return None


def find_storybook_for(abstraction_id: str, files: list[dict]) -> list[str]:
    matches = []
    norm_id = abstraction_id.replace("_", "").replace("-", "").lower()
    for f in files:
        path = f["path"].lower()
        if not (".stories." in path or "/stories/" in path):
            continue
        name = path.rsplit("/", 1)[-1].split(".stories.")[0]
        norm_name = name.replace("_", "").replace("-", "")
        if norm_id in norm_name or norm_name in norm_id:
            matches.append(f["path"])
    return matches


def main() -> int:
    if not DATA_JSON.exists():
        print("ERROR: .ground-truth/data.json not found.", file=sys.stderr)
        return 1

    data = json.loads(DATA_JSON.read_text())
    abstractions = data.get("abstractions", [])
    files = data.get("files", [])

    if not abstractions:
        print("⏺ Screenshot scanner · no abstractions yet")
        return 0

    found_count = 0
    storybook_count = 0
    too_large = []

    for a in abstractions:
        screenshot_path = find_screenshot_for(a["id"])
        if screenshot_path:
            data_uri = encode_data_uri(screenshot_path)
            if data_uri:
                a["screenshot"] = {
                    "source_path": str(screenshot_path),
                    "data_uri": data_uri,
                    "size_kb": screenshot_path.stat().st_size // 1024,
                }
                found_count += 1
            else:
                too_large.append(str(screenshot_path))

        stories = find_storybook_for(a["id"], files)
        if stories:
            a["storybook_stories"] = stories
            storybook_count += len(stories)

    data["abstractions"] = abstractions
    DATA_JSON.write_text(json.dumps(data, indent=2))

    print(f"⏺ Screenshot scanner · scanning visual assets")
    print(f"  ▸ {found_count} screenshots embedded")
    if storybook_count:
        print(f"  ▸ {storybook_count} Storybook stories linked")
    if too_large:
        print(f"  ▸ {len(too_large)} screenshots skipped (over 1.5 MB)")
    if found_count == 0 and storybook_count == 0:
        print(f"  ▸ tip: put PNG/JPG files in docs/screenshots/<abstraction_id>.png to embed them")

    return 0


if __name__ == "__main__":
    sys.exit(main())
