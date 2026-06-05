#!/usr/bin/env python3
"""Field run of the 4-key binary against the registered le4 predictions.

Runs the freshly built sabrsearch (full le4 pickMin, 3e4d2a0+) over the
same dispatches as the recording run, one process per plan, resumable.
Then scores: (a) the le4 mirror's frozen route predictions against the
binary's routes (P-V1); (b) the binary's routes against the per-dispatch
spec optima from grades.jsonl, reporting the key-3/key-4 populations the
version change leaves standing (P-V2, P-V3). The binary is the
authority; the mirror is the prediction under test.

Usage:
  le4field.py run --results out_diff_v3/diff_results.jsonl \
      --corpus <corpus root> --out out_diff_v3/le4_results.jsonl
  le4field.py score --le4 out_diff_v3/le4_results.jsonl \
      --predictions out_diff_v3/predictions_le4.jsonl \
      --grades out_diff_v3/grades.jsonl \
      --corpus <corpus root> --out out_diff_v3/le4_field_report.json
"""

import argparse
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from os import cpu_count
from pathlib import Path

BIN = Path(__file__).resolve().parents[2] / ".lake" / "build" / "bin" \
    / "sabrsearch"


def run_plan(pdir, queries):
    """queries: [(src_name, dst_name, t0)]; returns per-query results."""
    node_map = json.load(open(pdir / "plan_manifest.json"))["node_map"]
    qtext = "".join(f"{node_map[s]} {node_map[d]} {t}\n"
                    for s, d, t in queries)
    with tempfile.NamedTemporaryFile("w", suffix=".txt") as qf:
        qf.write(qtext)
        qf.flush()
        out = subprocess.run([str(BIN), str(pdir / "contact_plan.ionrc"),
                              qf.name], capture_output=True, text=True,
                             timeout=600)
    if out.returncode != 0:
        raise RuntimeError(f"sabrsearch rc={out.returncode}:"
                           f" {out.stderr[:300]}")
    byq = {}
    for line in out.stdout.splitlines():
        parts = line.split(" ")
        if len(parts) < 5 or parts[0] != "RESULT":
            continue
        num, den = parts[3].split("/")
        t0 = int(num) // int(den)
        if parts[4] == "NONE":
            byq[(parts[1], parts[2], t0)] = None
            continue
        anum, aden = parts[5].split("/")
        hops = []
        if len(parts) > 7 and parts[7]:
            for hop in parts[7].split(";"):
                f, t, ts = hop.split(":")
                hops.append((int(f), int(t), int(ts)))
        byq[(parts[1], parts[2], t0)] = {"arrival": int(anum) // int(aden),
                                         "hops": hops}
    results = []
    for s, d, t in queries:
        results.append({"src": s, "dst": d, "t0": t,
                        "le4": byq.get((str(node_map[s]),
                                        str(node_map[d]), t))})
    return results


def cmd_run(args):
    corpus = Path(args.corpus)
    outp = Path(args.out)
    done = set()
    if outp.exists():
        for line in open(outp):
            done.add(json.loads(line)["plan_id"])
    plans = []
    for line in open(args.results):
        rec = json.loads(line)
        if rec["plan_id"] in done:
            continue
        queries = [(q["src"], q["dst"], q["t0"]) for q in rec["results"]]
        plans.append((rec["plan_id"], queries))
    print(f"{len(done)} plans done, {len(plans)} to go")
    with open(outp, "a") as sink, \
            ProcessPoolExecutor(max_workers=cpu_count()) as pool:
        futs = {pool.submit(run_plan, corpus / pid, qs): pid
                for pid, qs in plans}
        n = 0
        for fut in as_completed(futs):
            pid = futs[fut]
            try:
                sink.write(json.dumps({"plan_id": pid,
                                       "results": fut.result()}) + "\n")
                sink.flush()
            except Exception as e:
                sink.write(json.dumps({"plan_id": pid, "error": repr(e)})
                           + "\n")
                sink.flush()
            n += 1
            if n % 100 == 0:
                print(f"{n}/{len(plans)}")


