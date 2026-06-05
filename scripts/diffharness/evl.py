#!/usr/bin/env python3
"""The volume layer's binary question, answered by two-ledger replay.

Route selection under SABR is action-deterministic at every latent tie
(degrees-of-freedom note): two conformant implementations enqueue to
the same neighbor whenever their route tuples tie through key 4, and
the residue is which route OBJECT gets stored. 3.2.8.1.2 then reduces
the MTVs of the stored route's contacts, so the residue has exactly one
path to behavioral divergence: the volume ledger. Backlog state cannot
carry it (identical actions produce identical queues), and the four
keys never read MTV; the ledger reaches selection only through the
3.2.6.9 f)/g) volume filters. The question is therefore binary: does
post-selection MTV evolution amplify the representational residue into
different selections - different entry, or found against none - for
some later bundle, or does action-determinism wash it out?

The amplify branch is a theorem before any corpus runs; --selftest
carries the witness. Two tuple-equal routes S->E->A->D and S->E->B->D
(shared entry contact carries the route minimum, legs term-slack), one
bundle S->D: ledger A charges the A-leg, ledger B the B-leg, actions
identical. A second bundle sourced at A with EVC above the remaining
A-leg volume: under ledger A the only route is volume-filtered and the
bundle is UNROUTABLE; under ledger B it routes. Both systems were
spec-conformant at every step. The corpus replay measures the rate and
character of that mechanism on realistic structure.

Model, sections cited inline: candidate routes are no-reuse chains (the
3.2.6.10 generation class; at the selection optimum the class choice is
provably invisible) enumerated to a depth cap with truncations counted.
Arrival threading per 3.2.6.3-7: first-byte transmission = max(arrival,
contact start) threaded forward, last-byte = first-byte + EVC/rate, PBAT
= final contact's last-byte arrival (uniform-rate plans reduce to the
audited first-byte order; mixed-rate plans do not, so the full
semantics are implemented). Volume per 3.2.6.8: effective stop = min of
own and successors' stops, EVL = min(MTV, rate x effective duration),
RVL = min EVL over the route. Filters: 3.2.6.9 e) expiration vacuous
here, f) depleted, g) RVL < EVC with fragmentation not permitted (the
binding form). Charge per 3.2.8.1.2 at enqueue: every contact of the
stored route, EVC = size + max(0.03 x size, 100) per 1.4. One priority
level (3.2.6.8.1 NOTE's single-level option). Selection: keys 1-4 on
(PBAT, hops, termination desc, entry numeric asc); the stored object is
the canonical minimum (ledger A) or maximum (ledger B) of the
tuple-equal optimum class by contact-id sequence - the two extreme
conformant tie resolutions, bracketing every faithful implementation.

Traffic per plan: the plan's query pairs, K bundles each, dispatch
times staggered across the horizon, bundle size set so K bundles sum to
CONTENTION times the tightest pass volume on the t0-feasible routes.

Usage:
  evl.py selftest
  evl.py run --corpus <root> --glob '<plan glob>' --out <results.jsonl>
      [--bundles 24] [--contention 2.0]
  evl.py analyze --results <results.jsonl> --out <report.json>
"""

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from os import cpu_count
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from instrument import parse_ionrc, key1_oracle  # noqa: E402

