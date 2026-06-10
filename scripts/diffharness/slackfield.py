#!/usr/bin/env python3
"""Window-gating slack sweep: ladder + gating metrics per level.

The dense2x2 adjudication left a post-hoc mechanism on the table: in a
dense mesh, parallel routes converge on shared downstream contacts
whose window STARTS gate departure, absorbing per-contact OWLT
differences - ties live where gating lives. This analyzer measures
both sides of that claim on one corpus level at a time:

  - the discrimination ladder (which key pins route identity), the
    same classification s5field.py computes;
  - gating: per dispatch, thread the selected route and record whether
    any hop's departure is gated (window start strictly later than the
    arrival at that node) and whether the final hop's is;
  - the joint: among tail-decided dispatches (ladder class key3, key4,
    or latent), the fraction whose selected route carries a gated hop.

Runs ride on s5field.py run (same results jsonl shape: lean hops are
(from, to, window_start) triples). Anchors for the registered sweep
live in out_s5/slack_sweep_predictions.json.

Usage:
  slackfield.py analyze --corpus <level root> --results <results.jsonl> \
      --out <report.json> [--glob 'slack_*']
"""

import argparse
import json
import sys
from collections import Counter
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from instrument import parse_ionrc, key1_oracle, grading_oracle, \
    spec_optimum, grade  # noqa: E402


def thread_route(adj, t0, hops):
    """Thread arrival through the selected route; return per-hop gating.

    hops: [(from_node, to_node, window_start), ...] from the runner.
    Returns (gated_flags, arrival) or raises if a hop has no contact.
    """
    t = t0
    flags = []
    for f, to, ts in hops:
        contact = None
        for c in adj[f]:
            if c[1] == to and c[2] == ts:
                contact = c
                break
        if contact is None:
            raise KeyError(f"no contact {f}->{to} start {ts}")
        gated = contact[2] > t
        depart = contact[2] if gated else t
        if depart > contact[3]:
            raise ValueError(f"hop departs after window end: {f}->{to}")
        t = depart + contact[4]
        flags.append(gated)
    return flags, t


def ladder_class(adj, src, dst, t0, lean):
    """s5field.py's ladder classification for one found dispatch."""
    a = lean["arrival"]
    depth = len(lean["hops"])
    tuples = grading_oracle(adj, src, dst, t0, a, depth)
    if not tuples:
        return None, None
    hmin = min(t[0] for t in tuples)
    at_h = [t for t in tuples if t[0] == hmin]
    if len(at_h) == 1:
        return "keys12", tuples
    tmax = max(t[1] for t in at_h)
    at_ht = [t for t in at_h if t[1] == tmax]
    if len(at_ht) == 1:
        return "key3", tuples
    emin = min(t[2] for t in at_ht)
    at_full = [t for t in at_ht if t[2] == emin]
    return ("key4" if len(at_full) == 1 else "latent"), tuples


def cmd_analyze(args):
    corpus = Path(args.corpus)
    found = none_agreed = 0
    k1_disagreements = []
    grades = Counter()
    ladder = Counter()
    gating = Counter()
    tail_gated = Counter()
    plan_cache = {}
    for line in open(args.results):
        rec = json.loads(line)
        if "error" in rec:
            print(f"RUN ERROR {rec['plan_id']}: {rec['error']}",
                  file=sys.stderr)
            continue
        pid = rec["plan_id"]
        if pid not in plan_cache:
            cs = parse_ionrc(corpus / pid / "contact_plan.ionrc")
            adj = defaultdict(list)
            for c in cs:
                adj[c[0]].append(c)
            nm = json.load(open(corpus / pid
                                / "plan_manifest.json"))["node_map"]
            plan_cache[pid] = (adj, nm)
        adj, nm = plan_cache[pid]
        for q in rec["results"]:
            src, dst, t0 = nm[q["src"]], nm[q["dst"]], q["t0"]
            lean = q["lean"]
            k1 = key1_oracle(adj, src, dst, t0)
            if lean is None:
                if k1 is None:
                    none_agreed += 1
                else:
                    k1_disagreements.append([pid, q["src"], q["dst"], t0])
                continue
            found += 1
            if k1 != lean["arrival"]:
                k1_disagreements.append([pid, q["src"], q["dst"], t0])
                continue
            cls, tuples = ladder_class(adj, src, dst, t0, lean)
            if cls is None:
                print(f"GRADING ORACLE EMPTY {pid}", file=sys.stderr)
                sys.exit(1)
            ladder[cls] += 1
            sopt = spec_optimum(tuples)
            term = None
            for f, t, ts in lean["hops"]:
                for c in adj[f]:
                    if c[1] == t and c[2] == ts:
                        term = c[3] if term is None or c[3] < term else term
                        break
            grades["lean_" + grade(
                (len(lean["hops"]), term, lean["hops"][0][1]), sopt)] += 1

            flags, arr = thread_route(adj, t0, lean["hops"])
            if arr != lean["arrival"]:
                print(f"THREAD MISMATCH {pid} {q}", file=sys.stderr)
                sys.exit(1)
            if flags[-1]:
                gating["final"] += 1
            if any(flags):
                gating["any"] += 1
            if cls != "keys12":
                tail_gated["tail"] += 1
                if any(flags):
                    tail_gated["tail_gated_any"] += 1
                if flags[-1]:
                    tail_gated["tail_gated_final"] += 1

    n = found or 1
    tail = tail_gated["tail"] or 1
    report = {
        "found_dispatches": found,
        "none_both_sides": none_agreed,
        "key1_disagreements": len(k1_disagreements),
        "key1_cases": k1_disagreements[:10],
        "lean_grades": dict(sorted(grades.items())),
        "ladder": {k: [v, round(100 * v / n, 1)]
                   for k, v in sorted(ladder.items())},
        "keys12_pin_pct": round(100 * ladder["keys12"] / n, 1),
        "tie_mass_pct": round(100 * (n - ladder["keys12"]) / n, 1),
        "gating_final_pct": round(100 * gating["final"] / n, 1),
        "gating_any_pct": round(100 * gating["any"] / n, 1),
        "tail_dispatches": tail_gated["tail"],
        "tail_gated_any_pct": round(
            100 * tail_gated["tail_gated_any"] / tail, 1),
        "tail_gated_final_pct": round(
            100 * tail_gated["tail_gated_final"] / tail, 1),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze")
    a.add_argument("--corpus", required=True)
    a.add_argument("--results", required=True)
    a.add_argument("--out", required=True)
    a.set_defaults(fn=cmd_analyze)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
