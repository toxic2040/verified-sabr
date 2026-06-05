#!/usr/bin/env python3
"""Mechanism predictors: each implementation's returned route, derived from
its source, computed per dispatch BEFORE any comparison is run.

The audit (instrument.py v2) graded WHAT each implementation returned; this
module predicts WHICH route each returns, from the construction mechanism
read in the source, so the deviation sets stop being counts and become
consequences. Predictions are emitted by the `predict` phase from nothing
but the contact plan and the dispatch instant - recorded routes, arrivals,
and oracle verdicts are never read in that phase. The `score` phase joins
the frozen predictions against the recorded results.

ION side - bpv7/cgr/libcgr.c, ION 4.1.4, read 2026-06-05:

  In the unloaded regime (size-0 bundle, no queue backlog, no blocked or
  missing egress plans, expiration beyond the horizon) loadBestRoutesList
  stops the moment the candidate list is nonempty at the end of the
  selected-routes walk, and the first Dijkstra route passes every check in
  checkRoute/tryRoute. The Yen/Lawler registry (computeAnotherRoute,
  computeSpurRoute) never iterates: the returned route IS the single
  insertFirstRoute Dijkstra route. Every cgrfetch capture in corpus_v3
  contains exactly one route. tryRoute's comparator is a faithful
  transcription of 3.2.8.1.4 keys 1-4 (pbat, fewest hops, latest toTime,
  smallest entry node) - it just never sees a second candidate.

  computeDistanceToTerminus, the mechanism that therefore decides
  everything (line numbers from the 4.1.4 tree):

  - relaxation (l.610): strict `<` on best-case arrival only; an
    equal-arrival path NEVER updates a work area, so predecessor and
    hopCount keep the values of the path that first strictly improved the
    arrival - hopCount is a history artifact, not a minimum;
  - next-current selection (l.645-698): global scan of all contacts in
    contact-index order (regionNbr, fromNode, toNode, fromTime ascending;
    rfx_order_contacts), lexicographic (arrivalTime, hopCount), with ties
    keeping the earliest contact in index order;
  - termination (l.714): the outer loop stops at the FIRST popped contact
    that delivers to the terminus node;
  - successor admission (l.545): contact must end strictly after the
    arrival at the sender (toTime > arrival); transmit = max(arrival,
    fromTime); arrival' = transmit + owlt + margin, where margin =
    (MAX_SPEED_MPH/3600)*owlt/186282 in integer arithmetic = 0 for all
    owlt below 1491 s (everything in this corpus; nonzero from ~1491 s,
    relevant to the helio B2/B3 bands);
  - range lookup (getApplicableRange, l.299): first range for the node
    pair, in fromTime order, whose toTime is not earlier than the
    contact's fromTime; a contact with no applicable range is suppressed;
  - contacts whose toTime <= dispatch time are skipped (l.500, l.654);
    registration contacts are type-skipped (corpus plans contain none).

  Spec keys in this mechanism: key 1 holds globally (the relaxation is a
  sound earliest-arrival Dijkstra); key 2 is attempted at pop time but
  over stale hopCounts, so the returned route's hop count is not minimal
  among arrival-optimal routes; key 3 is never consulted anywhere; key 4
  is never consulted, but the index-order tie-break biases toward small
  node numbers structurally.

lean side - VerifiedSabr/Search.lean AS OF THE RECORDING RUN:

  Version fact, established 2026-06-05: the sabrsearch binary that
  produced out_diff_v3 (mtime 06-03 23:33; diff_results.jsonl mtime
  06-04 02:18) was built at 66948c9, BEFORE the full 4-key pickMin
  (3e4d2a0, 06-04 13:38). The recorded routes - the routes the audit
  graded - were selected by the two-key comparator:

      c.arrival < m.arrival
        or (c.arrival = m.arrival and c.hops.length <= m.hops.length)

  with full ties resolving to the leftmost frontier element. Keys 3-4
  were NOT in the recording comparator. Everything below key 2 in the
  recorded data is therefore resolved by frontier ORDER: expansion
  filters the plan in file order, forbids contact reuse within a
  candidate, admits a window when max(arrival, tStart) <= tEnd (lean
  admits transmission at the closing instant; ION requires strictly
  earlier), and PREPENDS new candidates to the frontier, reversing
  relative order between expansion generations. The visited list closes
  the popped candidate's terminal contact; a popped candidate whose
  terminal contact is already closed is dropped unexpanded. A popped
  candidate sitting at the destination returns immediately. Fuel
  (n+1)^2+1 per searchLoop step.

  Spec keys in the recorded data: key 1 global (theorem), key 2 held by
  the pop order, keys 3-4 BLIND - the comparator never consults
  termination or entry, so the 2024 key-3 and 49 key-4 deviations are
  frontier-order artifacts gated by the closed list, NOT string-order
  effects (the le4 string comparison postdates the recording). The
  --order le4 mode mirrors the current source (3e4d2a0+) for the
  version differential; its corpus run is meaningful only against a
  binary rebuilt from that source, not against out_diff_v3.

Usage:
  predict.py predict --results out_diff_v3/diff_results.jsonl \
      --corpus <corpus root> --out out_diff_v3/predictions.jsonl
  predict.py score --results out_diff_v3/diff_results.jsonl \
      --predictions out_diff_v3/predictions.jsonl \
      --out out_diff_v3/prediction_score.json
"""

