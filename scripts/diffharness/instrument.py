#!/usr/bin/env python3
"""S1 conformance instrumentation over recorded differential results.

Epistemic roles, stated so the report cannot be over-read:

  - lean and ION are AUTHORITIES: records of what each implementation did.
  - This module supplies the TRUTH CLAIMS, by two oracles whose assumptions
    are a strict relaxation of lean's frame, so lean's theorems sit inside
    their search space as falsifiable hypotheses rather than constraints
    (the frame-relaxation principle):

      1. key-1 oracle: time-dependent label-correcting earliest arrival
         over (node, time) states. No route objects, no visited list, no
         tie keys, reuse irrelevant by construction - a different
         algorithm family from the candidate search. Complete over the
         UNBOUNDED route class: monotone relaxation on a finite value
         lattice terminates with no depth cap. Soundness needs only
         owlt >= 0, checked directly on the parsed data. Two-sided: it
         can refute the recorded optimal arrival and, when it agrees,
         confirms it.
      2. grading oracle: exhaustive chain enumeration WITH contact reuse
         up to depth max(returned hop counts). Complete for every
         question it grades, because hop-count questions self-bound:
         spec-minimal hops, spec key-3 termination, spec key-4 entry all
         live at depths <= the returned routes'.

  Triangulation scope: ION's 4100/4100 arrival agreement externally
  anchors the arrival FUNCTION (max-with-start plus range); it says
  nothing about the arrival DOMAIN (which routes exist). The oracles
  above are what test the domain.

Spec basis for grading (CCSDS 734.3-B-1, 3.2.8.1.4 a, read verbatim):
keys are total through key 4 (arrival up, hops up, termination down,
entry node NUMBER up; "arbitrarily" in 4) names the rule, not
implementation freedom). Below key 4 the standard is silent, and
3.2.8.1.4 b) consumes the best route only through its entry node, so
sub-key-4 divergence is forwarding-equivalent in the no-volume regime.
Quantifier caveat carried in the report: the spec ranges over "the
candidate routes in the list" and never pins the list's contents; this
module grades the strong reading (all valid routes) and reports the weak
reading as the conformance escape hatch.
"""

import argparse
import json
import sys
import heapq
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


def key1_oracle(adj, src, dst, t0):
    """Earliest arrival at dst over ALL chains (reuse included), by
    time-dependent Dijkstra on (node, earliest-known-arrival) labels.
    Sound for owlt >= 0 (checked by caller); complete with no depth cap."""
    best = {src: t0}
    heap = [(t0, src)]
    while heap:
        t, node = heapq.heappop(heap)
        if t > best.get(node, None if node not in best else best[node]):
            continue
        if node == dst and node != src:
            pass  # settled; continue draining for clarity (heap is tiny)
        for c in adj[node]:
            tx = t if t > c[2] else c[2]
            if tx > c[3]:
                continue
            t2 = tx + c[4]
            if c[1] not in best or t2 < best[c[1]]:
                best[c[1]] = t2
                heapq.heappush(heap, (t2, c[1]))
    return best.get(dst)


def grading_oracle(adj, src, dst, t0, a, depth):
    """All chains (reuse allowed) up to `depth`, pruned at arrival > a.
    Returns (h, minTermEnd, entryNode) tuples of routes arriving exactly
    at a. Complete for hop/term/entry grading at depths <= `depth`."""
    tuples = []

    def dfs(node, t, d, term, entry):
        if d >= depth:
            return
        for c in adj[node]:
            tx = t if t > c[2] else c[2]
            if tx > c[3]:
                continue
            t2 = tx + c[4]
            if t2 > a:
                continue
            nterm = c[3] if term is None or c[3] < term else term
            nentry = entry if entry is not None else c[1]
            if c[1] == dst and t2 == a:
                tuples.append((d + 1, nterm, nentry))
            dfs(c[1], t2, d + 1, nterm, nentry)

    dfs(src, t0, 0, None, None)
    return tuples


def spec_optimum(tuples):
    """3.2.8.1.4 a) keys 2-4 at fixed optimal arrival: hops up, then
    termination down, then entry node number up."""
    hmin = min(t[0] for t in tuples)
    at_h = [t for t in tuples if t[0] == hmin]
    tmax = max(t[1] for t in at_h)
    at_ht = [t for t in at_h if t[1] == tmax]
    emin = min(t[2] for t in at_ht)
    return (hmin, tmax, emin)


