# verified-sabr — v1 design

2026-06-03

## Why

Schedule-Aware Bundle Routing (SABR, CCSDS 734.3-B-1) is the standardized form of
Contact Graph Routing and the routing layer being deployed toward LunaNet-era and
deep-space DTN networks. Its correctness properties are handled informally: the
literature documents routing loops and patches them with heuristics (Caini 2021
proposes "enhancements for resistance against possible loops"), and no
mechanized verification of CGR/SABR exists in any proof assistant — not Lean,
Rocq, Isabelle, or TLA+. The nearest prior art is HOL+SPIN verification of
distance-vector protocols (RIP, AODV loop-freedom), a different protocol family.

Standardized protocol, known correctness gap, zero mechanization. That is the
opening.

## Deliverable

A public Lean 4 repository containing:

1. An executable model of SABR contact-plan route computation, with every
   definition traceable to its Blue Book section.
2. Kernel-checked theorems: route validity, earliest-arrival optimality, and a
   loop-freedom characterization with explicit counterexamples outside its
   hypotheses.
3. A differential-test harness showing the Lean executable agrees with a
   deployed reference implementation on randomized contact plans.
4. A short paper (Zenodo first, arXiv second) when the loop theorem lands.

The claim the artifact supports: "the route-search procedure standardized in
CCSDS 734.3-B-1, as written, provably satisfies X under conditions Y, and
provably fails outside them — kernel-checked, code and counterexamples public."

## Scope

In (v1):

- Contact plan model, contact graph construction, route well-formedness.
- Executable route search (the standard's modified Dijkstra, earliest arrival).
- Theorems T1–T3 below.
- Differential testing against one reference implementation.
- Demo evaluation on one real contact plan.

Out (v1):

- BPv7 bundle-agent state machine (RFC 9171) — separate project if ever.
- Volume / effective-volume-limit (EVL) accounting in route selection.
  Decide in Phase 0 whether time-feasibility-only route search is a faithful
  restriction of the standard or a strawman; if the latter, EVL moves in-scope
  and the schedule stretches.
- Bundle expiration/deadline filtering and the standard's full best-route
  tie-break order; both are route-selection concerns, deferred together.
- Contact plan distribution/synchronization protocols.
- Opportunistic/probabilistic contacts; scheduled contacts only.
- BPSec, fragmentation, custody.

## Model

- Time is ℚ. Exact arithmetic keeps ordering decidable and everything
  executable; no real analysis is needed anywhere in the development.
- `Contact`: from-node, to-node, start, end, transmission rate, one-way light
  time. Contact plan: finite list of contacts.
- Contact graph per the standard: vertices are contacts, edges are temporally
  feasible successions (receiver of A is sender of B; arrival at B's sender,
  including propagation, falls inside B's window or before it with waiting).
- `Route`: a contact sequence with a well-formedness predicate covering
  adjacency, window feasibility, and propagation delay. Earliest arrival time
  is computed by structural recursion over the route.
- `routeSearch : ContactPlan → Node → Node → Time → Option Route` — executable,
  mirroring the Blue Book procedure. Exact tie-breaking criteria (hop count,
  termination time) pinned in Phase 0 from the Blue Book text, not from
  secondary sources.

## Theorems

- **T1 — route validity (soundness).** Any route returned by `routeSearch` is
  well-formed: plan-drawn, adjacent, and window-feasible from the start time.
  First presentable result. Bundle-deadline filtering belongs to route
  selection and moves to v2 with the full tie-break order.
- **T2 — optimality.** The returned route minimizes earliest arrival time over
  all well-formed routes in the plan. Dijkstra-correctness on the contact
  graph; the hard grind, but a well-trodden proof pattern.
- **T3 — loop characterization.** Multi-node forwarding model: each node runs
  `routeSearch` over its own contact plan and forwards accordingly.
  - T3a: under identical and accurate plans at every node, no bundle revisits
    a node (or revisits are bounded — exact statement fixed during proof).
  - T3b: explicit counterexample family under plan inconsistency, reproducing
    the loop phenomenology the literature patches heuristically.

T2 is the stall risk. If it drags, T1 + T3 alone are a publishable artifact;
reorder rather than block.

## Reality bridge

The standing failure mode this project must design out is verification that
restates its target. Three independent gates:

1. **Spec traceability.** Every Lean definition carries a comment naming the
   Blue Book section it models. A reviewer can diff model against standard
   without trusting the author.
2. **Differential testing.** The Lean executable runs against a reference
   implementation (candidates: pyCGR, µD3TN, ION, HDTN — pick one in Phase 0)
   on randomized contact plans. The oracle is external code we did not write;
   agreement is a prediction-class check, not a consistency-class one. Disagreements
   are findings either way: a model bug or a reference-implementation bug.
3. **Real-data demo.** `#eval` route computation on a contact plan derived from
   the archived DSN scheduling data. Demonstration, not evidence — labeled as
   such.

## Phases

Each phase has an exit criterion; no phase starts until the previous one's
criterion is met.

- **P0 — pin the target.** Obtain CCSDS 734.3-B-1 (ccsds.org, free), Caini
  2021, Fraire et al. 2021 tutorial. Write `docs/algorithm.md`: the exact
  procedure being modeled, with section references, including the EVL
  in/out decision and the oracle choice. Exit: algorithm.md complete; no Lean
  written before it.
- **P1 — structures.** Lean project setup (toolchain check first — prior Lean
  environment was archived), core types, well-formedness predicates,
  contact-graph construction. Exit: definitions compile, traceability comments
  in place.
- **P2 — executable search.** `routeSearch` runs on toy plans. Exit: `#eval`
  matches hand-computed routes on at least three worked examples, one from the
  published tutorial.
- **P3 — T1 validity.** Exit: theorem checked, zero sorry.
- **P4 — T2 optimality.** Exit: theorem checked, zero sorry — or a documented
  decision to defer and proceed.
- **P5 — T3 loops.** Forwarding model, T3a proof, T3b counterexamples. Exit:
  both checked, zero sorry.
- **P6 — differential harness.** Random plan generator, oracle runs, agreement
  report. Exit: N ≥ 1000 random plans, all agreements or all disagreements
  explained.
- **P7 — paper and outreach.** Zenodo, then arXiv. Direct contact: Fraire,
  Caini, CCSDS SIS-DTN, IPNSIG.

Workflow: structures, theorem statements, and proof skeletons are blueprinted
before tactic work begins; disposition decisions stay with the author.

## Risks

- **Strawman model.** Mitigated by P0-before-code and the traceability gate.
  This is the kill case: if the model can't be tied line-by-line to the Blue
  Book, the result is ignorable and the project has failed regardless of how
  many theorems check.
- **T2 stalls.** Mitigated by reordering (see Theorems).
- **Loop theorem turns out trivial or known.** Partially mitigated by the
  novelty search (nothing mechanized exists), but if T3a follows in three lines
  from strictly increasing arrival times, the contribution thins. Counter:
  the counterexample family T3b and the precise hypothesis boundary are the
  contribution, not the happy path.
- **Audience indifference.** Possible. The artifact still stands alone as the
  first mechanization of a CCSDS routing standard, and the cost of outreach on
  top of a finished artifact is near zero.

## Licensing and publication

Code MIT. Paper CC-BY-4.0. Zenodo before arXiv. No paper or figure PDFs
committed to the repo.

## Open questions (decided in P0)

- Final repo name (`verified-sabr` is the working name).
- EVL/volume in or out of the v1 route search.
- Reference oracle choice.
- Exact T3a statement (strict loop-freedom vs bounded revisits).
