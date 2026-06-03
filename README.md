# verified-sabr

A Lean 4 formalization of Schedule-Aware Bundle Routing (CCSDS 734.3-B-1),
the standardized form of Contact Graph Routing used in delay-tolerant space
networks.

Current state: executable model of contact plans and earliest-arrival route
search, with a machine-checked soundness theorem — every route the search
returns is plan-drawn, adjacent, and window-feasible (`VerifiedSabr/Validity.lean`).
Definitions carry references to the sections of the standard they model
(`docs/algorithm.md`).

Planned: optimality of the returned route, loop-freedom characterization for
multi-node forwarding, and differential testing against a reference
implementation. See `docs/specs/` for the design.

Build: `lake exe cache get && lake build`.

License: MIT.