def evc(size):
    """1.4: estimated convergence-layer overhead on top of the bundle."""
    return size + max(size * 3 // 100, 100)


def route_rvl(contacts, path, mtv):
    """3.2.6.8.6-10: effective stop is clipped by successor stops; EVL =
    min(MTV, rate x effective duration); RVL = min EVL."""
    rvl = None
    suffix_stop = None
    for i in reversed(path):
        f, to, s, e, owlt, rate = contacts[i]
        stop = e if suffix_stop is None or e < suffix_stop else suffix_stop
        suffix_stop = stop
        dur = stop - s
        if dur < 0:
            dur = 0
        evl = mtv[i] if mtv[i] < rate * dur else rate * dur
        if rvl is None or evl < rvl:
            rvl = evl
    return rvl


def select(contacts, by_from, src, dst, t0, evc_b, mtv, depth_cap,
           max_rate):
    """Keys-best volume-live candidate plus the canonical extremes of
    its tuple-tie class, by branch-and-bound: a prefix is pruned when
    its optimistic PBAT (first-byte arrival so far plus the radiation
    latency at the plan's best rate; owlt >= 0) already exceeds the
    best live route's PBAT - such a completion loses at key 1 and can
    neither be selected nor stored. Volume filters 3.2.6.9 f)/g)
    applied at the terminal (no-fragmentation form, RVL >= EVC).
    Returns (best_tuple, path_min, path_max, truncated)."""
    best = [None]		# (pbat, hops, -term, entry)
    tie = []
    truncated = [False]
    floor = evc_b / max_rate

    def dfs(node, t_first, depth, term, entry, used, path):
        if depth >= depth_cap:
            truncated[0] = True
            return
        if best[0] is not None and t_first + floor > best[0][0]:
            return
        for i, c in by_from.get(node, ()):
            if i in used:
                continue
            f, to, s, e, owlt, rate = c
            tx_first = t_first if t_first > s else s
            if tx_first > e:
                continue
            arr_first = tx_first + owlt
            nterm = e if term is None or e < term else term
            nentry = entry if entry is not None else to
            npath = path + (i,)
            if to == dst:
                arr_last = tx_first + evc_b / rate + owlt
                key = (arr_last, depth + 1, -nterm, nentry)
                if (best[0] is None or key <= best[0]) \
                        and route_rvl(contacts, npath, mtv) >= evc_b:
                    if best[0] is None or key < best[0]:
                        best[0] = key
                        tie.clear()
                    tie.append(npath)
            dfs(to, arr_first, depth + 1, nterm, nentry,
                used | {i}, npath)

    dfs(src, t0, 0, None, None, frozenset(), ())
    if best[0] is None:
        return None, None, None, truncated[0]
    b = best[0]
    return (b[0], b[1], -b[2], b[3]), min(tie), max(tie), truncated[0]


def replay_plan(pdir, n_bundles, contention, depth_cap):
    """Two-ledger replay over one plan. Returns the per-plan record."""
    raw = parse_ionrc(pdir / "contact_plan.ionrc")
    nm = json.load(open(pdir / "plan_manifest.json"))["node_map"]
    # parse_ionrc returns (from, to, start, end, owlt); rates live in the
    # contact lines - read them positionally (same order).
    rates = []
    for line in (pdir / "contact_plan.ionrc").read_text().splitlines():
        if line.startswith("a contact"):
            rates.append(int(line.split()[6]))
    contacts = [(f, t, s, e, o, rates[i])
                for i, (f, t, s, e, o) in enumerate(raw)]
    by_from = defaultdict(list)
    for i, c in enumerate(contacts):
        by_from[c[0]].append((i, c))

    qf = pdir / "queries.jsonl"
    if qf.exists():
        pairs = sorted({(q["src"], q["dst"]) for q in
                        (json.loads(line) for line in open(qf))})
    else:
        rows = [json.loads(line) for line in open(pdir / "pairs.jsonl")]
        if any(p.get("query") for p in rows):
            pairs = sorted({(p["src"], p["dst"]) for p in rows
                            if p.get("query")})
        else:
            # corpus_v3 schema: undirected pair lists, no query flag -
            # take a deterministic subset as traffic endpoints
            pairs = sorted({tuple(p["pair"]) for p in rows})[:6]
    horizon = max(c[3] for c in contacts)

    # dispatch schedule: K bundles per pair, staggered, interleaved
    dispatches = []
    for k in range(n_bundles):
        t0 = (k + 1) * horizon // (n_bundles + 1)
        for src, dst in pairs:
            dispatches.append((t0, src, dst))
    dispatches.sort()

    max_rate = max(c[5] for c in contacts)

    # bundle size: K bundles x pairs sum to `contention` x the tightest
    # volume on any contact of the first dispatch's tie class
    probe = None
    for t0, src, dst in dispatches:
        bt, pmin, _, _ = select(contacts, by_from, nm[src], nm[dst],
                                t0, 100, [10**18] * len(contacts),
                                depth_cap, max_rate)
        if bt:
            probe = pmin
            break
    if probe is None:
        return {"plan_id": pdir.name, "skipped": "no routable dispatch"}
    tight = min(contacts[i][5] * (contacts[i][3] - contacts[i][2])
                for i in probe)
    total_bundles = len(dispatches)
    size = max(1, int(contention * tight / total_bundles))
    evc_b = evc(size)

    # depth-cap closure check (uniform-rate plans): the key-1 oracle is
    # depth-free, so the volume-unconstrained optimal PBAT is its value
    # plus the constant radiation latency. A ledger whose SELECTED pbat
    # equals that optimum cannot be beaten at key 1 by any deeper route,
    # and deeper routes lose key 2 at equal pbat - so entry divergence
    # from beyond the cap is impossible at that dispatch. Dispatches
    # where a selection sits ABOVE the unconstrained optimum are the
    # only ones the cap leaves open; they are counted here.
    uniform_rate = len({c[5] for c in contacts}) == 1
    adj = defaultdict(list)
    for c in contacts:
        adj[c[0]].append(c[:5])

    mtv_a = [c[5] * (c[3] - c[2]) for c in contacts]
    mtv_b = list(mtv_a)
    residue_events = 0
    first_div = None
    actions = {"same": 0, "entry_diverged": 0, "found_none": 0}
    truncations = 0
    pbat_gap = 0
    for n, (t0, src, dst) in enumerate(dispatches):
        s, d = nm[src], nm[dst]
        bt_a, pa_min, pa_max, tr_a = select(contacts, by_from, s, d,
                                            t0, evc_b, mtv_a,
                                            depth_cap, max_rate)
        bt_b, pb_min, pb_max, tr_b = select(contacts, by_from, s, d,
                                            t0, evc_b, mtv_b,
                                            depth_cap, max_rate)
        truncations += tr_a or tr_b
        if (bt_a is None) != (bt_b is None):
            actions["found_none"] += 1
            if first_div is None:
                first_div = {"n": n, "type": "found_none",
                             "src": src, "dst": dst, "t0": t0,
                             "none_side_truncated":
                                 tr_a if bt_a is None else tr_b}
        elif bt_a is None:
            actions["same"] += 1
        elif bt_a[3] != bt_b[3]:
            actions["entry_diverged"] += 1
            if first_div is None:
                first_div = {"n": n, "type": "entry",
                             "src": src, "dst": dst, "t0": t0,
                             "entry_a": bt_a[3], "entry_b": bt_b[3]}
        else:
            actions["same"] += 1
            if uniform_rate and (tr_a or tr_b):
                a_star = key1_oracle(adj, s, d, t0)
                if a_star is not None:
                    opt = a_star + evc_b / contacts[0][5]
                    if bt_a[0] > opt or bt_b[0] > opt:
                        pbat_gap += 1
        # each ledger stores and charges its own conformant resolution:
        # A the canonical minimum of its tie class, B the maximum
        if bt_a is not None:
            if pa_min != pa_max:
                residue_events += 1
            for i in pa_min:
                mtv_a[i] -= evc_b
        if bt_b is not None:
            for i in pb_max:
                mtv_b[i] -= evc_b

    return {"plan_id": pdir.name, "dispatches": len(dispatches),
            "bundle_size": size, "residue_events": residue_events,
            "actions": actions, "first_divergence": first_div,
            "truncated_enumerations": truncations,
            "pbat_gap_dispatches": pbat_gap}


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
        futs = {pool.submit(replay_plan, p, args.bundles,
                            args.contention, args.depth): p.name
                for p in plans}
        n = 0
        for fut in as_completed(futs):
            pid = futs[fut]
            try:
                sink.write(json.dumps(fut.result()) + "\n")
            except Exception as e:
                sink.write(json.dumps({"plan_id": pid,
                                       "error": repr(e)}) + "\n")
            sink.flush()
            n += 1
            if n % 200 == 0:
                print(f"{n}/{len(plans)}")


def cmd_analyze(args):
    plans = diverged = entry_div = none_div = washed = 0
    residue_plans = residue_total = errors = truncs = 0
    first_examples = []
    for line in open(args.results):
        rec = json.loads(line)
        if "error" in rec:
            errors += 1
            continue
        if "skipped" in rec:
            continue
        plans += 1
        residue_total += rec["residue_events"]
        truncs += rec["truncated_enumerations"]
        if rec["residue_events"]:
            residue_plans += 1
        a = rec["actions"]
        if rec["first_divergence"]:
            diverged += 1
            if rec["first_divergence"]["type"] == "entry":
                entry_div += 1
            else:
                none_div += 1
            if len(first_examples) < 25:
                first_examples.append({"plan": rec["plan_id"],
                                       **rec["first_divergence"]})
        elif rec["residue_events"]:
            washed += 1
    report = {
        "plans": plans, "errors": errors,
        "plans_with_residue_events": residue_plans,
        "residue_events_total": residue_total,
        "plans_diverged": diverged,
        "diverged_entry": entry_div,
        "diverged_found_none": none_div,
        "plans_residue_washed_out": washed,
        "truncated_enumerations": truncs,
        "first_divergences": first_examples,
    }
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items()
                      if k != "first_divergences"}, indent=1))


