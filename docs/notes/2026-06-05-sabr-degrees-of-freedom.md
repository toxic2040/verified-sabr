# Finding: SABR's best-route order is total; its domain is the standard's open degree of freedom

Status: measured 2026-06-05 over corpus_v3 (4093 dispatches, 1000 plans);
every number below is reproducible from artifacts in `out_diff_v3/` via
`scripts/diffharness/predict.py` and `scripts/diffharness/instrument.py`.
This note states the finding the conformance audit was converging on,
locates it in the standard's text at clause level, and closes the two
open caveats the audit carried (the quantifier reading and the thread
ambiguities).

## The finding

Two independently developed implementations of SABR route selection -
deployed ION 4.1.4 and this repository's search - disagree on which route
wins in 2497 of 4093 dispatches at equal hop count, in complementary and
now mechanism-predicted ways, while both implement CCSDS 734.3-B-1
§3.2.8.1.4 a)'s comparison faithfully or near-faithfully. Neither
implementation is wrong about the order. They differ about the *list*
the order ranges over, and the standard pins that list twice,
incompatibly:

- §3.2.5.1 b): the candidate routes list "shall contain one entry for
  each candidate route ..., that is, for each route that could result in
  arrival of the bundle at node D." A completeness clause.
- §3.2.6.9.1: "As long as the route list contains no candidate routes,"
  the next best route shall be computed and added - and "identification
  of the conditions under which the computing of additional routes must
  cease is an implementation matter." A cessation license, with
  §3.2.6.10 pinning the generation order (Yen-style, next-best by
  arrival time only).

An implementation that stops computing routes the moment one candidate
exists satisfies §3.2.6.9.1 literally and presents §3.2.8.1.4 with a
singleton list, making keys 2-4 vacuous. An implementation graded
against §3.2.5.1 b)'s complete list answers for every route that could
deliver. The entire measured deviation profile of ION is the swing
between these two clauses; the deviation profile of this repository's
recording binary survives every reading, including the one most
favorable to it. Below key 1, SABR conformance is undefined until the
reader chooses a clause.

## Mechanism accounts (both mirrors route-exact, 4093/4093)

`predict.py` reimplements each construction from source and predicts
each implementation's returned route per dispatch from nothing but the
contact plan and the dispatch instant. Both mirrors reproduce the
recorded route on all 4093 dispatches (`prediction_score.json`;
predictions frozen before scoring, sha256 in the run log).

**ION 4.1.4** (`bpv7/cgr/libcgr.c`): in the unloaded regime the Yen
registry never iterates - `loadBestRoutesList` stops when one candidate
exists at the end of the walk, and the first route always passes. Every
cgrfetch capture in the corpus contains exactly one route. The returned
route is the single first Dijkstra route of `computeDistanceToTerminus`:

- relaxation is strict `<` on best-case arrival only, so an
  equal-arrival path never updates a work area: predecessor and hop
  count keep the first strict improver's values (hop counts on work
  areas are history artifacts, not minima);
- the next current contact is chosen by (arrivalTime, hopCount) over
  those stale counts, ties to the earliest contact in index order
  (region, from node, to node, start time);
- the search stops at the first popped contact that delivers to the
  terminus.

Spec keys in that mechanism: key 1 holds globally (sound earliest-arrival
Dijkstra; confirmed two-sided by the key-1 oracle). Key 2 is attempted
at pop time over stale counts - the 512 key-2 excesses are exactly where
that approximation bites. Key 3 is never consulted anywhere; ION's
relative key-3 strength is emergent. Key 4 is never consulted; the
index-order tie-break biases toward small node numbers, which is why ION
shows a single key-4 deviation. `tryRoute`'s comparator transcribes keys
1-4 verbatim (delivery time, fewest hops, latest termination, smallest
entry node) - it just never sees a second candidate.

OWLT margin note for the helio corpus: ION adds
`(MAX_SPEED_MPH/3600)*owlt/186282` seconds of margin in integer
arithmetic. This is 0 for owlt <= 1490 s (all of corpus_v3) and nonzero
from 1491 s - the B2/B3 helio bands will diverge from the lean arrival
function unless the margin is modeled.

**Recording binary** (66948c9): the routes the audit graded were
produced by the binary built 06-03 23:33 (diff_results.jsonl written
06-04 02:18), which predates the full 4-key `pickMin` (3e4d2a0, 06-04
13:38). That binary's comparator is two-key - (arrival, hop count),
leftmost frontier element on full ties - with keys 3-4 absent.
Everything below key 2 in the recorded data is resolved by frontier
order: expansions are prepended in contact-plan file order, so relative
order reverses between expansion generations, and the visited list gates
which candidates exist at all. The field behavior of the current
source's 4-key comparator is not yet measured (see the registered
predictions below).

