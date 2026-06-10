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

## Production results (250 plans x 5 levels, 1250 dispatches each)

Corpus built with `cislunar-lab run_slack_corpus` (commit 98ff4ac),
graded with `s5field.py run` + `slackfield.py analyze`; artifacts in
`out_slack/` (gitignored; this note is the tracked record). Key-1
disagreements: zero at every level - the two-sided oracle gate that
voided v1 is clean.

| level | keys 1-2 pin | tie mass | gating any | gating final | tail n | tail gated any |
|---|---:|---:|---:|---:|---:|---:|
| s0 (control) | 76.3% | 23.7% | 46.5% | 46.4% | 296 | 100.0% |
| s05 | 87.1% | 12.9% | 29.5% | 29.4% | 161 | 98.8% |
| s2 | 97.8% | 2.2% | 2.9% | 2.8% | 28 | 96.4% |
| s8 | 99.8% | 0.2% | 0.0% (raw 0) | 0.0% | 3 | exempt (<20) |
| OPEN | 99.8% | 0.2% | 0.0% (raw 0) | 0.0% | 3 | exempt (<20) |

The three residual ties at s8 and OPEN are the same three dispatches
(plans 000166/000201/000249), multiplicity 2, no gated hop on either
route - the predicted OWLT-sum-collision residue, at 2.4 per
thousand against the registered "few percent at most."

## Adjudication, by the registered terms

- **P3 control integrity: CLEAN.** s0 ladder 954/197/99/0, equal to
  the published cell exactly; zero de-collision bumps fired.
- **P1 monotone: FAILED BY LETTER at one floor-degenerate step.**
  gating_any falls 46.5 -> 29.5 -> 2.9 -> 0 and then sits at exactly
  zero for s8 -> OPEN; the registered letter demanded a strict
  decrease at EVERY step, including between two exact zeros. The pin
  is non-decreasing at every step (76.3 -> 87.1 -> 97.8 -> 99.8 ->
  99.8), and no step anywhere shows a reversal - the failure mode the
  anchor was written to catch (gating not responding to slack) did
  not occur. The defect is in the anchor's wording, which did not
  anticipate the curve saturating at the floor before the last level.
  Recorded as failed, because that is what the letter says.
- **P2 endpoint clears the missed bar: PASS, decisively.** At OPEN,
  keys-1-2 pin 99.8% > 90.0 - the bar the gated dense2x2 HETERO cell
  missed at 76.3. The void-check holds (gating_any raw count 0 by
  construction). Removing the gating lets per-contact heterogeneity
  pin route identity at the sparse-corpus level.
- **P4 ties live where gating lives: PASS at every binding level.**
  tail_gated_any 100.0 / 98.8 / 96.4 at s0/s05/s2 (>= 90 required);
  s8 and OPEN exempt at 3 tail dispatches (< 20), and their tails are
  the collision residue, which the mechanism does not claim.
- **P5 tracking: PASS.** Spearman rho(tie_mass, gating_any) = 1.0
  across the five levels (identical rank vectors, ties in the same
  places).

**Verdict under the registered rule** (CONFIRMED requires P1, P2, P4,
P5 with P3 clean): **NOT CONFIRMED AS REGISTERED** - P1's letter
fails at the floor step. In substance the mechanism survives its
sharpest test: the refutable core (P2) passes by 9.8 points, tracking
is perfect, every tie at every binding level rides a gated route, and
the residue at the no-gating endpoint is exactly the predicted
collision class at the predicted scale. The same discipline that
caught the dense2x2 registration's mechanism gap here catches a
registration-writing defect of this sweep's own: the strict-decrease
anchor should have read "strictly decreases until it reaches zero."
Both verdicts are reported as the letters bind, not as the substance
tempts.

What this settles for the paper: the window-gating account of the
dense2x2 HETERO miss - post hoc when offered - now has a registered,
adjudicated test on its motivating mesh. What it does not settle:
generality beyond this topology family and query set (one mesh, five
fixed pairs, t0 = 120 s), and the floor-saturated P1 letter.
