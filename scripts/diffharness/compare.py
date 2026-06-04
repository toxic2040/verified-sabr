#!/usr/bin/env python3
"""Differential comparison: verified sabrsearch vs ION CGR on generated plans.

Per plan directory (contact_plan.ionrc + contacts.json + plan_manifest.json):
boot a throwaway ION node as the query source, simulate dispatches with
cgrfetch, run the compiled sabrsearch binary on the same ionrc at the same
plan-relative times, and append one JSONL row per plan. Resume by plan_id;
per-plan failures are recorded, never fatal. Serial by construction: ION is a
host singleton (see ion_node.py).

Agreement criterion (algorithm.md §9.3): found/none verdict and exact earliest
arrival, after the measured constant OWLT-margin transform; hop sequences are
reported, not gated.

Usage:
  compare.py --plans <corpus root or single plan dir> --out <dir>
             [--limit N] [--owlt-margin 0] [--registration]
  compare.py --fixture <toy.ionrc> --src 1 --dst 5 --t0 60 --out <dir>
"""

import argparse
import json
import math
import re
import sys
import time
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cgr_oracle import fetch_routes  # noqa: E402
from ion_node import IonNode  # noqa: E402

BIN = Path(__file__).resolve().parents[2] / ".lake" / "build" / "bin" / "sabrsearch"

QUERY_DESTS = ["CANBERRA", "GOLDSTONE", "MADRID", "GATEWAY"]
QUERY_SRC = "SHACKLETON"
REVERSE_EVERY = 10  # every 10th plan adds CANBERRA -> SHACKLETON
BOUNDARY_MARGIN_S = 30
MIN_T0_S = 120

LINE_RE = re.compile(
    r"^a (contact|range) \+(\d+) \+(\d+) (\d+) (\d+) (\d+)$")


def parse_ionrc(path):
    rows = []
    for line in Path(path).read_text().splitlines():
        m = LINE_RE.match(line.strip())
        if m:
            kind, s, e, a, b, v = m.groups()
            rows.append((kind, int(s), int(e), int(a), int(b), int(v)))
    return rows


def guarded_t0(rows, start_from):
    """First t >= start_from at least BOUNDARY_MARGIN_S from every boundary."""
    bounds = sorted({r[1] for r in rows} | {r[2] for r in rows})
    t = max(MIN_T0_S, start_from)
    while any(abs(t - b) < BOUNDARY_MARGIN_S for b in bounds):
        t += 1
    return t


