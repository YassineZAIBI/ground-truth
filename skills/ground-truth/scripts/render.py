#!/usr/bin/env python3
"""
Renderer v2 — produces all artifacts including endpoints, risks, screenshots.

Reads:  .ground-truth/data.json
        .ground-truth/voice.yaml (optional)

Writes: GROUND_TRUTH.md
        BUSINESS_MIRROR.md
        .ground-truth/dashboard.html
        .ground-truth/drift-report.md
        .ground-truth/history/<timestamp>.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from string import Template
from typing import Any

DATA_JSON = Path(".ground-truth/data.json")
VOICE_YAML = Path(".ground-truth/voice.yaml")
HISTORY_DIR = Path(".ground-truth/history")
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

STATUS_TO_BUSINESS = {
    "live": "working", "unverified": "working",
    "half-built": "half-finished", "broken": "broken", "dead": "dead",
}


def load_voice() -> dict[str, Any]:
    if not VOICE_YAML.exists():
        return {
            "project": {"name": Path.cwd().name, "tagline": None, "voice": "neutral"},
            "vocabulary": {"unit_of_work": "request", "primary_actor": "user",
                          "capability": "feature", "data_record": "session"},
            "style": {"capitalization": "sentence", "contractions": "yes", "jargon_to_avoid": []},
            "abstraction_naming": {"pattern": "literal"},
        }
    try:
        import yaml
        return yaml.safe_load(VOICE_YAML.read_text()) or {}
    except ImportError:
        return _parse_simple_yaml(VOICE_YAML.read_text())


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    stack = [(0, out)]
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else out
        if ":" in line:
            key, _, val = line.strip().partition(":")
            val = val.strip()
            if not val:
                parent[key] = {}
                stack.append((indent, parent[key]))
            else:
                parent[key] = val.strip("\"'")
    return out


def write_history(data: dict[str, Any]) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    snap = HISTORY_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
    snap.write_text(json.dumps(data, indent=2))


def cap_plural(voice: dict) -> str:
    cap = voice.get('vocabulary', {}).get('capability', 'feature')
    return cap + ('s' if not cap.endswith('s') else '')


def loc_of(file_path: str, data: dict) -> int:
    for fr in data.get("files", []):
        if fr.get("path") == file_path:
            return fr.get("loc", 0)
    return 0


def render_ground_truth_md(data: dict, voice: dict) -> str:
    project = voice.get("project", {})
    project_name = project.get("name", "this project")
    abstractions = data.get("abstractions", [])
    drift = data.get("drift_findings", [])
    risks = data.get("risks", [])
    endpoints = data.get("endpoints", [])
    critical_path = data.get("critical_path", [])

    by_status: dict[str, list] = {"live": [], "unverified": [], "half-built": [], "broken": [], "dead": []}
    for a in abstractions:
        by_status.setdefault(a.get("status", "unclear"), []).append(a)

    out = []
    out.append(f"# Ground Truth — {project_name}\n")
    out.append(f"_Generated {data.get('scanned_at', '?')} from commit "
               f"{data.get('last_commit', '?')[:7]}. {len(abstractions)} {cap_plural(voice)} analyzed._\n")

    out.append("## Executive summary\n")
    if data.get("business_summary"):
        out.append(data["business_summary"] + "\n")
    else:
        out.append(f"This project has {len(abstractions)} core {cap_plural(voice)}. "
                   f"{len(by_status['live'])} are fully working. "
                   f"{len(by_status['half-built'])} are half-built. "
                   f"{len(by_status['broken'])} are broken.\n")

    if risks:
        out.append("\n## Critical path & top risks\n")
        if critical_path:
            id_to_name = {a["id"]: a.get("name", a["id"]) for a in abstractions}
            path_names = " → ".join(id_to_name.get(cid, cid) for cid in critical_path)
            out.append(f"**Critical path:** {path_names}\n")
        out.append("\n**Top risks:**\n")
        for i, r in enumerate(risks, 1):
            out.append(f"{i}. **{r.get('name', '?')}** — {r.get('explanation', '')}")
            out.append(f"   _score {r.get('risk_score', 0):.2f} · {r.get('centrality', 0)} dependents · "
                       f"fragility {r.get('fragility', 0):.2f}_")

    out.append(f"\n## The {len(abstractions)} {cap_plural(voice)}\n")
    out.append("| # | Name | Literal | Status | LOC | Callers | Drift |")
    out.append("|---|------|---------|--------|-----|---------|-------|")
    for i, a in enumerate(abstractions, 1):
        loc = sum(loc_of(f, data) for f in a.get("files", []))
        drift_count = sum(1 for d in drift if a["id"] in d.get("references", []))
        out.append(f"| {i} | {a.get('name', '?')} | {a.get('literal_name', '')} | "
                   f"{a.get('status', '?')} | {loc} | {a.get('callers_total', 0)} | "
                   f"{drift_count or '—'} |")

    if endpoints:
        out.append(f"\n## API tree ({len(endpoints)} endpoints)\n")
        by_prefix: dict[str, list] = {}
        for ep in endpoints:
            prefix = "/" + ep["path"].strip("/").split("/")[0] if ep["path"] != "/" else "/"
            by_prefix.setdefault(prefix, []).append(ep)
        for prefix, eps in sorted(by_prefix.items()):
            out.append(f"### `{prefix}`\n")
            for ep in eps:
                doc = f" — {ep['purpose_doc']}" if ep.get("purpose_doc") else ""
                out.append(f"- `{ep['method']:6s} {ep['path']}` "
                           f"→ `{ep['handler_file']}`{doc}")

    if drift:
        out.append("\n## Drift findings\n")
        for d in drift:
            out.append(f"### {d.get('verdict', '?')} — {d.get('claim', '')[:80]}")
            out.append(f"- claim: `{d.get('source', '?')}` — \"{d.get('claim', '')}\"")
            out.append(f"- evidence: {d.get('evidence', '')}")
            out.append(f"- recommended fix: {d.get('recommended_fix', '')}\n")

    if by_status["dead"]:
        out.append("\n## Dead code\n")
        for a in by_status["dead"]:
            files = a.get("files", [""])
            out.append(f"- `{files[0] if files else '?'}` — {a.get('purpose_oneline', '')}")

    out.append("\n## Open questions\n")
    for u in data.get("unknowns", []):
        out.append(f"- {u}")
    if not data.get("unknowns"):
        out.append("- (none recorded)")

    return "\n".join(out) + "\n"


def render_business_mirror_md(data: dict, voice: dict) -> str:
    project = voice.get("project", {})
    project_name = project.get("name", "your project")
    abstractions = [a for a in data.get("abstractions", []) if a.get("status") != "dead"]

    by_business = {"working": [], "half-finished": [], "broken": []}
    for a in abstractions:
        bucket = STATUS_TO_BUSINESS.get(a.get("status", ""), "working")
        if bucket in by_business:
            by_business[bucket].append(a)

    out = []
    out.append(f"# What you've actually built — {project_name}\n")
    out.append("_Plain-language version. No code paths, no jargon._\n")

    if data.get("business_summary"):
        out.append("## In one paragraph\n")
        out.append(data["business_summary"] + "\n")

    out.append(f"## The {len(abstractions)} {cap_plural(voice)}\n")

    if by_business["working"]:
        out.append(f"### ✓ Working ({len(by_business['working'])})")
        for a in by_business["working"]:
            line = f"- **{a.get('name', '?')}** — {a.get('purpose_oneline', '')}"
            if a.get("business_outcome"):
                line += f" _If this breaks: {a['business_outcome']}_"
            if a.get("status") == "unverified":
                line += " _(works but untested)_"
            out.append(line)
        out.append("")

    if by_business["half-finished"]:
        out.append(f"### ⊘ Half-finished ({len(by_business['half-finished'])})")
        for a in by_business["half-finished"]:
            line = f"- **{a.get('name', '?')}** — {a.get('purpose_oneline', '')}"
            if a.get("business_outcome"):
                line += f" _Cost of not finishing: {a['business_outcome']}_"
            out.append(line)
        out.append("")

    if by_business["broken"]:
        out.append(f"### ✕ Broken ({len(by_business['broken'])})")
        for a in by_business["broken"]:
            line = f"- **{a.get('name', '?')}** — {a.get('purpose_oneline', '')}"
            if a.get("business_outcome"):
                line += f" _Until fixed: {a['business_outcome']}_"
            out.append(line)
        out.append("")

    contradicted = [d for d in data.get("drift_findings", []) if d.get("verdict") == "CONTRADICTED"]
    if contradicted:
        out.append("## Promises in the docs that aren't really there yet\n")
        for i, d in enumerate(contradicted[:5], 1):
            out.append(f"{i}. {d.get('claim', '?')} — {d.get('evidence', '?')}")
        out.append("")

    out.append("---")
    out.append("\n_For the engineering view, see GROUND_TRUTH.md._")
    out.append("_For the interactive map, open .ground-truth/dashboard.html._\n")

    return "\n".join(out) + "\n"


def render_drift_report_md(data: dict) -> str:
    drift = data.get("drift_findings", [])
    if not drift:
        return "# Drift report\n\nNo drift findings.\n"

    by_verdict: dict[str, list] = {"CONTRADICTED": [], "PARTIAL": [], "ABSENT": [], "CONFIRMED": []}
    for d in drift:
        by_verdict.setdefault(d.get("verdict", "OTHER"), []).append(d)

    out = ["# Drift report\n"]
    for verdict in ["CONTRADICTED", "PARTIAL", "ABSENT", "CONFIRMED"]:
        if not by_verdict[verdict]:
            continue
        out.append(f"## {verdict} ({len(by_verdict[verdict])})\n")
        for d in by_verdict[verdict]:
            out.append(f"### {d.get('claim', '?')}")
            out.append(f"- source: `{d.get('source', '?')}`")
            out.append(f"- evidence: {d.get('evidence', '?')}")
            out.append(f"- fix: {d.get('recommended_fix', '?')}\n")

    return "\n".join(out) + "\n"


def render_dashboard_html(data: dict, voice: dict) -> str:
    template_path = TEMPLATE_DIR / "dashboard.html"
    if not template_path.exists():
        raise SystemExit(
            f"FATAL: dashboard template missing at {template_path}\n"
            "The skill installation is incomplete. Re-install the plugin."
        )
    template = template_path.read_text()

    required_markers = [
        "ground-truth-template-v2.2",
        'id="window-biz"',
        'id="window-tech"',
        'id="window-api"',
        "$DATA_JSON",
        "$PROJECT_NAME",
    ]
    missing = [m for m in required_markers if m not in template]
    if missing:
        raise SystemExit(
            f"FATAL: dashboard template at {template_path} is corrupted.\n"
            f"Missing markers: {missing}\n"
            "Re-install the plugin to restore the official template."
        )

    abstractions = data.get("abstractions", [])
    biz_abstractions = [a for a in abstractions if a.get("status") != "dead"]
    project = voice.get("project", {})

    by_business = {"working": [], "half-finished": [], "broken": []}
    for a in biz_abstractions:
        bucket = STATUS_TO_BUSINESS.get(a.get("status", ""), "working")
        if bucket in by_business:
            by_business[bucket].append(a)

    most_urgent = None
    for a in biz_abstractions:
        if a.get("status") == "broken":
            most_urgent = a
            break
    if not most_urgent:
        for a in biz_abstractions:
            if a.get("status") == "half-built":
                most_urgent = a
                break

    drift = data.get("drift_findings", [])
    risks = data.get("risks", [])
    critical_path = data.get("critical_path", [])
    endpoints = data.get("endpoints", [])

    payload = {
        "project_name": project.get("name", "your project"),
        "scanned_at": data.get("scanned_at", "?"),
        "summary": data.get("business_summary", ""),
        "totals": {
            "all": len(biz_abstractions),
            "working": len(by_business["working"]),
            "half_finished": len(by_business["half-finished"]),
            "broken": len(by_business["broken"]),
        },
        "tech_totals": {
            "total": len(abstractions),
            "live": sum(1 for a in abstractions if a.get("status") == "live"),
            "drift_count": len(drift),
            "stale_claude_md": sum(1 for d in drift if "CLAUDE.md" in d.get("source", "")),
            "endpoints_count": len(endpoints),
        },
        "most_urgent": {
            "name": most_urgent.get("name", "") if most_urgent else None,
            "what_to_watch_for": most_urgent.get("purpose_oneline", "") if most_urgent else None,
            "business_outcome": most_urgent.get("business_outcome", "") if most_urgent else None,
        } if most_urgent else None,
        "abstractions": [
            {
                "id": a.get("id", ""),
                "name": a.get("name", "?"),
                "literal_name": a.get("literal_name", ""),
                "status": a.get("status", ""),
                "business_status": STATUS_TO_BUSINESS.get(a.get("status", ""), "working"),
                "purpose": a.get("purpose_oneline", ""),
                "tech_purpose": a.get("tech_purpose", a.get("purpose_oneline", "")),
                "business_outcome": a.get("business_outcome", ""),
                "loc": sum(loc_of(f, data) for f in a.get("files", [])),
                "files": a.get("files", []),
                "callers": a.get("callers_total", 0),
                "relationships": a.get("relationships", []),
                "screenshot": a.get("screenshot", {}).get("data_uri", "") if a.get("screenshot") else "",
                "storybook_stories": a.get("storybook_stories", []),
                "endpoints": [
                    {"method": ep["method"], "path": ep["path"], "purpose": ep.get("purpose_doc", "")}
                    for ep in endpoints if ep.get("abstraction_id") == a.get("id")
                ],
                "on_critical_path": a.get("id") in critical_path,
            }
            for a in abstractions
        ],
        "biz_abstractions": [a.get("id") for a in biz_abstractions],
        "drift": [
            {
                "claim": d.get("claim", ""),
                "verdict": d.get("verdict", ""),
                "source": d.get("source", ""),
                "evidence": d.get("evidence", ""),
                "references": d.get("references", []),
            }
            for d in drift
        ],
        "risks": risks,
        "critical_path": critical_path,
        "endpoints_grouped": _group_endpoints(endpoints),
        "mermaid_source": _build_mermaid(abstractions, voice, critical_path),
    }

    html = Template(template).safe_substitute(
        DATA_JSON=json.dumps(payload),
        PROJECT_NAME=project.get("name", "your project"),
        SCANNED_AT=data.get("scanned_at", "?"),
    )
    return html


def _group_endpoints(endpoints: list[dict]) -> list[dict]:
    """Group endpoints by route prefix for the API tree view."""
    groups: dict[str, list] = {}
    for ep in endpoints:
        path = ep.get("path", "/")
        if path == "/" or path == "":
            prefix = "/"
        else:
            parts = path.strip("/").split("/")
            prefix = "/" + parts[0]
        groups.setdefault(prefix, []).append({
            "method": ep["method"],
            "path": ep["path"],
            "handler_file": ep["handler_file"],
            "purpose": ep.get("purpose_doc", ""),
            "abstraction_id": ep.get("abstraction_id"),
        })
    return [
        {"prefix": k, "endpoints": sorted(v, key=lambda e: (e["path"], e["method"]))}
        for k, v in sorted(groups.items())
    ]


def _build_mermaid(abstractions: list[dict], voice: dict, critical_path: list[str]) -> str:
    lines = ["flowchart TB", ""]
    crit_set = set(critical_path)
    for a in abstractions:
        if a.get("status") == "dead":
            continue
        aid = a.get("id", "n")
        name = a.get("name", "?")
        lit = a.get("literal_name", "")
        loc_total = sum(loc_of(f, {"files": []}) for f in a.get("files", []))
        loc_str = f"{lit} · {loc_total} LOC" if lit else ""
        node_label = (f'{name}<br/><span style=\'font-size:11px;opacity:.7\'>{loc_str}</span>'
                      if loc_str else name)
        cls = a.get("status", "live").replace("-", "_")
        if aid in crit_set:
            cls += "_crit"
        lines.append(f'  {aid}["{node_label}"]:::{cls}')

    lines.append("")
    for a in abstractions:
        if a.get("status") == "dead":
            continue
        for rel in a.get("relationships", []):
            verb = rel.get("verb", "calls")
            target = rel.get("target", "")
            flow = rel.get("flow", "runtime")
            arrow = f"-- {verb} -->" if flow == "runtime" else f"-. {verb} .->"
            lines.append(f"  {a.get('id', 'n')} {arrow} {target}")

    lines.append("")
    lines.append("  classDef live fill:#C0DD97,stroke:#3B6D11,color:#173404")
    lines.append("  classDef unverified fill:#FAC775,stroke:#854F0B,color:#412402")
    lines.append("  classDef half_built fill:#F5C4B3,stroke:#993C1D,color:#4A1B0C")
    lines.append("  classDef broken fill:#F7C1C1,stroke:#A32D2D,color:#501313")
    lines.append("  classDef live_crit fill:#C0DD97,stroke:#854F0B,stroke-width:3px,color:#173404")
    lines.append("  classDef unverified_crit fill:#FAC775,stroke:#854F0B,stroke-width:3px,color:#412402")
    lines.append("  classDef half_built_crit fill:#F5C4B3,stroke:#854F0B,stroke-width:3px,color:#4A1B0C")
    lines.append("  classDef broken_crit fill:#F7C1C1,stroke:#854F0B,stroke-width:3px,color:#501313")
    return "\n".join(lines)


def main() -> int:
    if not DATA_JSON.exists():
        print("ERROR: .ground-truth/data.json not found.", file=sys.stderr)
        return 1

    data = json.loads(DATA_JSON.read_text())
    voice = load_voice()

    write_history(data)

    Path("GROUND_TRUTH.md").write_text(render_ground_truth_md(data, voice))
    Path("BUSINESS_MIRROR.md").write_text(render_business_mirror_md(data, voice))
    (Path(".ground-truth") / "drift-report.md").write_text(render_drift_report_md(data))
    (Path(".ground-truth") / "dashboard.html").write_text(render_dashboard_html(data, voice))

    sizes = {
        "GROUND_TRUTH.md": Path("GROUND_TRUTH.md").stat().st_size,
        "BUSINESS_MIRROR.md": Path("BUSINESS_MIRROR.md").stat().st_size,
        "dashboard.html": (Path(".ground-truth") / "dashboard.html").stat().st_size,
        "drift-report.md": (Path(".ground-truth") / "drift-report.md").stat().st_size,
    }
    print("⏺ Renderer · writing artifacts")
    for name, sz in sizes.items():
        print(f"  ▸ {name} ({sz/1024:.1f} KB)")

    dashboard_text = (Path(".ground-truth") / "dashboard.html").read_text()
    required_in_output = [
        "ground-truth-template-v2.2",
        'id="window-biz"',
        'id="window-tech"',
        'id="window-api"',
    ]
    missing_in_output = [m for m in required_in_output if m not in dashboard_text]
    if missing_in_output:
        print(f"\n  ⚠ WARNING: rendered dashboard is missing markers: {missing_in_output}", file=sys.stderr)
        print("  This indicates the template was not applied correctly.", file=sys.stderr)
        return 2

    cwd = Path.cwd().absolute()
    print(f"\n  ✓ Dashboard ready: file://{cwd}/.ground-truth/dashboard.html")

    return 0


if __name__ == "__main__":
    sys.exit(main())
