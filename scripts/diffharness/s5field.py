#!/usr/bin/env python3
"""S5 distribution swap, stage A: the lean+oracle leg over the DSN-real
corpus (dsn-scraper build_contact_corpus.py output).

Every rate the audit reports has so far been conditioned on the cislunar
generator's plan distribution. This runner re-derives the
distribution-sensitive quantities on plans built from archived DSN Now
tracking data - real pass windows, real station multiplicity, measured
light times - with the same binary and the same oracles:

  - two-sided key-1 check per dispatch (found: oracle arrival must equal
    the binary's; none: the oracle must agree no route exists) - T2b and
    completeness tested outside the generator's world;
  - spec grading of the returned route (filter-c basis, strong reading);
  - the discrimination ladder (which key pins route identity) and the
    latent full-tuple-indifference count, the corpus_v3 baselines for
    which are 24.6 / 65.0 / 10.3 / 0.12 percent and 5 cases.

The ION leg is deliberately absent: 556 range entries here are owlt >=
1491 s where ION's margin binds and is not yet modeled (the instrument
refuses such plans by design). This runner also emits a
diff_results-shaped file (ion null) so predict.py can freeze
margin-aware ION-mirror predictions for that future leg, and scores the
lean le4 mirror against the binary on this distribution.

Usage:
  s5field.py run --corpus <dsn_real_v1 root> --out out_s5/s5_results.jsonl
  s5field.py analyze --corpus <root> --results out_s5/s5_results.jsonl \
      --out out_s5/s5_report.json [--predictions out_s5/predictions.jsonl]
"""

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from os import cpu_count
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from instrument import parse_ionrc, key1_oracle, grading_oracle, \
    spec_optimum, grade  # noqa: E402

BIN = Path(__file__).resolve().parents[2] / ".lake" / "build" / "bin" \
    / "sabrsearch"


def load_queries(pdir):
    """queries.jsonl ({src,dst,t0} lines), or the corpus_v3-family
    pairs.jsonl (query-flagged pairs with a single t0_s each)."""
    qf = pdir / "queries.jsonl"
    if qf.exists():
        return [json.loads(line) for line in open(qf)]
    out = []
    for line in open(pdir / "pairs.jsonl"):
        p = json.loads(line)
        if p.get("query"):
            out.append({"src": p["src"], "dst": p["dst"], "t0": p["t0_s"]})
    return out


