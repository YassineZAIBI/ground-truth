#!/usr/bin/env python3
"""
Risk analyst — compute critical path and rank risks.

Reads:  .ground-truth/data.json (must contain abstractions[] with status from triage)
Writes: same file, with critical_path[], risks[]

Algorithm (deterministic part, before the LLM names them):

For each abstraction A, compute:
  - blast_radius(A) = number of abstractions transitively reachable
                      from A via the dependency graph (out-edges).
                      High = many things break if A breaks.

  - centrality(A)   = number of abstractions that depend on A
                      (transitive in-edges).
                      High = many things rely on A.

  - fragility(A)    = score derived from status + drift + tests:
                        broken     → 1.00
                        half-built → 0.70
                        unverified → 0.40
                        live       → 0.10 + 0.05 * drift_count
                        dead       → 0.00 (excluded)
                      capped at 1.00.

  - risk_score(A)   = (centrality / max_centrality) * fragility
                      (using centrality, not blast_radius — what matters
                      is "how many things rely on this thing being healthy",
                      not "how much can this thing reach")

Critical path:
  the chain of abstractions from any entry-point abstraction (one with
  zero in-edges and at least one out-edge to a live core piece) through
  the highest-centrality abstractions to the leaf "must work" pieces.
  Drawn on the dashboard as a highlighted path.

Top risks:
  the 5 abstractions with highest risk_score, plus a one-line
  natural-language explanation suitable for the Tech window.
  The LLM stage that follows fills in the explanation; this script
  only assigns the score and shortlist.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DATA_JSON = Path(".ground-truth/data.json")

FRAGILITY = {
    "broken": 1.00,
    "half-built": 0.70,
    "unverified": 0.40,
    "live": 0.10,
    "dead": 0.00,
}


def build_graph(abstractions: list[dict]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return (out_edges, in_edges) adjacency."""
    ids = {a["id"] for a in abstractions}
    out: dict[str, set[str]] = {a["id"]: set() for a in abstractions}
    inc: dict[str, set[str]] = {a["id"]: set() for a in abstractions}
    for a in abstractions:
        for rel in a.get("relationships", []):
            target = rel.get("target")
            if target in ids and target != a["id"]:
                out[a["id"]].add(target)
                inc[target].add(a["id"])
    return out, inc


def transitive(adj: dict[str, set[str]], start: str) -> set[str]:
    seen = set()
    stack = [start]
    while stack:
        n = stack.pop()
        for nb in adj.get(n, set()):
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    seen.discard(start)
    return seen


def compute_critical_path(abstractions: list[dict], out_edges: dict[str, set[str]],
                          in_edges: dict[str, set[str]]) -> list[str]:
    """Find the dominant path from entry → leaf through highest-centrality nodes."""
    if not abstractions:
        return []

    centralities = {a["id"]: len(transitive(in_edges, a["id"])) for a in abstractions}

    entry_candidates = [a for a in abstractions
                        if not in_edges.get(a["id"]) and out_edges.get(a["id"])]
    if not entry_candidates:
        entry_candidates = sorted(
            abstractions,
            key=lambda a: (len(in_edges.get(a["id"], set())), -len(out_edges.get(a["id"], set())))
        )[:1]

    leaf_candidates = [a for a in abstractions
                       if not out_edges.get(a["id"]) and in_edges.get(a["id"])]
    if not leaf_candidates:
        leaf_candidates = sorted(abstractions, key=lambda a: -centralities.get(a["id"], 0))[:1]

    best_path: list[str] = []
    best_score = -1

    for entry in entry_candidates:
        for leaf in leaf_candidates:
            path = bfs_path(out_edges, entry["id"], leaf["id"])
            if not path:
                continue
            score = sum(centralities.get(node, 0) for node in path)
            if score > best_score:
                best_score = score
                best_path = path

    return best_path


def bfs_path(adj: dict[str, set[str]], start: str, end: str) -> list[str]:
    if start == end:
        return [start]
    queue = [(start, [start])]
    seen = {start}
    while queue:
        node, path = queue.pop(0)
        for nb in adj.get(node, set()):
            if nb == end:
                return path + [nb]
            if nb not in seen:
                seen.add(nb)
                queue.append((nb, path + [nb]))
    return []


def compute_risks(abstractions: list[dict], in_edges: dict[str, set[str]],
                  drift_findings: list[dict]) -> list[dict]:
    if not abstractions:
        return []

    drift_by_abs: dict[str, int] = {}
    for d in drift_findings:
        if d.get("verdict") in ("CONTRADICTED", "PARTIAL"):
            for ref in d.get("references", []):
                drift_by_abs[ref] = drift_by_abs.get(ref, 0) + 1

    centralities = {a["id"]: len(transitive(in_edges, a["id"])) for a in abstractions}
    max_cent = max(centralities.values()) or 1

    scored = []
    for a in abstractions:
        if a.get("status") == "dead":
            continue

        base_frag = FRAGILITY.get(a.get("status", "live"), 0.5)
        drift_bonus = 0.05 * drift_by_abs.get(a["id"], 0)
        fragility = min(base_frag + drift_bonus, 1.00)

        centrality_score = centralities.get(a["id"], 0) / max_cent
        risk_score = centrality_score * fragility

        scored.append({
            "abstraction_id": a["id"],
            "name": a.get("name"),
            "status": a.get("status"),
            "centrality": centralities.get(a["id"], 0),
            "fragility": round(fragility, 3),
            "risk_score": round(risk_score, 3),
            "drift_count": drift_by_abs.get(a["id"], 0),
            "explanation": "",
        })

    scored.sort(key=lambda r: -r["risk_score"])
    return scored[:5]


def main() -> int:
    if not DATA_JSON.exists():
        print("ERROR: .ground-truth/data.json not found.", file=sys.stderr)
        return 1

    data = json.loads(DATA_JSON.read_text())
    abstractions = data.get("abstractions", [])

    if not abstractions:
        print("⏺ Risk analyst · no abstractions yet (run archaeologist first)")
        return 0

    out_edges, in_edges = build_graph(abstractions)
    critical_path = compute_critical_path(abstractions, out_edges, in_edges)
    risks = compute_risks(abstractions, in_edges, data.get("drift_findings", []))

    data["critical_path"] = critical_path
    data["risks"] = risks
    DATA_JSON.write_text(json.dumps(data, indent=2))

    print(f"⏺ Risk analyst · graph + risk scoring")
    if critical_path:
        names = []
        for cid in critical_path:
            for a in abstractions:
                if a["id"] == cid:
                    names.append(a.get("name", cid))
                    break
        print(f"  ▸ critical path: {' → '.join(names)}")
    if risks:
        print(f"  ▸ top risk: {risks[0]['name']} (score {risks[0]['risk_score']:.2f}, "
              f"{risks[0]['centrality']} dependents, fragility {risks[0]['fragility']:.2f})")
        print(f"  ▸ {len(risks)} risks shortlisted for narration")

    return 0


if __name__ == "__main__":
    sys.exit(main())
