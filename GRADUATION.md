# verified-sabr — Graduation package (draft)

**Status:** ready for owner-initiated public release  
**Decision recorded:** 2026-06-28 (YES graduate: GitHub + Zenodo, MIT)  
**This file:** local checklist only — no remote linked until owner GO at push time.

## What ships

A Lean 4 formalization of Schedule-Aware Bundle Routing (CCSDS 734.3-B-1 /
Contact Graph Routing practice), with:

- Executable earliest-arrival search (`lake exe sabrsearch`)
- Machine-checked soundness (`routeSearch_sound` / related; `#print axioms`
  limited to `propext`, `Classical.choice`, `Quot.sound`)
- Differential harness vs ION 4.1.4 (`scripts/diffharness/`) — 4100/4100
  found/none + arrival agreement on the published corpus
- Honest residual on four-key route selection (3882/4093 conformant; visited-
  contact list cost disclosed in README)

## Public surface checklist

- [ ] Owner voice pass on README (already accurate; confirm tone)
- [ ] Confirm LICENSE is MIT and headers match
- [ ] `lake build` clean on a fresh clone
- [ ] Strip any local paths / operator-only notes from tracked docs
- [ ] Create GitHub repo (suggested name: `verified-sabr`) under toxic2040 or a
      percolate-space org
- [ ] Push `master` (first remote)
- [ ] Tag `v0.1.0` with the ION-diff numbers frozen in the tag message
- [ ] Zenodo DOI from the GitHub release (or deposit tarball)
- [ ] One-line entry on percolate.space /projects with claim-status:
      `THEOREM (soundness + T2b arrival optimality) · RESULT (ION differential) · not full four-key route-selection optimality`

## Claim language (do not overshoot)

| Claim | Strength |
|-------|----------|
| Returned routes are plan-drawn, adjacent, window-feasible | THEOREM (Lean) |
| T2b earliest-arrival optimality (under stated model) | THEOREM (Lean; see docs/algorithm.md) |
| Found/none + earliest arrival match ION 4.1.4 on corpus | RESULT (4100/4100) |
| Full four-key route-selection optimum (arrival, hops, latest termination, smallest entry) | NOT claimed — residual disclosed (3882/4093) |
| Loop-freedom / multi-node forwarding | Planned, not shipped |

## Build (release gate)

```bash
lake exe cache get
lake build
# optional differential (needs ION 4.1.4 on PATH):
# python3 scripts/diffharness/compare.py --plans <corpus> --out <out>
```

## Deliberately not in this package

- SNTC / TIN claim revival
- Optimality closing of the explored-frontier gap (tracked in `docs/specs/`)
- Any dependency on private `perc-engine`

---

Owner action required to leave local-only: authorize remote + first push.
