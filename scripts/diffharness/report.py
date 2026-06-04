#!/usr/bin/env python3
"""Assemble agreement_report.json from a differential run's JSONL.

Gating criteria (algorithm.md §9.3): found/none verdict, and exact earliest
arrival on found/found pairs. Hop-sequence equality is reported and
characterized but not gated; every hop divergence must sit at an arrival tie
(equal arrival, different route choice — the §3.2.8.1.4 keys-3/4 class), and
any that does not is surfaced as unexplained.

Usage: report.py --jsonl <diff_results.jsonl> --out <agreement_report.json>
"""

import argparse
import json
from collections import Counter
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = [json.loads(l) for l in Path(args.jsonl).read_text().splitlines()]
    report = {
        "plans": len(rows),
        "plan_errors": [],
        "queries": 0,
        "agree_gating": 0,
        "verdict_found_found": 0,
        "verdict_none_none": 0,
        "verdict_mismatch": [],
        "arrival_mismatch": [],
        "hops_equal": 0,
        "hop_divergence_at_arrival_tie": 0,
        "hop_divergence_unexplained": [],
        "by_query_class": {},
    }
    per_class = Counter()
    per_class_agree = Counter()

    for r in rows:
        if "error" in r:
            report["plan_errors"].append(
                {"plan_id": r["plan_id"], "error": r["error"]})
            continue
        for q in r["results"]:
            report["queries"] += 1
            cls = f"{q['src']}->{q['dst']}"
            per_class[cls] += 1
            both_found = q["lean"] is not None and q["ion"] is not None
            both_none = q["lean"] is None and q["ion"] is None
            gating = q["agree_verdict"] and q["agree_arrival"] is not False
            report["agree_gating"] += bool(gating)
            per_class_agree[cls] += bool(gating)
            if both_found:
                report["verdict_found_found"] += 1
            if both_none:
                report["verdict_none_none"] += 1
            if not q["agree_verdict"]:
                report["verdict_mismatch"].append(
                    {"plan_id": r["plan_id"], **{k: q[k] for k in
                     ("src", "dst", "t0", "lean", "ion", "raw")}})
            elif both_found and not q["agree_arrival"]:
                report["arrival_mismatch"].append(
                    {"plan_id": r["plan_id"], **{k: q[k] for k in
                     ("src", "dst", "t0", "lean", "ion", "raw")}})
            if q["agree_hops"]:
                report["hops_equal"] += 1
            elif both_found:
                if q["agree_arrival"]:
                    # equal arrival, different route: tie-break divergence
                    report["hop_divergence_at_arrival_tie"] += 1
                else:
                    report["hop_divergence_unexplained"].append(
                        {"plan_id": r["plan_id"], "src": q["src"],
                         "dst": q["dst"], "t0": q["t0"], "raw": q["raw"]})

    report["by_query_class"] = {
        cls: {"queries": per_class[cls], "agree": per_class_agree[cls]}
        for cls in sorted(per_class)}
    report["gate_passed"] = (
        not report["plan_errors"]
        and not report["verdict_mismatch"]
        and not report["arrival_mismatch"]
        and not report["hop_divergence_unexplained"])

    Path(args.out).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if not isinstance(v, (list, dict))}, indent=2))
    print("by_query_class:")
    for cls, st in report["by_query_class"].items():
        print(f"  {cls}: {st['agree']}/{st['queries']}")
    print(f"gate_passed: {report['gate_passed']}")


if __name__ == "__main__":
    main()