import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from os import cpu_count
from pathlib import Path

MAX_SPEED_MPS = 450000 // 3600		# ion.h MAX_SPEED_MPH / 3600


def parse_plan(pdir):
    """Contacts and ranges in file order, fields as raw line tokens."""
    contacts, ranges = [], []
    for line in (pdir / "contact_plan.ionrc").read_text().splitlines():
        parts = line.split()
        if line.startswith("a contact"):
            contacts.append((parts[4], parts[5], int(parts[2].lstrip("+")),
                             int(parts[3].lstrip("+")), int(parts[6])))
        elif line.startswith("a range"):
            ranges.append((parts[4], parts[5], int(parts[2].lstrip("+")),
                           int(parts[3].lstrip("+")), int(parts[6])))
    return contacts, ranges


# ---------------------------------------------------------------- ION mirror

def ion_route(contacts, ranges, src, dst, t0):
    """First-Dijkstra route per computeDistanceToTerminus, or None.

    contacts: (from, to, s, e, rate) with int node numbers, index-sorted
    by the caller. Returns hops as (from, to, tStart) triples.
    """
    n = len(contacts)
    INF = None
    arrival = [INF] * n
    hop = [0] * n
    pred = [None] * n		# index of predecessor contact; -1 = root
    visited = [False] * n
    suppressed = [False] * n

    by_from = {}
    for i, c in enumerate(contacts):
        by_from.setdefault(c[0], []).append(i)

    # getApplicableRange: first range for the pair, in fromTime order,
    # with toTime >= contact fromTime.
    rng = {}
    for rf, rt, rs, re_, rv in ranges:
        rng.setdefault((rf, rt), []).append((rs, re_, rv))
    for k in rng:
        rng[k].sort()

    def applicable_owlt(c):
        for rs, re_, rv in rng.get((c[0], c[1]), ()):
            if re_ < c[2]:
                continue
            owlt = rv + (MAX_SPEED_MPS * rv) // 186282
            return owlt
        return None

    cur_node, cur_arrival, cur_hop, cur_idx = src, t0, 0, -1
    while True:
        for i in by_from.get(cur_node, ()):
            c = contacts[i]
            if c[3] <= t0 or suppressed[i] or visited[i]:
                continue
            if c[3] <= cur_arrival:		# l.545: must end after arrival
                continue
            owlt = applicable_owlt(c)
            if owlt is None:
                suppressed[i] = True
                continue
            tx = cur_arrival if cur_arrival > c[2] else c[2]
            arr = tx + owlt
            if arrival[i] is None or arr < arrival[i]:	# strict < only
                arrival[i] = arr
                pred[i] = cur_idx
                hop[i] = cur_hop + 1
        if cur_idx >= 0:
            visited[cur_idx] = True

        best = -1
        for i in range(n):		# index order; first strict best wins
            if contacts[i][3] <= t0 or suppressed[i] or visited[i] \
                    or arrival[i] is None:
                continue
            if best >= 0:
                if arrival[i] > arrival[best]:
                    continue
                if arrival[i] == arrival[best] and hop[i] >= hop[best]:
                    continue
            best = i
        if best < 0:
            return None
        cur_idx = best
        c = contacts[best]
        cur_node, cur_arrival, cur_hop = c[1], arrival[best], hop[best]
        if c[1] == dst:
            hops = []
            i = best
            while i >= 0:
                c = contacts[i]
                hops.append((c[0], c[1], c[2]))
                i = pred[i]
            hops.reverse()
            return {"arrival": cur_arrival, "hops": hops}


# --------------------------------------------------------------- lean mirror

