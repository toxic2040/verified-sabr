#!/usr/bin/env python3
"""Depth-N adjudication of diverged plans from an evl.py run.

Mirrors the endpoint-run protocol: the full sweep runs at depth 3 with
truncations counted; every plan whose two-ledger replay diverged is
re-replayed at a deeper cap. A divergence that was a cap artifact
(found/none whose none side truncated, or an entry pick a deeper route
dominates) dissolves under the deeper cap; one that persists at a depth
where the pbat-gap check holds is cap-proof, by the same monotonicity
arguments the endpoint run used: found verdicts are monotone in depth,
and a selection at the volume-unconstrained optimal PBAT cannot be
beaten at key 1 by any deeper route while deeper routes lose key 2 at
equal PBAT.

Usage:
  evl_adjudicate.py --results <results.jsonl> --corpus <root>
      [--depth 4] [--contention 8.0] [--bundles 24]
      [--traffic relay] --out <adjudicated.jsonl>
"""

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from os import cpu_count
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evl import replay_plan  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--contention", type=float, default=8.0)
    ap.add_argument("--bundles", type=int, default=24)
    ap.add_argument("--traffic", default="relay")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    diverged = []
    for line in open(args.results):
        rec = json.loads(line)
        if rec.get("first_divergence"):
            diverged.append(rec["plan_id"])
    print(f"{len(diverged)} diverged plans to adjudicate at depth "
          f"{args.depth}")

    outp = Path(args.out)
    done = set()
    if outp.exists():
        for line in open(outp):
            done.add(json.loads(line)["plan_id"])
    todo = [p for p in diverged if p not in done]

    corpus = Path(args.corpus)
    persist = dissolved = 0
    with open(outp, "a") as sink, \
            ProcessPoolExecutor(max_workers=cpu_count()) as pool:
        futs = {pool.submit(replay_plan, corpus / pid, args.bundles,
                            args.contention, args.depth,
                            args.traffic): pid
                for pid in todo}
        for fut in as_completed(futs):
            pid = futs[fut]
            try:
                rec = fut.result()
            except Exception as e:
                rec = {"plan_id": pid, "error": repr(e)}
            sink.write(json.dumps(rec) + "\n")
            sink.flush()
    for line in open(outp):
        rec = json.loads(line)
        if rec.get("first_divergence"):
            persist += 1
        elif "error" not in rec:
            dissolved += 1
    print(f"adjudicated: {persist} persist, {dissolved} dissolved")


if __name__ == "__main__":
    main()
