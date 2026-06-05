#!/usr/bin/env python3
"""S1 corpus instrumentation over recorded differential results.

Reads diff_results.jsonl plus the corpus ionrc plans and measures, without
any ION or sabrsearch runs:

  - owlt distribution (the delay-degeneracy profile of the corpus);
  - per-dispatch tie classification: does another route reach the recorded
    optimal arrival with no more hops than the returned one (multiplicity
    among minimal-hop optima; same-multiset reorderings of the returned
    route are not counted, a documented non-case on chain-constrained
    plans);
  - per-dispatch minimal hop count at the optimal arrival, by bounded
    exhaustive enumeration (exact: enumeration depth equals the returned
    route's hop count, and any strictly shorter optimum lies within it);
  - identity excess for both sides: returned hops minus minimal hops at
    the optimum. A positive excess is a 3.2.8.1.4 key-2 shortfall against
    the full valid-route class (the visited-set identity finding of
    docs/notes/2026-06-05-visited-list-finding.md, measured in the field).

Validator: the enumerator independently recomputes the optimal arrival via
the section 3.1 recursion (integer arithmetic, exact on this corpus) and
aborts if it ever disagrees with the recorded lean arrival - the kernel-
checked side anchors the python reimplementation on every dispatch.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def parse_ionrc(path):
    """Contacts as (from, to, start, end, owlt) ints; range joined by key."""
    contacts = []
    ranges = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if line.startswith("a contact"):
            s, e = int(parts[2].lstrip("+")), int(parts[3].lstrip("+"))
            contacts.append([int(parts[4]), int(parts[5]), s, e])
        elif line.startswith("a range"):
            s = int(parts[2].lstrip("+"))
            ranges[(int(parts[4]), int(parts[5]), s)] = int(parts[6])
    out = []
    for f, t, s, e in contacts:
        out.append((f, t, s, e, ranges.get((f, t, s), 0)))
    return out


def enumerate_optima(contacts, src, dst, t0, arrival, max_hops):
    """Exhaustively walk no-reuse chains from src up to max_hops deep,
    pruning on partial arrival > arrival (sound: owlt >= 0 on this corpus).

    Returns (best_arrival_found, hop-count histogram of routes arriving
    exactly at `arrival`)."""
    adj = defaultdict(list)
    for c in contacts:
        adj[c[0]].append(c)
    best = [None]
    hist = Counter()

    def step(t, c):
        tx = max(t, c[2])
        if tx > c[3]:
            return None
        return tx + c[4]

    def dfs(node, t, depth, used):
        if depth >= max_hops:
            return
        for c in adj[node]:
            if id(c) in used:
                continue
            t2 = step(t, c)
            if t2 is None or t2 > arrival:
                continue
            if c[1] == dst:
                if best[0] is None or t2 < best[0]:
                    best[0] = t2
                if t2 == arrival:
                    hist[depth + 1] += 1
            used.add(id(c))
            dfs(c[1], t2, depth + 1, used)
            used.discard(id(c))

    dfs(src, t0, 0, set())
    return best[0], hist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="out_diff_v3/diff_results.jsonl")
    ap.add_argument("--corpus", required=True,
                    help="corpus root holding <plan_id>/contact_plan.ionrc")
    ap.add_argument("--out", default="out_diff_v3/instrumentation_report.json")
    args = ap.parse_args()

    corpus = Path(args.corpus)
    owlt_hist = Counter()
    plan_cache = {}
    nodemap_cache = {}

    stats = Counter()
    lean_excess_hist = Counter()
    ion_excess_hist = Counter()
    tie_count = 0
    found = 0
    offenders = []

    for line in open(args.results):
        rec = json.loads(line)
        pid = rec["plan_id"]
        if pid not in plan_cache:
            pdir = corpus / pid
            plan_cache[pid] = parse_ionrc(pdir / "contact_plan.ionrc")
            nodemap_cache[pid] = json.load(
                open(pdir / "plan_manifest.json"))["node_map"]
            for c in plan_cache[pid]:
                owlt_hist[c[4]] += 1
        contacts = plan_cache[pid]
        nm = nodemap_cache[pid]
        for q in rec["results"]:
            lean, ion = q.get("lean"), q.get("ion")
            if not lean or not ion or lean.get("hops") is None \
                    or ion.get("hops") is None:
                stats["none_none"] += 1
                continue
            found += 1
            a = lean["arrival"]
            kL, kI = len(lean["hops"]), len(ion["hops"])
            src, dst, t0 = nm[q["src"]], nm[q["dst"]], q["t0"]
            best, hist = enumerate_optima(contacts, src, dst, t0, a,
                                          max(kL, kI))
            if best != a:
                print(f"VALIDATOR FAILURE {pid} {q['src']}->{q['dst']} "
                      f"t0={t0}: enumerator best {best} != recorded {a}",
                      file=sys.stderr)
                sys.exit(1)
            min_hops = min(hist) if hist else None
            if min_hops is None:
                print(f"VALIDATOR FAILURE {pid}: no route at optimum",
                      file=sys.stderr)
                sys.exit(1)
            le, ie = kL - min_hops, kI - min_hops
            lean_excess_hist[le] += 1
            ion_excess_hist[ie] += 1
            if le > 0:
                offenders.append({"plan": pid, "src": q["src"],
                                  "dst": q["dst"], "t0": t0, "side": "lean",
                                  "hops": kL, "min": min_hops})
            # tie among minimal-hop optima: another route at the optimal
            # arrival with <= kL hops (the returned route is one of them)
            if sum(n for h, n in hist.items() if h <= kL) >= 2:
                tie_count += 1

    report = {
        "found_dispatches": found,
        "none_none": stats["none_none"],
        "owlt_range_entries": dict(sorted(owlt_hist.items())),
        "tie_among_minhop_optima": tie_count,
        "tie_rate": round(tie_count / found, 4) if found else None,
        "lean_hop_excess_hist": dict(sorted(lean_excess_hist.items())),
        "ion_hop_excess_hist": dict(sorted(ion_excess_hist.items())),
        "lean_excess_offenders": offenders,
    }
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1)[:1200])


if __name__ == "__main__":
    main()