def lean_route(contacts, ranges, src, dst, t0, order="twokey"):
    """Mirror of routeSearch: best-first with the closed list.

    order="twokey" mirrors the recording binary (66948c9): lexicographic
    (arrival, hop count), leftmost tie. order="le4" mirrors the current
    source (3e4d2a0+): full 3.2.8.1.4 a) comparison with termination
    down (root as +inf) and entry node up as strings.

    contacts/ranges: raw-token tuples in FILE order; src/dst are node
    strings. Returns hops as (from, to, tStart) int triples plus the
    count of drop-at-closed-contact events (the mechanism's footprint).
    """
    # buildPlan: join by exact (from, to, start), first match, default 0
    rng = {}
    for rf, rt, rs, re_, rv in ranges:
        rng.setdefault((rf, rt, rs), rv)
    cp = [(c[0], c[1], c[2], c[3], rng.get((c[0], c[1], c[2]), 0))
          for c in contacts]

    by_source = {}
    for c in cp:
        by_source.setdefault(c[0], []).append(c)

    # candidate: (hops tuple most-recent-first, arrival, nhops, term, entry)
    root = ((), t0, 0, None, None)

    def le_twokey(c, m):
        if c[1] != m[1]:
            return c[1] < m[1]
        return c[2] <= m[2]

    def le4(c, m):
        if c[1] != m[1]:
            return c[1] < m[1]
        if c[2] != m[2]:
            return c[2] < m[2]
        if c[3] != m[3]:		# termLater, None as +inf
            if c[3] is None:
                return True
            if m[3] is None:
                return False
            return m[3] < c[3]
        if c[4] is None:		# entryLE, root first, string order
            return True
        if m[4] is None:
            return False
        return c[4] <= m[4]

    le = le_twokey if order == "twokey" else le4

    def expand(cand):
        hops, arr = cand[0], cand[1]
        node = hops[0][1] if hops else src
        entry = cand[4]
        out = []
        for c in by_source.get(node, ()):
            tx = arr if arr > c[2] else c[2]
            if tx > c[3] or c in hops:
                continue
            nterm = c[3] if cand[3] is None or c[3] < cand[3] else cand[3]
            out.append(((c,) + hops, tx + c[4], cand[2] + 1, nterm,
                        entry if entry is not None else c[1]))
        return out

    frontier = [root]
    closed = set()
    drops = 0
    fuel = (len(cp) + 1) * (len(cp) + 1) + 1
    while fuel and frontier:
        fuel -= 1
        bi = len(frontier) - 1		# pickMin: leftmost tie-winner
        for i in range(len(frontier) - 2, -1, -1):
            if le(frontier[i], frontier[bi]):
                bi = i
        best = frontier.pop(bi)
        hops = best[0]
        node = hops[0][1] if hops else src
        if node == dst and hops:
            # Own-list reading (the weakest construal of 3.2.8.1.4's
            # quantifier): every dst-complete candidate the search ever
            # enumerated is still in the frontier here - dst candidates
            # are never dropped, and only one dst pop occurs. The
            # returned route conforms list-relatively iff no enumerated
            # arrival-and-hop-tied competitor beats it at spec keys 3-4
            # (termination down, entry NUMERIC up per 3.2.8.1.4 a) 4).
            dominated = None
            for c in frontier:
                if not c[0] or c[0][0][1] != dst:
                    continue
                if c[1] != best[1] or c[2] != best[2]:
                    continue
                if c[3] > best[3] or (c[3] == best[3]
                                      and int(c[4]) < int(best[4])):
                    dominated = {"term": c[3], "entry": int(c[4])}
                    break
            return {"arrival": best[1],
                    "hops": [(int(c[0]), int(c[1]), c[2])
                             for c in reversed(hops)],
                    "drops": drops,
                    "own_list_dominated": dominated,
                    "own_tuple": [best[2], best[3], int(best[4])]}
        if not hops:
            frontier = expand(best) + frontier
            continue
        c = hops[0]
        if c in closed:
            drops += 1
            continue
        closed.add(c)
        frontier = expand(best) + frontier
    return None


# ------------------------------------------------------------------- phases

def predict_plan(pdir, queries, order):
    """All predictions for one plan. queries: [(src_name, dst_name, t0)]."""
    contacts, ranges = parse_plan(pdir)
    node_map = json.load(open(pdir / "plan_manifest.json"))["node_map"]

    icontacts = sorted(((int(f), int(t), s, e, v)
                        for f, t, s, e, v in contacts))
    iranges = [(int(f), int(t), s, e, v) for f, t, s, e, v in ranges]

    out = []
    for src, dst, t0 in queries:
        isrc, idst = node_map[src], node_map[dst]
        ion = ion_route(icontacts, iranges, isrc, idst, t0)
        lean = lean_route(contacts, ranges, str(isrc), str(idst), t0, order)
        out.append({"src": src, "dst": dst, "t0": t0,
                    "ion_pred": ion, "lean_pred": lean})
    return out


