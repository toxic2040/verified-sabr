# dense2x2 cell: adjudication of the registered prediction

Status: adjudicated 2026-06-09 against the frozen anchors. The runs
and grading completed 2026-06-05; the artifacts sat in `out_s5/` with
the harness scripts untracked and the paper still calling the cell
unmeasured. This note is the tracked record; the paper fold-in and the
script commits land with it.

## Registration

`out_s5/dense2x2_predictions.json`, written 2026-06-05T17:15:54Z,
before any grading pass (verified by file mtimes: results jsonl land
from 21:19Z). Source: the degrees-of-freedom note's "What drives the
ladder" section. Anchors, binding on the s5field keys-1-2-pin ladder:

- HOMOG (one large OWLT per plan): PASS below 50% keys-1-2 pin,
  strong pass below 40%; FAIL at or above 50%.
- HETERO (independent OWLT per contact): PASS above 90%; FAIL at or
  below 90%.
- Discrimination: HETERO minus HOMOG must exceed 40 points, and both
  individual thresholds must hold, for the cell to confirm the
  mechanism.

Registered mechanism: heterogeneous light times break ties,
homogeneous ones preserve them; the variable is arrival-value
degeneracy across parallel routes.

## Corpus

`cislunar-lab/out/dense2x2_v1` - corpus_v3's dense 13-node mesh with
every light time rewritten to 1980-3300 s integer seconds, HOMOG (one
value per plan) and HETERO (one per contact), 250 plans and 1250
dispatches per variant; topology, windows, and rates untouched.

## Result (out_s5/dense2x2_cell_results.json)

| cell | keys 1-2 | key 3 | key 4 | latent | anchor | verdict |
|---|---:|---:|---:|---:|---|---|
| DENSE-HOMOG | 22.9% | 69.1% | 8.0% | 0% | < 50 (strong < 40) | CONFIRMED, strong |
| DENSE-HETERO | 76.3% | 15.8% | 7.9% | 0% | > 90 | FAILED threshold; predicted side |

Separation 53.4 points (> 40 required: met). Key-1 disagreements zero
in both cells; latent full-tuple ties zero.

## Adjudication

Split, by the registration's own terms.

- **HOMOG: confirmed at the strong anchor.** 22.9% sits on
  corpus_v3's 24.6%. Equal light times at interplanetary scale
  reproduce the quantized cell, which settles what the quantized cell
  was measuring: arrival-value degeneracy, with zero-OWLT quantization
  one source of it rather than the variable itself.
- **HETERO: mixed - the conjunction registered as "confirm" is not
  met.** 76.3% is on the predicted high side with separation well
  past the requirement, but the registered PASS bound was > 90% and
  the cell came in 13.7 points under it. Per the discrimination
  clause (separation AND both thresholds), the cell does not confirm
  the registered mechanism as stated.
- **The miss has a mechanism, and it is post hoc.** Per-contact
  heterogeneity breaks only ties that accumulate OWLT. In the dense
  mesh, parallel routes frequently converge on a shared downstream
  contact whose window start gates departure (arrival is
  max(t, start) + owlt on the shared leg), absorbing per-hop OWLT
  differences; 296 of 1250 HETERO dispatches retain >= 2 tied
  minimum-hop routes, some at multiplicity 20-53. The registration
  treated propagation as the arrival-setter; wherever schedules are
  slack, waiting sets arrival, and waiting regenerates degeneracy.
  This account was constructed after the data and is flagged
  unregistered in the paper's §8; its testable content - tie mass
  wherever shared-contact window starts gate arrival - is untested
  beyond the cell that motivated it.

Corrected field statement carried into §6.1: route multiplicity
drives which key decides, degenerate arrivals are the amplifier, and
a dense schedule regenerates degeneracy through window gating at any
light-time scale.

## ION leg

`scripts/diffharness/dense2x2_ion_fold.py` ran live ION 4.1.4 over
both variants (one boot per source per plan, resumable);
`dense2x2_update_analysis.py` folded the results
(`out_s5/dense2x2_ION_live_analysis.md`). Route-exact agreement with
the lean selections: 72.64% (HETERO), 68.64% (HOMOG); every non-match
sits on a tied-multiplicity class, where lean and ION each
deterministically pick a different member of the tied class - the
§4.1/§7 candidate-list and tie-storage freedom expressing at
interplanetary light times. On matched routes arrivals agree within
the ~1 s dispatch quantization. The live leg confirms the graded
selections are executable against deployed ION; it neither
strengthens nor weakens the anchor verdicts above.

## Process note

The cell results, ION fold-in, and analysis were complete on
2026-06-05 and unrecorded for four days: scripts untracked, no note,
paper §6.1/§8 still claiming the cell unmeasured. Same fault line as
the dsn relay replay (2026-06-09 note): execution outran the record.
The verdict strings in `dense2x2_cell_results.json` also carry a
cosmetic artifact of that gap - the ION-confirmation suffix is
appended four times over, the update script having been re-run without
an idempotency guard.

## Paper deltas in this commit

- §2.4 gains the dense2x2_v1 corpus entry.
- §6.1 table gains both cell rows; the registered-prediction
  parenthetical becomes the adjudication (HOMOG confirmed strong,
  HETERO failed threshold on the predicted side, gating mechanism
  marked post hoc); the design statement covers the new cells.
- Abstract and §1 regime-field bullet carry the four-family field.
- §8 drops "unmeasured", adds the post-hoc-mechanism limitation.
- §9's self-falsification count goes six to seven.
- Appendix B gains the dense2x2 runners and frozen anchors.
- `dense2x2_ion_fold.py` and `dense2x2_update_analysis.py` are
  committed.