def grade(tup, sopt):
    if tup[0] > sopt[0]:
        return "key2_excess"
    if tup[1] != sopt[1]:
        return "key3_dev"
    if tup[2] != sopt[2]:
        return "key4_dev"
    return "conformant"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="out_diff_v3/diff_results.jsonl")
    ap.add_argument("--corpus", required=True,
                    help="corpus root holding <plan_id>/contact_plan.ionrc")
    ap.add_argument("--out", default="out_diff_v3/instrumentation_report.json")
    args = ap.parse_args()

    corpus = Path(args.corpus)
    owlt_hist = Counter()
    plan_cache, nm_cache, adj_cache, ctab_cache = {}, {}, {}, {}

    found = none_none = ambiguous = 0
    grades = Counter()
    eqhop_buckets = Counter()
    tie_count = 0
    lean_k4 = []
    lean_offenders_k2 = []

    for line in open(args.results):
        rec = json.loads(line)
        pid = rec["plan_id"]
        if pid not in plan_cache:
            pdir = corpus / pid
            cs = parse_ionrc(pdir / "contact_plan.ionrc")
            for c in cs:
                if c[4] < 0:
                    print(f"NEGATIVE OWLT in {pid}: key-1 oracle unsound",
                          file=sys.stderr)
                    sys.exit(1)
                owlt_hist[c[4]] += 1
            plan_cache[pid] = cs
            nm_cache[pid] = json.load(
                open(pdir / "plan_manifest.json"))["node_map"]
            adj = defaultdict(list)
            ctab = defaultdict(list)
            for c in cs:
                adj[c[0]].append(c)
                ctab[(c[0], c[1])].append(c)
            adj_cache[pid], ctab_cache[pid] = adj, ctab
        adj, nm, ctab = adj_cache[pid], nm_cache[pid], ctab_cache[pid]

        for q in rec["results"]:
            lean, ion = q.get("lean"), q.get("ion")
            if not lean or not ion or lean.get("hops") is None \
                    or ion.get("hops") is None:
                none_none += 1
                continue
            found += 1
            a = lean["arrival"]
            t0 = q["t0"]
            lh, ih = lean["hops"], ion["hops"]
            src, dst = nm[q["src"]], nm[q["dst"]]

            # key-1 truth: two-sided check of the recorded optimum
            k1 = key1_oracle(adj, src, dst, t0)
            if k1 != a:
                print(f"KEY-1 ORACLE DISAGREES {pid} {q['src']}->{q['dst']} "
                      f"t0={t0}: oracle {k1} vs recorded {a} - punt-to-truth "
                      f"event, investigate before trusting either",
                      file=sys.stderr)
                sys.exit(1)

            tuples = grading_oracle(adj, src, dst, t0, a, max(len(lh), len(ih)))
            if not tuples:
                print(f"GRADING ORACLE EMPTY {pid}", file=sys.stderr)
                sys.exit(1)
            sopt = spec_optimum(tuples)

            # lean tuple: (from, to, tStart) triples identify contacts
            lterm = min(next(c for c in ctab[(f, t)] if c[2] == ts)[3]
                        for f, t, ts in lh)
            ltuple = (len(lh), lterm, lh[0][1])
            lg = grade(ltuple, sopt)
            grades["lean_" + lg] += 1
            if lg == "key2_excess":
                lean_offenders_k2.append({"plan": pid, "src": q["src"],
                                          "dst": q["dst"], "t0": t0})
            if ltuple[0] == sopt[0] and ltuple[1] == sopt[1] \
                    and ltuple[2] != sopt[2]:
                lean_k4.append({"plan": pid, "src": q["src"], "dst": q["dst"],
                                "lean_entry": ltuple[2],
                                "spec_entry": sopt[2]})

            # ion tuple: (from, to) pairs thread over candidate windows;
            # ambiguity flagged, never guessed
            threads = [(t0, None)]
            for f, t in ih:
                nxt = []
                for tcur, term in threads:
                    for c in ctab[(f, t)]:
                        tx = tcur if tcur > c[2] else c[2]
                        if tx > c[3]:
                            continue
                        nterm = c[3] if term is None or c[3] < term else term
                        nxt.append((tx + c[4], nterm))
                threads = nxt
            terms = sorted(set(term for tarr, term in threads if tarr == a))
            if not terms:
                print(f"ION THREAD INCONSISTENT {pid}", file=sys.stderr)
                sys.exit(1)
            if len(terms) > 1:
                ambiguous += 1
                grades["ion_ambiguous"] += 1
            else:
                ituple = (len(ih), terms[0], ih[0][1])
                ig = grade(ituple, sopt)
                grades["ion_" + ig] += 1
                if not q["agree_hops"] and len(lh) == len(ih):
                    eqhop_buckets[("lean_dev" if ltuple != sopt else "lean_ok")
                                  + "/" +
                                  ("ion_dev" if ituple != sopt else "ion_ok")
                                  ] += 1

            if sum(n for n, _, _ in [(t[0], 0, 0) for t in tuples]
                   if n <= len(lh)) >= 2:
                tie_count += 1

    report = {
        "epistemics": {
            "lean": "authority (what the verified implementation did)",
            "ion": "authority (what deployed ION did)",
            "key1_truth": "state-space oracle, two-sided, unbounded class",
            "grading_truth": "exhaustive reuse-allowed enumeration,"
                             " self-bounded by the graded question",
            "triangulation": "ION anchors the arrival function, not the"
                             " route domain; the oracles test the domain",
            "spec_quantifier": "strong reading graded (all valid routes);"
                               " the text's list-relative reading is the"
                               " conformance escape hatch",
        },
        "found_dispatches": found,
        "none_none": none_none,
        "owlt_range_entries": dict(sorted(owlt_hist.items())),
        "tie_among_minhop_optima": tie_count,
        "grades": dict(sorted(grades.items())),
        "ion_thread_ambiguous": ambiguous,
        "equal_hop_divergence_buckets": dict(sorted(eqhop_buckets.items())),
        "lean_key4_delta8_cases": lean_k4,
        "lean_key2_offenders": lean_offenders_k2,
    }
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("lean_key4_delta8_cases",
                                   "lean_key2_offenders")}, indent=1))
    print(f"lean_key4_delta8_cases: {len(lean_k4)}")


if __name__ == "__main__":
    main()
