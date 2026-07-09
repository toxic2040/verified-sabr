# verified-sabr — claim status and scope

This project formalizes Schedule-Aware Bundle Routing (CCSDS 734.3-B-1), the
standardized form of Contact Graph Routing used in delay-tolerant space
networks, in Lean 4. This document states exactly what is proved, what is
measured, and what is deliberately not claimed.

## What the project provides

- Executable earliest-arrival route search (`lake exe sabrsearch`) over
  ION-style contact plans, using exact rational arithmetic.
- Machine-checked soundness (`routeSearch_sound`): every route the search
  returns is plan-drawn, adjacent, and window-feasible.
- Machine-checked earliest-arrival optimality (`routeSearch_optimal`, the
  T2b result): the returned route's arrival time is optimal under the stated
  model.
- A differential harness against ION 4.1.4 (`scripts/diffharness/`):
  found/none verdicts and earliest-arrival times agree on 4100/4100 route
  queries across 1000 generated cislunar contact plans, independent of
  tie-break.
- An honest residual on full four-key route selection: 3882/4093 dispatches
  conformant, with the deployed visited-contact-list cost disclosed in the
  README and the per-regime breakdown in `paper/`.

Both machine-checked theorems reduce to the standard classical axioms only —
`propext`, `Classical.choice`, `Quot.sound` — re-reported on every build by
`VerifiedSabr/Tests/Axioms.lean`.

## Claim language

| Claim | Strength |
|-------|----------|
| Returned routes are plan-drawn, adjacent, window-feasible | THEOREM (Lean) |
| T2b earliest-arrival optimality (under the stated model) | THEOREM (Lean; see `docs/algorithm.md`) |
| Found/none and earliest arrival match ION 4.1.4 on corpus | RESULT (4100/4100) |
| Full four-key route-selection optimum (arrival, hops, latest termination, smallest entry) | NOT claimed — residual disclosed (3882/4093) |
| Loop-freedom / multi-node forwarding | Planned, not shipped |

## Build

```bash
lake exe cache get
lake build
# optional differential (needs ION 4.1.4 on PATH):
# python3 scripts/diffharness/compare.py --plans <corpus> --out <out>
```

## Deliberately out of scope

- Global four-key route-selection optimality (the explored-frontier gap;
  the design is tracked in `docs/specs/`).
- Loop-freedom characterization for multi-node forwarding.

License: MIT.