## Decomposition of the recorded deviations

Joining the per-dispatch grades (`grades.jsonl`) with the mirror's
own-list scan (`predictions_ownlist.jsonl`):

- lean key-3 deviations, 2024 total = **1841 comparator-caused** (the
  spec-better route was in the frontier at return; the two-key
  comparator never consulted termination) + **183 closing-caused** (the
  spec-better route was never enumerated; the visited list killed its
  prefix). The visited list's measured field price at key 3 is 183
  dispatches, not 2024.
- lean key-4 deviations, 49 total = 49 comparator-caused, 0
  closing-caused. The audit's earlier attribution of these to the le4
  string order was wrong for the recorded data - the recording
  comparator had no entry key at all. The {10,11,12}-over-{2,8} pattern
  is frontier-order emergence (prepend-reversal of the plan file's
  numeric to-node order); the dominating smaller-entry candidate was
  present in the frontier every time. The string-order mechanism is
  real in the current source (pinned by SearchTests) but is not what
  produced these 49 data points.
- Sanity: zero dispatches are globally conformant yet own-list
  dominated, and 1841 + 49 = 1890, the own-list domination count.

ION's 512 key-2 excesses and the 3009 hop-sequence divergences need no
further cause: with both constructions route-exact under the mirrors,
every deviation is a theorem of its construction.

## Closing the quantifier caveat

The audit carried the caveat that §3.2.8.1.4 quantifies over an unpinned
candidate list. Closure, by exhaustion over the readings the text
supports:

1. **Complete-list reading** (§3.2.5.1 b) with §3.2.6.9's filters): the
   graded basis. The one filter the v2 oracle had not applied -
   §3.2.6.9 c), no route containing a contact back to the forwarding
   node - changes the graded optimum on **0 of 4093** dispatches
   (measured, `filter_c_changed_sopt`). Grades on this reading: lean
   2020 conformant / 0 key-2 / 2024 key-3 / 49 key-4; ION 2526 / 512 /
   1054 / 1 (after thread resolution, below).
2. **Loopless-route reading**: "route" read as a simple path (the
   §3.2.6.10 Yen framing). Invariant by derivation: at the globally
   minimal arrival (key-1 oracle, two-sided), any contact-reusing chain
   loop-erases to a no-reuse route with the same arrival and strictly
   fewer hops, so no reuse-bearing tuple exists at minimal hop count,
   and keys 3-4 compare only at minimal hop count. The reuse-allowed
   and loopless universes grade identically.
3. **Per-neighbor reading** (§3.2.8.1.1's best-candidate-per-neighbor
   construed as the list): the keys-1-4 global optimum is also its own
   neighbor's best, so selection over per-neighbor bests returns the
   same tuple. Collapses to reading 1.
4. **Cessation reading** (§3.2.6.9.1 + §3.2.6.10): ION's
   `loadBestRoutesList` is a literal transcription of this clause; the
   singleton list is the text's own licensed minimal behavior, under
   which ION is conformant by construction and its whole 512/1054/1
   profile vanishes. The recording binary's generator (best-first
   search with a visited list) is not the prescribed Yen generation, so
   this reading does not rescue it - it judges generators, not
   selections.
5. **Own-list reading** (weakest: the list is whatever the
   implementation enumerated): ION trivially conformant (singleton).
   The recording binary still returns a route dominated at keys 3-4 by
   a candidate in its own frontier on **1890 of 4093** dispatches
   (measured; dst-candidates are never dropped, so the frontier at
   return is the full enumerated list).

So the deviation verdicts are not artifacts of a candidate-list choice:
lean's deviations persist under every reading including its own list;
ION's deviations exist exactly insofar as §3.2.5.1 b) outranks
§3.2.6.9.1. The clause-level contradiction is the finding, and the
512/1054/1-to-zero swing is its measured size.

## Closing the thread ambiguities