def cmd_selftest(args):
    """The witness, end to end: charge divergence then found/none."""
    # rate 100 B/s puts contact volumes at 4000-6000 B, comfortably
    # above the 1.4 overhead floor on the bundle sizes below
    contacts = [
        ("S", "E", 0, 40, 0, 100),
        ("E", "A", 0, 50, 0, 100),
        ("A", "D", 0, 60, 0, 100),
        ("E", "B", 0, 50, 0, 100),
        ("B", "D", 0, 60, 0, 100),
    ]
    by_from = defaultdict(list)
    for i, c in enumerate(contacts):
        by_from[c[0]].append((i, c))
    mtv_a = [c[5] * (c[3] - c[2]) for c in contacts]
    mtv_b = list(mtv_a)
    size1 = 1900			# evc = 2000
    bt_a, pa, _, _ = select(contacts, by_from, "S", "D", 0,
                            evc(size1), mtv_a, 4, 100)
    bt_b, _, pb, _ = select(contacts, by_from, "S", "D", 0,
                            evc(size1), mtv_b, 4, 100)
    assert bt_a == bt_b and bt_a is not None, "tie class must select"
    assert pa != pb, "two distinct tuple-equal routes expected"
    for i in pa:
        mtv_a[i] -= evc(size1)
    for i in pb:
        mtv_b[i] -= evc(size1)

    # bundle 2: A->D, sized between the charged and uncharged leg volume
    size2 = 4500			# evc = 4635; A->D volume 6000/4000
    bt_a, _, _, _ = select(contacts, by_from, "A", "D", 0,
                           evc(size2), mtv_a, 4, 100)
    bt_b, _, _, _ = select(contacts, by_from, "A", "D", 0,
                           evc(size2), mtv_b, 4, 100)
    assert bt_a is None and bt_b is not None, \
        f"expected found/none divergence, got {bt_a} / {bt_b}"
    print("selftest: charge divergence amplified to found/none - the"
          " amplify branch is constructively real")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("selftest")
    s.set_defaults(fn=cmd_selftest)
    r = sub.add_parser("run")
    r.add_argument("--corpus", required=True)
    r.add_argument("--glob", default="lunanet_baseline_v2_plan_*")
    r.add_argument("--out", required=True)
    r.add_argument("--bundles", type=int, default=24)
    r.add_argument("--contention", type=float, default=2.0)
    r.add_argument("--depth", type=int, default=3,
                   help="route enumeration cap; truncations are counted,"
                        " never silent")
    r.set_defaults(fn=cmd_run)
    a = sub.add_parser("analyze")
    a.add_argument("--results", required=True)
    a.add_argument("--out", required=True)
    a.set_defaults(fn=cmd_analyze)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