def run_predict(args):
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
    print(f"{len(done)} plans already predicted, {len(plans)} to go")

    with open(outp, "a") as sink, \
            ProcessPoolExecutor(max_workers=cpu_count()) as pool:
        futs = {pool.submit(predict_plan, corpus / pid, qs, args.order): pid
                for pid, qs in plans}
        ndone = 0
        for fut in as_completed(futs):
            pid = futs[fut]
            try:
                preds = fut.result()
                sink.write(json.dumps({"plan_id": pid, "queries": preds})
                           + "\n")
                sink.flush()
            except Exception as e:
                sink.write(json.dumps({"plan_id": pid, "error": repr(e)})
                           + "\n")
                sink.flush()
            ndone += 1
            if ndone % 100 == 0:
                print(f"{ndone}/{len(plans)}")

    digest = hashlib.sha256(outp.read_bytes()).hexdigest()
    print(f"predictions frozen: {outp} sha256={digest}")


def run_score(args):
    preds = {}
    for line in open(args.predictions):
        rec = json.loads(line)
        if "error" in rec:
            print(f"PREDICTION ERROR {rec['plan_id']}: {rec['error']}",
                  file=sys.stderr)
            continue
        for q in rec["queries"]:
            preds[(rec["plan_id"], q["src"], q["dst"], q["t0"])] = q

    tallies = {"dispatches": 0, "skipped_none": 0,
               "ion_route_exact": 0, "ion_route_diff": 0,
               "ion_arrival_agree": 0,
               "lean_route_exact": 0, "lean_route_diff": 0,
               "lean_arrival_agree": 0}
    ion_misses, lean_misses = [], []
    for line in open(args.results):
        rec = json.loads(line)
        for q in rec["results"]:
            lean, ion = q.get("lean"), q.get("ion")
            if not lean or not ion or lean.get("hops") is None \
                    or ion.get("hops") is None:
                tallies["skipped_none"] += 1
                continue
            tallies["dispatches"] += 1
            key = (rec["plan_id"], q["src"], q["dst"], q["t0"])
            p = preds.get(key)
            if p is None:
                print(f"NO PREDICTION for {key}", file=sys.stderr)
                continue

            ip = p["ion_pred"]
            recorded = [tuple(h) for h in ion["hops"]]
            predicted = ([(f, t) for f, t, _ in ip["hops"]]
                         if ip else None)
            if predicted == recorded:
                tallies["ion_route_exact"] += 1
            else:
                tallies["ion_route_diff"] += 1
                if len(ion_misses) < 50:
                    ion_misses.append({"key": list(key),
                                       "recorded": recorded,
                                       "predicted": predicted})
            if ip and ip["arrival"] == ion["arrival"]:
                tallies["ion_arrival_agree"] += 1

            lp = p["lean_pred"]
            recorded = [tuple(h) for h in lean["hops"]]
            predicted = ([tuple(h) for h in lp["hops"]] if lp else None)
            if predicted == recorded:
                tallies["lean_route_exact"] += 1
            else:
                tallies["lean_route_diff"] += 1
                if len(lean_misses) < 50:
                    lean_misses.append({"key": list(key),
                                        "recorded": recorded,
                                        "predicted": predicted})
            if lp and lp["arrival"] == lean["arrival"]:
                tallies["lean_arrival_agree"] += 1

    report = {"tallies": tallies, "ion_misses": ion_misses,
              "lean_misses": lean_misses}
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(json.dumps(tallies, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("predict")
    p.add_argument("--results", default="out_diff_v3/diff_results.jsonl")
    p.add_argument("--corpus", required=True)
    p.add_argument("--out", default="out_diff_v3/predictions.jsonl")
    p.add_argument("--order", choices=["twokey", "le4"], default="twokey",
                   help="lean comparator: recording binary (66948c9) or"
                        " current source (3e4d2a0+)")
    p.set_defaults(fn=run_predict)
    s = sub.add_parser("score")
    s.add_argument("--results", default="out_diff_v3/diff_results.jsonl")
    s.add_argument("--predictions", default="out_diff_v3/predictions.jsonl")
    s.add_argument("--out", default="out_diff_v3/prediction_score.json")
    s.set_defaults(fn=run_score)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