ION's recorded hops are (from, to) pairs; window identity is threaded
over the plan. Hop count and entry node are thread-invariant, so of the
217 multi-window dispatches the v2 audit excluded, only **85** can swing
their grade at all (the other 132 grade identically under every
resolution and are now graded: +3 key-2, +129 key-3). Bounds across all
resolutions of the 85: ION key-3 in [969, 1054], conformant in [2526,
2589], key-4 in [1, 23]. At the extreme least favorable to the
complementary-profile claim, ION key-3 (1054) remains under half of
lean's 2024 and ION conformant (2526) exceeds lean's 2020
(`claim_checks` in the report: both true). The exclusion was never
load-bearing. The ION mirror then resolves all 85 by mechanism - its
window choices are consistent threads on 4093/4093 - and every one
lands on key-3 deviation: ION's mechanism-resolved profile is 2526 /
512 / 1054 / 1.

## Near-totality below key 1

Of the 2497 equal-hop divergences, 2463 carry a determinate grade
structure (34 sit inside the 85 grade-ambiguous): 1691 lean-deviates,
614 ION-deviates, 156 both, and exactly **2** where both routes are
§3.2.8.1.4-equivalent through key 4 - the only dispatches where the
standard itself is indifferent (and §3.2.8.1.4 b) consumes only the
entry node, making sub-key-4 divergence forwarding-equivalent). SABR's
order is near-total in the field: the residual nondeterminism across
implementations is realized by list construction, not licensed by the
comparison.

## Decidability covers the degenerate regime

The key-1 oracle's completeness comes from monotone relaxation over the
finite lattice of expressible arrival times - a proof over the unbounded
route class, not a sample - and it does not require positive OWLT. It
therefore covers the owlt-0 regime, which is 73.1% of corpus range
entries and the regime where nearly all ties live. Consequences: the
tie space above key 1 is finite and decidable exactly where the data
is; the 1691 lean-deviating equal-hop ties are a measured sample of
that space; and the T3a tie-resolution question over keys 3-4 is
decidable in the degenerate regime without a positive-OWLT hypothesis.

## The version differential, measured

Predictions registered before the run (P-V1: the le4 mirror predicts
the rebuilt binary's route per dispatch; P-V2: key-3 deviations
collapse to roughly the closing-caused population, membership predicted
exactly by the mirror; P-V3: key-4 deviations become genuinely
string-order-caused and nonzero). The binary was rebuilt from current
source and run over all 4093 dispatches (`le4field.py`; mirror
predictions frozen first, sha256 in the run log). Results:

- P-V1 confirmed: mirror route-exact 4093/4093 against the binary.
  Three constructions, three route-exact mirrors.
- P-V2 confirmed: key-3 deviations 2024 -> **210**, zero new - the
  4-key comparator eliminates every comparator-caused deviation, and
  the surviving 210 (the closing-caused set under the new pop order;
  183 under the old) all lie inside the old deviant population. The
  visited list's true key-3 price in the field is 210 dispatches.
- P-V3 confirmed, with a sharper edge: key-4 deviations 49 -> **106**.
  All 49 old cases persist (on that subpopulation frontier order and
  string order pick the same entry, which is why the old data could
  not distinguish the mechanisms), and **57 new** cases appear where
  the string order actively selects the digit-length-wrong entry that
  frontier order had gotten right. Every sampled case is digit-length
  (entries {10,11,12} vs spec {2,3,8}). Delta-8 is now a field
  mechanism, not just a source property.
- Conformant 2020 -> 3777 (92.3%); key-2 excess stays 0.

The three measured points in implementation space, all graded against
the same oracle truth on the same dispatches:

| construction                      | conformant | key-2 | key-3 | key-4 |
|-----------------------------------|-----------|-------|-------|-------|
| recording binary (two-key+closing)| 2020      | 0     | 2024  | 49    |
| current source (4-key str+closing)| 3777      | 0     | 210   | 106   |
| ION 4.1.4 (singleton Yen)         | 2526      | 512   | 1054  | 1     |

Each profile is a theorem of its construction; none is the standard,
and the standard's text licenses the spread.

## Artifacts

- `scripts/diffharness/predict.py` - both mirrors, predict/score phases,
  own-list scan; mechanism citations in the header.
- `scripts/diffharness/instrument.py` (v3) - filter-c grading, thread
  bounds, per-dispatch dump, prediction cross-check.
- `scripts/diffharness/le4field.py` - 4-key binary field run and the
  version-differential scoring.
- `out_diff_v3/predictions.jsonl`, `predictions_ownlist.jsonl`,
  `predictions_le4.jsonl` (route predictions, frozen before scoring),
  `prediction_score.json` (4093/4093 both sides), `grades.jsonl`
  (per-dispatch), `instrumentation_report.json` (aggregates, bounds,
  claim checks), `le4_results.jsonl` + `le4_field_report.json` (the
  rebuilt binary's field run).
