# verified-sabr

A Lean 4 formalization of Schedule-Aware Bundle Routing (CCSDS 734.3-B-1),
the standardized form of Contact Graph Routing used in delay-tolerant space
networks.

Current state: executable model of contact plans and earliest-arrival route
search with the visited-contact list of deployed CGR practice, a
machine-checked soundness theorem — every route the search returns is
plan-drawn, adjacent, and window-feasible (`VerifiedSabr/Validity.lean`) —
and differential validation against ION. Definitions carry references to the
sections of the standard they model (`docs/algorithm.md`).

## Differential testing

The verified search compiles to a CLI (`lake exe sabrsearch`) that ingests
ION-style contact plans (`a contact` / `a range` lines, integer fields) and
answers route queries with exact rational arithmetic. The harness under
`scripts/diffharness/` runs the same plans through ION 4.1.4 (`cgrfetch`
simulated dispatches against a throwaway single node) and compares outcomes
with dispatch instants aligned exactly: plans are loaded into ION at absolute
timestamps derived from an integer unix anchor, and the Lean side is queried
at the dispatch second ION reports back.

Result on 1000 generated cislunar contact plans (24 h horizons, 390–430
contacts each, 4100 route queries): found/none verdicts and earliest-arrival
times agree exactly with ION 4.1.4 on every query (4093 found/found, 7
none/none), independent of tie-break. Route selection uses the standard's
full four-key best-route order (arrival, hop count, latest termination,
smallest entry node — `Cand.le4`); graded against that four-key optimum the
returned route is conformant on 3882/4093 dispatches, the 210 key-3 and 1
key-4 residual deviations being the price of the deployed-practice
visited-contact list rather than a comparator gap. Per-regime breakdown:
`paper/sabr-regime-characterization.md`.
Methodology and ingestion semantics: `docs/algorithm.md` §8–§9. To reproduce
against any ionrc corpus:

```
python3 scripts/diffharness/compare.py --plans <corpus dir> --out <out dir>
python3 scripts/diffharness/report.py --jsonl <out dir>/diff_results.jsonl \
    --out <out dir>/agreement_report.json
```

Planned: global optimality of the returned route on the lower keys
(closing the explored-frontier gap; key 1 and four-key frontier-minimality
are proven) and loop-freedom characterization for multi-node forwarding.
See `docs/specs/` for the design.

Build: `lake exe cache get && lake build`. The default build includes the
test modules under `VerifiedSabr/Tests/`, whose `#guard` assertions are
checked at compile time.

License: MIT.
