#!/usr/bin/env python3
"""First-byte vs last-byte selection-key divergence on corpus_v3 (paper §8).

§3.2.8.1.4 a) 1) ranks candidates by projected bundle arrival time, which
§3.2.6.7 defines as last-byte arrival: first-byte arrival plus the
radiation latency EVC/rate of the contact before the terminal vertex. The
reference and ION 4.1.4 both score first-byte best-case arrival. This
runner measures what a last-byte-faithful selector would do differently:
for every dispatch on a fixed query grid over the corpus it enumerates
candidate routes to depth 3, picks a winner under both keys (exact
Fraction arithmetic for the EVC/rate term, remaining keys per
§3.2.8.1.4: fewest hops, latest termination, smallest entry node), and
classifies each winner change as either a first-byte tie the last-byte
key merely re-resolves (equal first-byte arrival - already counted as
route multiplicity) or a genuine inversion (the last-byte winner is
first-byte-suboptimal).

Generates the §8 numbers: 48000 dispatches, 44099 routable; genuine
inversions 0 / 12 / 7093 (16.1%) / 10203 (23.1%) at EVC 100 / 1e4 /
1e6 / 1e8; tie re-resolutions 34.7% at the kilobyte scales.

First run 2026-06-05 as a sandbox one-off while drafting the §8
paragraph; committed 2026-06-10 with the recovered algorithm unchanged
and re-verified against the published values.

Usage:
  pbat_inversion.py --corpus <corpus_v3 root> \
      --out out_s5/pbat_inversion_report.json
"""

import argparse
import json
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from instrument import parse_ionrc

DEPTH = 3
N_BUNDLES = 8
PAIRS_PER_PLAN = 6
EVCS = [100, 10_000, 1_000_000, 100_000_000]


def load(pdir):
    raw = parse_ionrc(pdir / "contact_plan.ionrc")
    nm = json.load(open(pdir / "plan_manifest.json"))["node_map"]
    rates = [int(ln.split()[6])
             for ln in (pdir / "contact_plan.ionrc").read_text().splitlines()
             if ln.startswith("a contact")]
    contacts = [(f, t, s, e, o, rates[i])
                for i, (f, t, s, e, o) in enumerate(raw)]
    by_from = defaultdict(list)
    for i, c in enumerate(contacts):
        by_from[c[0]].append((i, c))
    return contacts, by_from, nm


def routes(by_from, src, dst, t0):
    """Candidate routes as (first_byte_arrival, final_rate, hops, term, entry)."""
    out = []

    def dfs(node, t, depth, term, entry, used):
        if depth >= DEPTH:
            return
        for i, c in by_from.get(node, ()):
            if i in used:
                continue
            f, to, s, e, owlt, rate = c
            tx = t if t > s else s
            if tx > e:
                continue
            arr = tx + owlt
            nterm = e if term is None or e < term else term
            nentry = entry if entry is not None else to
            if to == dst:
                out.append((arr, rate, depth + 1, nterm, nentry))
            dfs(to, arr, depth + 1, nterm, nentry, used | {i})

    dfs(src, t0, 0, None, None, frozenset())
    return out


def pick(rs, key1):
    """§3.2.8.1.4 cascade: key1(arrival, rate), hops, latest term, entry."""
    return min(rs, key=lambda r: (key1(r[0], r[1]), r[2], -r[3], r[4]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", default="out_s5/pbat_inversion_report.json")
    args = ap.parse_args()

    corpus = Path(args.corpus).expanduser()
    plans = sorted(p for p in corpus.iterdir()
                   if (p / "contact_plan.ionrc").exists())

    dispatches = 0
    routable = 0
    multi_entry = 0
    skipped = []
    per_evc = {e: {"winner_changed": 0, "tie_reresolved": 0,
                   "genuine_inversion": 0, "examples": []} for e in EVCS}

    for n, pdir in enumerate(plans):
        try:
            contacts, by_from, nm = load(pdir)
            rows = [json.loads(l) for l in open(pdir / "pairs.jsonl")]
            pairs = sorted({tuple(q["pair"]) for q in rows})[:PAIRS_PER_PLAN]
            horizon = max(c[3] for c in contacts)
            for k in range(N_BUNDLES):
                t0 = (k + 1) * horizon // (N_BUNDLES + 1)
                for s, d in pairs:
                    dispatches += 1
                    rs = routes(by_from, nm[s], nm[d], t0)
                    if not rs:
                        continue
                    routable += 1
                    if len({r[4] for r in rs}) > 1:
                        multi_entry += 1
                    fb = pick(rs, lambda a, r: a)
                    for evc in EVCS:
                        lb = pick(rs, lambda a, r: a + Fraction(evc, r))
                        if fb[4] == lb[4]:
                            continue
                        R = per_evc[evc]
                        R["winner_changed"] += 1
                        if lb[0] > fb[0]:
                            R["genuine_inversion"] += 1
                        else:
                            R["tie_reresolved"] += 1
                        if len(R["examples"]) < 2:
                            R["examples"].append(dict(
                                plan=pdir.name, t0=t0, src=s, dst=d,
                                fb_entry=fb[4], fb_arr=fb[0], fb_rate=fb[1],
                                lb_entry=lb[4], lb_arr=lb[0], lb_rate=lb[1],
                                inversion=lb[0] > fb[0]))
        except Exception as ex:
            skipped.append({"plan": pdir.name, "error": repr(ex)[:200]})
        if (n + 1) % 100 == 0:
            print(f"{n + 1}/{len(plans)} plans", file=sys.stderr)

    n = routable or 1
    for evc in EVCS:
        R = per_evc[evc]
        R["tie_reresolved_pct"] = round(100 * R["tie_reresolved"] / n, 1)
        R["genuine_inversion_pct"] = round(
            100 * R["genuine_inversion"] / n, 1)

    report = {
        "corpus": str(corpus),
        "plans": len(plans),
        "depth": DEPTH,
        "pairs_per_plan": PAIRS_PER_PLAN,
        "n_bundles": N_BUNDLES,
        "dispatches": dispatches,
        "routable": routable,
        "multi_entry": multi_entry,
        "skipped_plans": skipped,
        "per_evc": {str(e): per_evc[e] for e in EVCS},
    }
    Path(args.out).write_text(json.dumps(report, indent=1))
    print(f"plans={len(plans)} dispatches={dispatches} routable={routable} "
          f"multi_entry={multi_entry} skipped={len(skipped)}")
    for evc in EVCS:
        R = per_evc[evc]
        print(f"EVC={evc:>11}: tie-reresolved={R['tie_reresolved']:>6} "
              f"({R['tie_reresolved_pct']}%)  genuine-inversion="
              f"{R['genuine_inversion']:>5} ({R['genuine_inversion_pct']}%)")


if __name__ == "__main__":
    main()