def run_plan(pdir):
    node_map = json.load(open(pdir / "plan_manifest.json"))["node_map"]
    queries = load_queries(pdir)
    qtext = "".join(f"{node_map[q['src']]} {node_map[q['dst']]} {q['t0']}\n"
                    for q in queries)
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
        key = (parts[1], parts[2], int(num) // int(den))
        if parts[4] == "NONE":
            byq[key] = None
            continue
        anum, aden = parts[5].split("/")
        hops = []
        if len(parts) > 7 and parts[7]:
            for hop in parts[7].split(";"):
                f, t, ts = hop.split(":")
                hops.append((int(f), int(t), int(ts)))
        byq[key] = {"arrival": int(anum) // int(aden), "hops": hops}
    results = []
    for q in queries:
        lean = byq.get((str(node_map[q["src"]]), str(node_map[q["dst"]]),
                        q["t0"]))
        results.append({"src": q["src"], "dst": q["dst"], "t0": q["t0"],
                        "lean": lean, "ion": None})
    return results


def cmd_run(args):
    corpus = Path(args.corpus)
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if outp.exists():
        for line in open(outp):
            done.add(json.loads(line)["plan_id"])
    plans = [p for p in sorted(corpus.glob(args.glob))
             if p.is_dir() and (p / "contact_plan.ionrc").exists()
             and p.name not in done]
    print(f"{len(done)} plans done, {len(plans)} to go")
    with open(outp, "a") as sink, \
            ProcessPoolExecutor(max_workers=cpu_count()) as pool:
        futs = {pool.submit(run_plan, p): p.name for p in plans}
        for fut in as_completed(futs):
            pid = futs[fut]
            try:
                sink.write(json.dumps({"plan_id": pid,
                                       "results": fut.result()}) + "\n")
            except Exception as e:
                sink.write(json.dumps({"plan_id": pid,
                                       "error": repr(e)}) + "\n")
            sink.flush()


def cmd_analyze(args):
    corpus = Path(args.corpus)
    preds = {}
    if args.predictions:
        for line in open(args.predictions):
            rec = json.loads(line)
            if "error" in rec:
                continue
            for q in rec["queries"]:
                preds[(rec["plan_id"], q["src"], q["dst"], q["t0"])] = q

    found = none_agreed = 0
    k1_disagreements = []
    grades = Counter()
    ladder = Counter()
    latent_cases = []
    mirror = Counter()
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
                if c[4] < 0:
                    print(f"NEGATIVE OWLT {pid}", file=sys.stderr)
                    sys.exit(1)
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
                    k1_disagreements.append(
                        {"key": [pid, q["src"], q["dst"], t0],
                         "lean": None, "oracle": k1})
                continue
            found += 1
            a = lean["arrival"]
            if k1 != a:
                k1_disagreements.append(
                    {"key": [pid, q["src"], q["dst"], t0],
                     "lean": a, "oracle": k1})
                continue
            depth = len(lean["hops"])
            tuples = grading_oracle(adj, src, dst, t0, a, depth)
            if not tuples:
                print(f"GRADING ORACLE EMPTY {pid}", file=sys.stderr)
                sys.exit(1)
            sopt = spec_optimum(tuples)
            term = None
            for f, t, ts in lean["hops"]:
                for c in adj[f]:
                    if c[1] == t and c[2] == ts:
                        term = c[3] if term is None or c[3] < term else term
                        break
            ltuple = (len(lean["hops"]), term, lean["hops"][0][1])
            grades["lean_" + grade(ltuple, sopt)] += 1

            hmin = min(t[0] for t in tuples)
            at_h = [t for t in tuples if t[0] == hmin]
            if len(at_h) == 1:
                ladder["keys12"] += 1
            else:
                tmax = max(t[1] for t in at_h)
                at_ht = [t for t in at_h if t[1] == tmax]
                if len(at_ht) == 1:
                    ladder["key3"] += 1
                else:
                    emin = min(t[2] for t in at_ht)
                    at_full = [t for t in at_ht if t[2] == emin]
                    if len(at_full) == 1:
                        ladder["key4"] += 1
                    else:
                        ladder["latent"] += 1
                        if len(latent_cases) < 40:
                            latent_cases.append(
                                {"key": [pid, q["src"], q["dst"], t0],
                                 "sopt": list(sopt),
                                 "multiplicity": len(at_full)})

            p = preds.get((pid, q["src"], q["dst"], t0))
            if p and p.get("lean_pred"):
                same = [tuple(h) for h in p["lean_pred"]["hops"]] == \
                    [tuple(h) for h in lean["hops"]]
                mirror["lean_mirror_exact" if same
                       else "lean_mirror_diff"] += 1

    n = found or 1
    report = {
        "found_dispatches": found,
        "none_both_sides": none_agreed,
        "key1_disagreements": len(k1_disagreements),
        "key1_cases": k1_disagreements[:20],
        "lean_grades": dict(sorted(grades.items())),
        "ladder": {k: [v, round(100 * v / n, 1)]
                   for k, v in sorted(ladder.items())},
        "ladder_baseline_corpus_v3": {"keys12": 24.6, "key3": 65.0,
                                      "key4": 10.3, "latent": 0.12},
        "latent_cases": latent_cases,
        "lean_mirror_check": dict(mirror),
    }
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("latent_cases", "key1_cases")},
                     indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--corpus", required=True)
    r.add_argument("--glob", default="dsn_real_v1_plan_*")
    r.add_argument("--out", default="out_s5/s5_results.jsonl")
    r.set_defaults(fn=cmd_run)
    a = sub.add_parser("analyze")
    a.add_argument("--corpus", required=True)
    a.add_argument("--results", default="out_s5/s5_results.jsonl")
    a.add_argument("--out", default="out_s5/s5_report.json")
    a.add_argument("--predictions", default=None)
    a.set_defaults(fn=cmd_analyze)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
