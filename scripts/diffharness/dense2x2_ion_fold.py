#!/usr/bin/env python3
"""Live ION fold-in for dense2x2 results (HETERO/HOMOG).

Reads existing dense2x2_*_results.jsonl (lean only, ion=null), runs live
ION (serial, one IonNode boot per distinct src per plan) for the nulls,
writes ion values, and emits updated results jsonl with ions folded in.
Incremental: records completed (plan_id, src) in a .done sidecar; skips
on restart. Writes each plan's updated row immediately on completion.

Usage (HETERO focus per registered MIXED cell):
  python scripts/diffharness/dense2x2_ion_fold.py \
      --results out_s5/dense2x2_HETERO_results.jsonl \
      --corpus <cislunar-lab>/out/dense2x2_v1/HETERO \
      --out out_s5/dense2x2_HETERO_results_ion.jsonl \
      [--limit-plans 10]

After, copy or mv the _ion to the canonical, re-analyze if reports need ION cols.
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ion_node import IonNode, fetch_routes, _ion_chosen, purge_ion  # noqa: E402


def load_plan_results(results_path, plan_id):
    for line in open(results_path):
        rec = json.loads(line)
        if rec.get("plan_id") == plan_id:
            return rec.get("results", [])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True, help="existing dense2x2_*_results.jsonl with lean+ion=null")
    ap.add_argument("--corpus", required=True, help="dir holding the dense2x2_*/ plan dirs")
    ap.add_argument("--out", required=True, help="output results jsonl with ion folded")
    ap.add_argument("--limit-plans", type=int, default=None)
    ap.add_argument("--settle", type=float, default=1.0)
    args = ap.parse_args()

    results_p = Path(args.results)
    corpus = Path(args.corpus)
    out_p = Path(args.out)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    # resume: which plans already fully done in out (have no null ions)
    done_plans = set()
    plan_ions = {}  # plan_id -> list of result dicts with ion filled
    if out_p.exists():
        for line in open(out_p):
            rec = json.loads(line)
            pid = rec.get("plan_id")
            if pid:
                rs = rec.get("results", [])
                if rs and all(r.get("ion") is not None or r.get("lean") is None for r in rs):
                    done_plans.add(pid)
                plan_ions[pid] = rs

    # plans needing work: from input results that have at least one ion null
    plans_to_do = []
    for line in open(results_p):
        rec = json.loads(line)
        pid = rec.get("plan_id")
        if not pid or pid in done_plans:
            continue
        rs = rec.get("results", [])
        has_null = any(r.get("ion") is None and r.get("lean") is not None for r in rs)
        if has_null:
            plans_to_do.append(pid)
    if args.limit_plans:
        plans_to_do = plans_to_do[:args.limit_plans]
    print(f"{len(done_plans)} plans already ion-complete in out; {len(plans_to_do)} to process", flush=True)

    with open(out_p, "a") as sink:
        for i, pid in enumerate(plans_to_do):
            pdir = corpus / pid
            if not pdir.exists():
                print(f"[{i+1}] SKIP missing {pid}", flush=True)
                continue
            t0 = time.time()
            try:
                nm = json.load(open(pdir / "plan_manifest.json"))["node_map"]
                # group queries by src exactly as validate_plan
                queries = []
                for line in open(pdir / "pairs.jsonl"):
                    p = json.loads(line)
                    if p.get("query"):
                        queries.append({"src": p["src"], "dst": p["dst"], "t0": p["t0_s"]})
                by_src = defaultdict(list)
                for q in queries:
                    by_src[q["src"]].append(q)

                # load the lean results for this plan to fold against
                lean_rows = load_plan_results(results_p, pid) or []
                lean_by_key = {(r["src"], r["dst"], r["t0"]): r for r in lean_rows}

                ion_filled = []
                for src in sorted(by_src):
                    workdir = out_p.parent / "raw" / "dense2x2_ion" / pid / src
                    with IonNode(nm[src], pdir / "contact_plan.ionrc", workdir) as ion:
                        time.sleep(args.settle)
                        for q in by_src[src]:
                            dst, t0s = q["dst"], q["t0"]
                            oracle = fetch_routes(nm[dst], t0s, ion, workdir)
                            chosen = _ion_chosen(oracle["routes"])
                            key = (src, dst, t0s)
                            base = lean_by_key.get(key, {"src": src, "dst": dst, "t0": t0s})
                            row = dict(base)  # preserve lean etc
                            if chosen is None:
                                row["ion"] = None
                            else:
                                live_hops = [[int(f), int(t)] for f, t in chosen["hops"]]
                                row["ion"] = {"arrival": chosen["arrival_rel"], "hops": live_hops}
                            ion_filled.append(row)
                # write updated plan row
                out_rec = {"plan_id": pid, "results": ion_filled}
                sink.write(json.dumps(out_rec) + "\n")
                sink.flush()
                wall = round(time.time() - t0, 1)
                n_ion = sum(1 for r in ion_filled if r.get("ion") is not None)
                print(f"[{i+1}/{len(plans_to_do)}] {pid} ion_filled={n_ion}/{len(ion_filled)} {wall}s", flush=True)
            except Exception as e:
                rec = {"plan_id": pid, "error": repr(e), "wall_s": round(time.time() - t0, 1)}
                sink.write(json.dumps(rec) + "\n")
                sink.flush()
                print(f"[{i+1}/{len(plans_to_do)}] {pid} ERROR {e}", flush=True)


if __name__ == "__main__":
    main()
