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


def grading_oracle(adj, src, dst, t0, a, depth, filter_c=True):
    """All chains (reuse allowed) up to `depth`, pruned at arrival > a.
    Returns (h, minTermEnd, entryNode) tuples of routes arriving exactly
    at a. Complete for hop/term/entry grading at depths <= `depth`.

    filter_c applies 3.2.6.9 c): a route that includes any contact
    delivering back to the forwarding node X is not a candidate (loopback
    aside, which the corpus never exercises). The v2 audit omitted this
    filter; v3 grades on the filtered universe and reports the delta."""
    tuples = []

    def dfs(node, t, d, term, entry):
        if d >= depth:
            return
        for c in adj[node]:
            if filter_c and c[1] == src:
                continue
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
    ap.add_argument("--dump", default=None,
                    help="per-dispatch grade records, one JSON line each")
    ap.add_argument("--predictions", default=None,
                    help="predict.py output; cross-checks predicted routes"
                         " against recorded grades per dispatch")
    args = ap.parse_args()

    corpus = Path(args.corpus)
    owlt_hist = Counter()
    plan_cache, nm_cache, adj_cache, ctab_cache = {}, {}, {}, {}

    preds = {}
    if args.predictions:
        for line in open(args.predictions):
            rec = json.loads(line)
            if "error" in rec:
                continue
            for q in rec["queries"]:
                preds[(rec["plan_id"], q["src"], q["dst"], q["t0"])] = q

    dump = open(args.dump, "w") if args.dump else None

    found = none_none = multiterm = grade_ambiguous = 0
    grades = Counter()
    bound_extra = Counter()     # grade -> count of swing dispatches allowing it
    eqhop_buckets = Counter()
    eqhop_excluded = 0
    tie_count = 0
    filter_c_changed = 0
    lean_k4 = []
    lean_offenders_k2 = []
    pred_check = Counter()

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
                if c[4] >= 1491:
                    # ION adds (MAX_SPEED_MPS*owlt)//186282 s of margin,
                    # nonzero from owlt 1491 s (helio B3). The oracles do
                    # not model it yet; grading that regime margin-blind
                    # would silently compare different arrival functions.
                    print(f"OWLT {c[4]} >= 1491 in {pid}: ION margin"
                          " binds and is unmodeled - refusing to grade",
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

            depth = max(len(lh), len(ih))
            tuples = grading_oracle(adj, src, dst, t0, a, depth)
            if not tuples:
                print(f"GRADING ORACLE EMPTY {pid}", file=sys.stderr)
                sys.exit(1)
            sopt = spec_optimum(tuples)
            sopt_u = spec_optimum(grading_oracle(adj, src, dst, t0, a,
                                                 depth, filter_c=False))
            if sopt != sopt_u:
                filter_c_changed += 1

            # 3.2.6.9 c) at route level: neither implementation may
            # return a route containing a contact back to the forwarding
            # node (loopback aside, never exercised here). Counted, not
            # assumed - a future corpus could trip it silently.
            if any(t == src for _, t, _ in lh):
                grades["lean_filter_c_route"] += 1
            if any(t == src for _, t in ih):
                grades["ion_filter_c_route"] += 1

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

            # ion: (from, to) pairs thread over candidate windows. Hop
            # count and entry node are thread-invariant; only the
            # termination time can swing. A dispatch is ambiguous only
            # when the GRADE swings across thread resolutions - a
            # multi-term thread whose resolutions all grade alike is
            # determinate (v2 flagged these; the bounds make the
            # distinction exact).
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
                multiterm += 1
            possible = sorted(set(grade((len(ih), t, ih[0][1]), sopt)
                                  for t in terms))
            ig = None
            if len(possible) == 1:
                ig = possible[0]
                grades["ion_" + ig] += 1
                ituple = (len(ih), terms[0], ih[0][1])
                if not q["agree_hops"] and len(lh) == len(ih):
                    eqhop_buckets[("lean_dev" if ltuple != sopt else "lean_ok")
                                  + "/" +
                                  ("ion_dev" if ig != "conformant"
                                   else "ion_ok")] += 1
            else:
                grade_ambiguous += 1
                for g in possible:
                    bound_extra[g] += 1
                if not q["agree_hops"] and len(lh) == len(ih):
                    eqhop_excluded += 1

            if sum(n for n, _, _ in [(t[0], 0, 0) for t in tuples]
                   if n <= len(lh)) >= 2:
                tie_count += 1

            # predicted-route cross-check: the mirrors' routes must carry
            # the same graded tuples as the recorded routes, and the ION
            # mirror's window choice must be one of the thread resolutions
            key = (pid, q["src"], q["dst"], t0)
            p = preds.get(key)
            pl = pi = None
            if p:
                lp, ip = p.get("lean_pred"), p.get("ion_pred")
                if lp:
                    plterm = min(next(c for c in ctab[(f, t)]
                                      if c[2] == ts)[3]
                                 for f, t, ts in lp["hops"])
                    pl = (len(lp["hops"]), plterm, lp["hops"][0][1])
                    pred_check["lean_tuple_match" if tuple(pl) == ltuple
                               else "lean_tuple_diff"] += 1
                    pred_check["lean_grade_match" if grade(pl, sopt) == lg
                               else "lean_grade_diff"] += 1
                if ip:
                    piterm = min(next(c for c in ctab[(f, t)]
                                      if c[2] == ts)[3]
                                 for f, t, ts in ip["hops"])
                    pi = (len(ip["hops"]), piterm, ip["hops"][0][1])
                    pred_check["ion_term_in_threads" if piterm in terms
                               else "ion_term_outside_threads"] += 1
                    pg = grade(pi, sopt)
                    if len(possible) == 1:
                        pred_check["ion_grade_match" if pg == ig
                                   else "ion_grade_diff"] += 1
                    else:
                        pred_check["ion_ambiguous_resolved"] += 1
                        grades["ion_resolved_" + pg] += 1

            if dump:
                dump.write(json.dumps({
                    "plan": pid, "src": q["src"], "dst": q["dst"], "t0": t0,
                    "arrival": a, "sopt": list(sopt),
                    "filter_c_changed": sopt != sopt_u,
                    "lean": {"tuple": list(ltuple), "grade": lg},
                    "ion": {"hops": len(ih), "entry": ih[0][1],
                            "terms": terms, "grade": ig,
                            "possible_grades": possible,
                            "mirror_term": (pi[1] if pi else None)},
                }) + "\n")
                dump.flush()

    if dump:
        dump.close()

    # Grade bounds across thread resolutions: key-2 status is
    # thread-invariant (hops decide it before terms are consulted), so
    # only conformant/key3/key4 can swing. Lower bound = determinate
    # count; upper bound adds every swing dispatch that admits the grade.
    bounds = {}
    for g in ("conformant", "key3_dev", "key4_dev"):
        det = grades.get("ion_" + g, 0)
        bounds[g] = [det, det + bound_extra.get(g, 0)]

    lean_key3 = grades.get("lean_key3_dev", 0)
    lean_conf = grades.get("lean_conformant", 0)
    claim_checks = {
        "ion_key2_exact": grades.get("ion_key2_excess", 0),
        "lean_key2_exact": grades.get("lean_key2_excess", 0),
        "complementary_profile_at_worst":
            bounds["key3_dev"][1] < lean_key3
            and grades.get("lean_key2_excess", 0)
            < grades.get("ion_key2_excess", 0),
        "ion_more_conformant_at_worst":
            bounds["conformant"][0] > lean_conf,
    }

    report = {
        "epistemics": {
            "lean": "authority (what the recording binary did - 66948c9"
                    " two-key pickMin; provenance and mirror: predict.py)",
            "ion": "authority (what deployed ION 4.1.4 did)",
            "key1_truth": "state-space oracle, two-sided, unbounded class",
            "grading_truth": "exhaustive reuse-allowed enumeration,"
                             " self-bounded by the graded question, on the"
                             " 3.2.6.9 c) filtered universe (no contact"
                             " back to the forwarding node)",
            "triangulation": "ION anchors the arrival function, not the"
                             " route domain; the oracles test the domain",
            "spec_quantifier": "graded against 3.2.5.1 b) (list contains"
                               " every deliverable route); 3.2.6.9.1"
                               " licenses ceasing computation once one"
                               " candidate exists, so the singleton-list"
                               " reading is the text's own minimal"
                               " behavior - the verdict swing between the"
                               " two clauses is reported, not hidden",
        },
        "found_dispatches": found,
        "none_none": none_none,
        "owlt_range_entries": dict(sorted(owlt_hist.items())),
        "tie_among_minhop_optima": tie_count,
        "grades_reading": "strong (3.2.5.1 b complete list, 3.2.6.9"
                          " filters); the 3.2.6.9.1 cessation reading"
                          " zeroes the ION rows - see the"
                          " degrees-of-freedom note",
        "grades": dict(sorted(grades.items())),
        "filter_c_changed_sopt": filter_c_changed,
        "ion_thread_multiterm": multiterm,
        "ion_grade_ambiguous": grade_ambiguous,
        "ion_grade_bounds": bounds,
        "claim_checks": claim_checks,
        "equal_hop_divergence_buckets": dict(sorted(eqhop_buckets.items())),
        "equal_hop_excluded_grade_ambiguous": eqhop_excluded,
        "prediction_crosscheck": dict(sorted(pred_check.items())),
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