def lean_queries(plan_path, queries, workdir):
    """Run sabrsearch once for a batch of (src, dst, t0) integer queries.

    The query file lands in the harness workdir, never next to the plan —
    plan directories belong to the generator and stay pristine.
    """
    qtext = "".join(f"{s} {d} {t}\n" for s, d, t in queries)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    qfile = workdir / "lean_queries.txt"
    qfile.write_text(qtext)
    import subprocess
    out = subprocess.run([str(BIN), str(plan_path), str(qfile)],
                         capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        raise RuntimeError(f"sabrsearch rc={out.returncode}: {out.stderr[:300]}")
    results = {}
    for line in out.stdout.splitlines():
        parts = line.split(" ")
        if len(parts) < 5 or parts[0] != "RESULT":
            continue
        src, dst, t0 = parts[1], parts[2], Fraction(parts[3])
        if parts[4] == "NONE":
            results[(src, dst, t0)] = None
        else:
            arrival = Fraction(parts[5])
            hops = []
            if len(parts) > 7 and parts[7]:
                for hop in parts[7].split(";"):
                    f, t, ts = hop.split(":")
                    hops.append((int(f), int(t), int(ts)))
            results[(src, dst, t0)] = {"arrival": arrival, "hops": hops}
    return results


def ion_chosen(oracle_result):
    """ION's pick: the SELECTED route, else best CONSIDERED, else none.

    Routes with flag DEFAULT/IDENTIFIED carry an ignoreReason (filtered by
    §3.2.6.9 machinery) and are not forwarding candidates.
    """
    routes = oracle_result["routes"]
    selected = [r for r in routes if r["flag"] == 3]
    if selected:
        return min(selected, key=lambda r: r["arrival_rel"])
    considered = [r for r in routes if r["flag"] == 2]
    if considered:
        return min(considered, key=lambda r: r["arrival_rel"])
    return None


def compare_query(lean_res, ion_res, t0, owlt_margin):
    row = {"t0": int(t0), "lean": None, "ion": None,
           "agree_verdict": False, "agree_arrival": None, "agree_hops": None}
    if lean_res is not None:
        assert lean_res["arrival"].denominator == 1, \
            f"non-integer lean arrival {lean_res['arrival']}"
        row["lean"] = {"arrival": int(lean_res["arrival"]),
                       "hops": lean_res["hops"]}
    if ion_res is not None:
        row["ion"] = {"arrival": ion_res["arrival_rel"],
                      "hops": ion_res["hops"]}
    row["agree_verdict"] = (lean_res is None) == (ion_res is None)
    if lean_res is not None and ion_res is not None:
        # exact integer comparison: both timelines share the same integer
        # anchor and the Lean side was queried at ION's measured dispatch
        expected_ion = (int(lean_res["arrival"])
                        + round(owlt_margin * len(lean_res["hops"])))
        row["agree_arrival"] = ion_res["arrival_rel"] == expected_ion
        lean_hops = [(f, t) for f, t, _ in lean_res["hops"]]
        ion_hops = [(int(f), int(t)) for f, t in ion_res["hops"]]
        row["agree_hops"] = lean_hops == ion_hops
    return row


def node_map_of(plan_dir):
    manifest = json.loads((plan_dir / "plan_manifest.json").read_text())
    if "node_map" in manifest:
        return {k: int(v) for k, v in manifest["node_map"].items()}
    contacts = json.loads((plan_dir / "contacts.json").read_text())
    names = sorted({c["from_node"] for c in contacts}
                   | {c["to_node"] for c in contacts})
    return {n: i + 1 for i, n in enumerate(names)}


def run_plan(plan_dir, idx, out_dir, owlt_margin, registration):
    plan_path = plan_dir / "contact_plan.ionrc"
    rows = parse_ionrc(plan_path)
    nmap = node_map_of(plan_dir)
    t_a = guarded_t0(rows, MIN_T0_S)
    queries = [(QUERY_SRC, d) for d in QUERY_DESTS]
    if idx % REVERSE_EVERY == 0:
        t_b = guarded_t0(rows, 43200)
        reverse = [("CANBERRA", QUERY_SRC, t_b)]
    else:
        reverse = []

    results = []
    groups = [(QUERY_SRC, [(s, d, t_a) for s, d in queries])]
    if reverse:
        groups.append(("CANBERRA", reverse))

    for boot_name, qs in groups:
        boot_num = nmap[boot_name]
        raw_dir = out_dir / "raw" / plan_dir.name
        # ION first: collect each query's MEASURED dispatch instant, then run
        # the Lean side at exactly those times (identical dispatch by
        # construction; the boundary guard on t0 is belt and braces)
        oracle_rows = []
        with IonNode(boot_num, plan_path, raw_dir,
                     registration=registration) as ion:
            time.sleep(1.0)  # let bp daemons settle before simulating
            for s, d, t0 in qs:
                oracle = fetch_routes(nmap[d], t0, ion, raw_dir)
                oracle_rows.append((s, d, t0, oracle))
        lean_out = lean_queries(
            plan_path,
            [(nmap[s], nmap[d], o["dispatch_rel"])
             for s, d, _, o in oracle_rows],
            raw_dir)
        for s, d, t0_req, oracle in oracle_rows:
            t_meas = oracle["dispatch_rel"]
            key = (str(nmap[s]), str(nmap[d]), Fraction(t_meas))
            row = compare_query(lean_out.get(key), ion_chosen(oracle),
                                t_meas, owlt_margin)
            row.update({"src": s, "dst": d, "t0_requested": int(t0_req),
                        "raw": oracle["raw_path"]})
            if abs(t_meas - t0_req) > 5:
                row["dispatch_drift_s"] = t_meas - t0_req
            results.append(row)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plans")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--owlt-margin", type=float, default=0.0)
    ap.add_argument("--registration", action="store_true")
    ap.add_argument("--fixture")
    ap.add_argument("--src"), ap.add_argument("--dst"), ap.add_argument("--t0")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl = out_dir / "diff_results.jsonl"

    if args.fixture:
        # single-query fixture mode: pins cgrfetch schema and the OWLT margin
        plan_path = Path(args.fixture)
        t0 = int(args.t0)
        with IonNode(int(args.src), plan_path, out_dir / "raw",
                     registration=args.registration) as ion:
            time.sleep(1.0)
            oracle = fetch_routes(int(args.dst), t0, ion, out_dir / "raw")
        t_meas = oracle["dispatch_rel"]
        lean_out = lean_queries(plan_path,
                                [(int(args.src), int(args.dst), t_meas)],
                                out_dir / "raw")
        key = (args.src, args.dst, Fraction(t_meas))
        row = compare_query(lean_out.get(key), ion_chosen(oracle), t_meas,
                            args.owlt_margin)
        row.update({"src": args.src, "dst": args.dst,
                    "t0_requested": t0,
                    "raw": oracle["raw_path"],
                    "dispatch_rel": t_meas})
        print(json.dumps(row, indent=2, default=str))
        return

    done = set()
    if jsonl.exists():
        for line in jsonl.read_text().splitlines():
            done.add(json.loads(line)["plan_id"])

    plan_dirs = sorted(p.parent for p in Path(args.plans).glob("*/contacts.json"))
    if not plan_dirs and (Path(args.plans) / "contacts.json").exists():
        plan_dirs = [Path(args.plans)]
    if args.limit:
        plan_dirs = plan_dirs[: args.limit]

    with jsonl.open("a") as fh:
        for idx, plan_dir in enumerate(plan_dirs):
            if plan_dir.name in done:
                continue
            try:
                results = run_plan(plan_dir, idx, out_dir,
                                   args.owlt_margin, args.registration)
                row = {"plan_id": plan_dir.name, "results": results}
            except Exception as e:  # never kill the batch on one plan
                row = {"plan_id": plan_dir.name, "error": repr(e)}
            fh.write(json.dumps(row, default=str) + "\n")
            fh.flush()
            print(f"[{idx + 1}/{len(plan_dirs)}] {plan_dir.name} "
                  f"{'ERR' if 'error' in row else 'ok'}", flush=True)


if __name__ == "__main__":
    main()
