# Window-gating slack sweep: registered test of the dense2x2 post-hoc mechanism

Status: REGISTERED 2026-06-10T05:54:37Z, before the corpus exists and
before any grading pass. The commit carrying this section is the
freeze; `out_s5/slack_sweep_predictions.json` holds the same anchors
(out_s5 is gitignored, so this tracked copy is the durable record).
Results and adjudication will be appended below the marked line, never
edited above it.

## What is under test

The dense2x2 adjudication (2026-06-09 note) left one post-hoc account
on the table, flagged unregistered in the paper's §8: the HETERO cell
missed its registered 90% keys-1-2 anchor because window starts on
shared downstream contacts gate departure (arrival is
max(t, start) + owlt on the shared leg), absorbing per-contact OWLT
differences - ties live where gating lives. Testable content: tie
mass should track gating, and removing the gating should let
per-contact heterogeneity discriminate fully.

## Design

`slack_sweep_v1`, generated in cislunar-lab from the frozen
`dense2x2_v1/HETERO` corpus (250 plans, per-contact OWLT 1980-3300 s).
Per level s, every contact's start moves earlier - new_start =
max(0, start - s*duration), end fixed, so windows only widen and
feasibility only grows; OWLT, rates, topology, and queries are
untouched. Levels: s = 0 (control), 0.5, 2, 8, OPEN (start = 0
everywhere - gating impossible by construction). Grading:
`s5field.py run` per level (sabrsearch + two-sided key-1 oracle),
`slackfield.py analyze` per level (ladder + gating metrics).

## Control calibration (published data, computed before registration)

Re-analysis of `out_s5/dense2x2_HETERO_results.jsonl` with
slackfield.py - the s=0 cell as already published: keys-1-2 pin 76.3%
(954/197/99/0), gating-any 46.5% of dispatches, and of the 296
tail-decided dispatches, 100.0% carry a gated hop on the selected
route (99.7% gated on the final hop). The mechanism's necessary
condition already holds exactly at the control; the sweep tests its
load-bearing direction.

## Registered anchors (binding; fail conditions explicit)

- **P1 monotone**: gating_any_pct strictly decreases at every step up
  the slack ladder, and keys12_pin_pct is non-decreasing at every step
  within 2.0 points (n=1250/level, s.e. ~1.2). FAIL if gating fails to
  fall at any step or the pin drops more than 2.0 at any step.
- **P2 endpoint clears the missed bar**: at OPEN, keys12_pin_pct >
  90.0 - the threshold the gated HETERO cell missed at 76.3. FAIL at
  <= 90.0, which refutes the gating account of the dense2x2 miss.
  (gating_any at OPEN must be 0.0 by construction; otherwise the
  generator is defective and the run is void, not a verdict.)
- **P3 control integrity**: the s0 level regenerates the source plans
  and reproduces the published ladder counts exactly (954/197/99/0).
  Any difference is a pipeline defect; fix before proceeding.
- **P4 ties live where gating lives**: at every level with >= 20
  tail-decided dispatches, tail_gated_any_pct >= 90.0. FAIL below.
- **P5 tracking**: Spearman rho(tie_mass_pct, gating_any_pct) >= 0.9
  across the five levels. FAIL below.

Verdict rule: CONFIRMED requires P1, P2, P4, P5 with P3 clean. P2
failing alone refutes the gating account even if the correlational
anchors pass.

---- RESULTS BELOW THIS LINE ARE APPENDED AFTER THE RUNS ----

## v1 corpus VOID at the 10-plan smoke: format defect, not a verdict

The first generator (pure start-shift) is void by the registration's
own instrument-validity clause. Both ionrc parsers - the harness
(`instrument.parse_ionrc`) and the Lean ingester (`Ionrc.lean`
`buildPlan`) - join range lines to contact lines by exact
(FROM, TO, START). The start-shift makes same-pair windows collide on
their start field (at OPEN, all 13 windows of a pair sit at +0), so
per-contact OWLT becomes inexpressible: the harness parser's dict
silently keeps the last range line, the Lean parser resolves the
ambiguity its own way, and the two sides no longer grade the same
plan. The smoke caught it as instrument failure, not as mechanism
data: key-1 disagreements 45/50 (OPEN) and 32/50 (s2) against a
two-sided oracle that had agreed on every dispatch of every prior
corpus. Disclosure: the smoke's ladder remnants over the few agreeing
dispatches read keys-1-2 pin 10.0% (OPEN, n=5) and 36.0% (s2, n=18);
these are computed over an ill-formed corpus with the two sides
disagreeing on key 1 itself and carry no evidential weight for the
anchors - recorded here so nothing seen goes unrecorded.

## Amendment (before any production run): de-collided starts

The rewrite gains one rule: after the slack shift, integer starts
within each directed pair are de-collided by +1 s bumps (sorted by
original start, then end; at most 12 s for the densest pair). The
bumps are two orders of magnitude below the OWLT scale (1980-3300 s)
and below every query t0 (120 s), so they cannot re-introduce
mechanism-relevant gating: at OPEN, starts sit at 0-12 s against
t0 = 120 s and downstream arrivals >= t0 + 1980 s, so gating_any
remains exactly 0.0 by construction and the registered void-check is
unchanged. At s0 no same-pair starts collide (real geometry), no
bumps fire, and the control regenerates the source plans unchanged -
P3 binds as registered. All anchors P1-P5 stand verbatim; nothing
about the prediction moved.