def cmd_score(args):
    preds = {}
    for line in open(args.predictions):
        rec = json.loads(line)
        if "error" in rec:
            continue
        for q in rec["queries"]:
            preds[(rec["plan_id"], q["src"], q["dst"], q["t0"])] = \
                q["lean_pred"]

    sopts = {}
    for line in open(args.grades):
        g = json.loads(line)
        sopts[(g["plan"], g["src"], g["dst"], g["t0"])] = \
            (tuple(g["sopt"]), g["lean"]["grade"])

    corpus = Path(args.corpus)
    ctabs = {}

    def ctab_for(pid):
        if pid not in ctabs:
            tab = {}
            for line in (corpus / pid / "contact_plan.ionrc") \
                    .read_text().splitlines():
                p = line.split()
                if line.startswith("a contact"):
                    tab[(int(p[4]), int(p[5]), int(p[2].lstrip("+")))] = \
                        int(p[3].lstrip("+"))
            ctabs[pid] = tab
        return ctabs[pid]

    tall = {"dispatches": 0, "mirror_route_exact": 0, "mirror_route_diff": 0,
            "grades": {}, "k3_was_dev_now_ok": 0, "k3_still_dev": 0,
            "k3_new_dev": 0, "k4_still_dev": 0, "k4_new_dev": 0}
    k4_cases, mirror_misses = [], []
    for line in open(args.le4):
        rec = json.loads(line)
        if "error" in rec:
            print(f"RUN ERROR {rec['plan_id']}", file=sys.stderr)
            continue
        pid = rec["plan_id"]
        for q in rec["results"]:
            r = q["le4"]
            key = (pid, q["src"], q["dst"], q["t0"])
            if key not in sopts:
                continue		# none_none dispatch
            if r is None:
                print(f"UNEXPECTED NONE {key}", file=sys.stderr)
                continue
            tall["dispatches"] += 1
            p = preds.get(key)
            if p and [tuple(h) for h in p["hops"]] == \
                    [tuple(h) for h in r["hops"]]:
                tall["mirror_route_exact"] += 1
            else:
                tall["mirror_route_diff"] += 1
                if len(mirror_misses) < 50:
                    mirror_misses.append({
                        "key": list(key),
                        "binary": r["hops"],
                        "mirror": p["hops"] if p else None})
            tab = ctab_for(pid)
            term = min(tab[(f, t, ts)] for f, t, ts in r["hops"])
            tup = (len(r["hops"]), term, r["hops"][0][1])
            sopt, old = sopts[key]
            if tup[0] > sopt[0]:
                g = "key2_excess"
            elif tup[1] != sopt[1]:
                g = "key3_dev"
            elif tup[2] != sopt[2]:
                g = "key4_dev"
            else:
                g = "conformant"
            tall["grades"][g] = tall["grades"].get(g, 0) + 1
            if old == "key3_dev":
                if g == "key3_dev":
                    tall["k3_still_dev"] += 1
                else:
                    tall["k3_was_dev_now_ok"] += 1
            elif g == "key3_dev":
                tall["k3_new_dev"] += 1
            if g == "key4_dev":
                if old == "key4_dev":
                    tall["k4_still_dev"] += 1
                else:
                    tall["k4_new_dev"] += 1
                if len(k4_cases) < 60:
                    k4_cases.append({"key": list(key), "entry": tup[2],
                                     "spec_entry": sopt[2]})

    report = {"tallies": tall, "k4_cases": k4_cases,
              "mirror_misses": mirror_misses}
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(json.dumps(tall, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--results", default="out_diff_v3/diff_results.jsonl")
    r.add_argument("--corpus", required=True)
    r.add_argument("--out", default="out_diff_v3/le4_results.jsonl")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("score")
    s.add_argument("--le4", default="out_diff_v3/le4_results.jsonl")
    s.add_argument("--predictions", default="out_diff_v3/predictions_le4.jsonl")
    s.add_argument("--grades", default="out_diff_v3/grades.jsonl")
    s.add_argument("--corpus", required=True)
    s.add_argument("--out", default="out_diff_v3/le4_field_report.json")
    s.set_defaults(fn=cmd_score)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
