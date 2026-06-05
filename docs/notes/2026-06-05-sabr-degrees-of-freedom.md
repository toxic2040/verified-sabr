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

## The pattern: deferred and contradictory degrees of freedom

The candidate-list contradiction is not an isolated drafting accident.
SABR's text repeatedly either contradicts itself or defers a
load-bearing value to an unstated operator choice, and the audit's
verdicts are conditional on all of these simultaneously:

1. **Candidate-list population**: §3.2.5.1 b) mandates completeness;
   §3.2.6.9.1 licenses ceasing computation at one candidate, with the
   cessation condition "an implementation matter." (Above.)
2. **The contact graph is declared acyclic and is not**: §3.2.1 calls
   it "a conceptual directed acyclic graph," but its edge rule d) is
   purely topological - an edge wherever one contact's receiving node
   is another's sending node, with no temporal guard - so every
   bidirectional contact pair forms a 2-cycle. The declaration is false
   on every plan in both corpora and on any network with two-way links.
   This is a flat internal contradiction, demonstrable from the text
   and any real contact plan, depending on no implementation. It now
   stands alone as 2026-06-05-sabr-acyclicity-erratum.md, with witness
   and minimal fixes, because it needs nothing else in this note.
3. **The route class is pinned three ways**: §1.4 (sequences, reuse
   permitted), §3.2.1 (the false acyclicity), §3.2.6.10 (generation by
   loopless paths). Detail in its own section below.
4. **The OWLT margin is spec text with an operator-defined value**:
   §3.2.6.5 adds "the applicable OWLT margin" to every arrival
   computation and never fixes it. ION computes it from a MAX_SPEED
   constant; a margin-0 deployment is equally conformant. Measured
   footprint on the DSN-real corpus: the margin VALUE alone moves the
   delivered arrival on 851 of 6935 dispatches (12.3%) relative to a
   margin-0 deployment (mirror-predicted, registered for the ION leg).
   Conformance below key 1 - and at key 1 itself, through arrival -
   is undefined until an ops authority pins a number the standard
   declines to fix.

One species, four instances: the standard is total and precise about
the comparison and silent or self-contradictory about the objects the
comparison ranges over.

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

The string entry order was then replaced (same day) by
shorter-string-first-then-lexicographic, which is numeric order on the
canonical decimal identifiers ingestion produces - Delta 8 resolved at
the source (algorithm.md §10.1). Field run of the rebuilt binary,
mirror predictions frozen first and confirmed 4093/4093: key-4
deviations 106 -> 1 (the survivor is closing-caused - the numerically
best entry's route is never enumerated), key-3 exactly 210 with zero
new, conformance 3882 (94.8%).

The four measured points in implementation space, all graded against
the same oracle truth on the same dispatches:

| construction                       | conformant | key-2 | key-3 | key-4 |
|------------------------------------|-----------|-------|-------|-------|
| recording binary (two-key+closing) | 2020      | 0     | 2024  | 49    |
| 4-key, string entry (+closing)     | 3777      | 0     | 210   | 106   |
| 4-key, numeric entry (+closing)    | 3882      | 0     | 210   | 1     |
| ION 4.1.4 (singleton Yen)          | 2526      | 512   | 1054  | 1     |

Each profile is a theorem of its construction; none is the standard,
and the standard's text licenses the spread. The comparator rows also
serve as a version-regression probe: every comparator change gets a
one-minute field re-run (le4field.py), so a refactor that silently
moves the conformance profile cannot pass unnoticed again.

## The irreducible residue: two witnesses, dissected

Of the 2497 equal-hop divergences, exactly 2 survive every key - both
implementations conformant, routes different. Both are CANBERRA ->
SHACKLETON dispatches at t0 = 43199 (the latest query time), both
3-hop, and they share one anatomy: same entry contact, two parallel
interior relays (plan_000720: 12->{10,3}->13; plan_000870:
1->3->{11,8}->13), arrival equal because waiting absorbs the interior
difference, and the route's minimum end time achieved on a SHARED
element - the common first contact in plan_000870 (ends 44985, against
interior legs ending 76296 and 67908) and the generator's 86400
horizon clip in plan_000720 (every leg on both routes ends exactly at
the horizon). The differing segment is strictly termination-slack.

That is the general shape of SABR's irreducible nondeterminism: the
four keys observe a route only through (arrival, length, min-end,
first hop), so any two routes that differ strictly between the first
hop and the destination, with the binding minimum outside the
differing segment, are indistinguishable to the standard. The latent
incidence on this corpus is 5 of 4093 dispatches (0.12%) with two or
more distinct routes at the full optimal tuple; 2 of the 5 realized as
cross-implementation divergence. Two consequences:

- A full-tuple tie forces an equal entry node, and 3.2.8.1.4 b)
  consumes only the entry node - so SABR's selection is
  ACTION-deterministic at every latent tie. The residue is
  representational, not behavioral, in the no-volume regime.
- Under 3.2.8.1.2 the representational choice becomes state: the MTVs
  decremented are those of the contacts in the stored route object, so
  two conformant implementations diverge in volume state exactly on
  this residue. The nondeterminism the text permits is invisible to
  the forwarded bundle and visible to the bookkeeping.

Discrimination ladder over the same corpus (which key pins route
identity, given the complete candidate list): keys 1-2 suffice on
24.6% of dispatches; 65.0% need key 3; 10.3% need key 4; 0.12% defeat
the ladder. In the integer-second cislunar regime the standard's
primary objective does a quarter of the deciding and the "tiebreak"
tail does the rest - a load profile worth knowing before treating
arrival optimality as the design's center of gravity.

## The route class is pinned three ways

Seam check on the model's no-reuse constraint: is it SABR or a
modeling choice? The text answers three times, incompatibly:

1. §1.4 defines a route as "a sequence of contacts" with chaining and
   one weak temporal condition ("the time at which contact i+1 ends
   is no earlier than the time at which contact i begins"). No
   contact-uniqueness, no node-uniqueness: reuse is permitted by the
   definition. Feasibility arrives separately (3.2.4.1.1).
2. §3.2.1 declares the contact graph "a conceptual directed acyclic
   graph" - but its edge rule d) is purely topological (an edge
   wherever one contact's receiving node is another's sending node,
   no temporal guard), so any bidirectional contact pair produces a
   2-cycle. The acyclicity declaration is false on every plan in this
   corpus and on any network with two-way links.
3. §3.2.6.10 generates routes as "the shortest path ... through the
   contact graph" (Yen) - paths are loopless by definition, so the
   generation procedure quietly produces only no-reuse routes, leaning
   on the path notion to terminate in the cyclic graph the text says
   is acyclic.

So: the model's per-route no-reuse (`expand`'s contains check) is the
§3.2.6.10 generation class, not the §1.4 route class; the grading
oracle's reuse-allowed enumeration is the §1.4 class - the
"relaxation" was the faithful reading all along. The selection-time
footprint of the difference is provably nil (at the globally minimal
arrival, any reuse-bearing chain loop-erases to a no-reuse route with
strictly fewer hops, so no reuse-bearing tuple exists at minimal hop
count). Where the class choice is NOT nil: route-list generation
(Yen's de-duplication semantics) and the T3a loop layer - node
revisits within a route remain in the model's class (only contact
repeats are excluded), and forwarding-level loops across custody
transfers are the genuinely open question, which the route-class fiat
neither creates nor settles. The §3.2.8.1 history-list NOTE concedes
loops at exactly that layer.

## The distribution swap (S5 stage A, DSN-real corpus)

Every rate above is conditioned on corpus_v3 - the cislunar generator's
plan distribution. dsn_real_v1 (dsn-scraper, build_contact_corpus.py)
re-derives the distribution-sensitive quantities on 55 day-plans built
from two months of archived DSN Now tracking data: real pass windows
under the archive's snapshot-persistence rule, real station
multiplicity (MSPA, handovers, three complexes), measured light times
(median rtlt/2 per interval, range/c fallback; OWLT 1 s to 84,725 s),
spacecraft <-> antenna <-> NOC topology with an owlt-0 terrestrial
backbone, 8912 dispatches. Results, same binary, same oracles:

- Two-sided key 1: **0 disagreements** on 6935 found and 1977 none
  dispatches. T2b and completeness hold outside the generator's world.
- The current binary is **conformant on 6935/6935** graded dispatches.
- The discrimination ladder inverts: keys 1-2 pin route identity on
  **96.3%** (corpus_v3: 24.6%), key 3 decides 0.6% (was 65.0%), key 4
  3.1% (was 10.3%), latent full-tuple indifference **0** (was 5).
- The lean le4 mirror is route-exact 6935/6935 - fifth distribution.

Verdict on the stakes question: **key 3's dominance was a regime
signature, not a property of SABR routing in general.** corpus_v3's
integer-quantized cislunar light times ({0,1} s on a 1.3-light-second
system) manufacture arrival ties, and everything below key 1 lives on
arrival ties; measured deep-space owlts make arrival decisive almost
everywhere. Neither world is wrong - integer-second quantization is
what an ionrc carries for cislunar plans, so the 65% is real for
LunaNet-class deployments - but every rate in this program is now
REGIME-INDEXED: cislunar-quantized and deep-space-real are different
worlds, and the tiebreak layer only does work in the first.

Registered for the ION leg (mirror-predicted, frozen before any ION
run; the instrument still refuses the 556 margin-binding range entries
until the margin frame is modeled): ION key-2 excess **0** (the
stale-hopCount mechanism bites only at arrival ties), key-3 28,
conformant 6056, and the 851 margin-moved arrivals above - the
complementary profiles CONVERGE on real deep-space plans, so the
differential engine's disagreement signal localizes to the
cislunar-quantized regime plus the margin axis.

Where this moves the frontier: route selection is now settled on both
distributions - mechanism-explained deviations in the regime that has
them, clean conformance in the regime that does not, and
action-determinism at every latent tie in both. The divergence that
remains live is in what implementations REMEMBER, not what they choose:
§3.2.8.1.2 volume bookkeeping, where the irreducible-residue analysis
already showed route-object identity becomes diverging MTV state. The
EVL/volume layer is the open frontier; route-selection hardening is the
settled part.

## What drives the ladder: multiplicity, not OWLT

The planned transition curve - trace the OWLT value at which the
discrimination ladder inverts, using the helio bands - came back flat
and thereby answered a better question. All four bands (250 plans
each, key-1 two-sided clean, every dispatch conformant):

| family       | owlt        | topology                  | keys 1-2 pin |
|--------------|-------------|---------------------------|--------------|
| corpus_v3    | 0-1 s       | dense 13-node lunar mesh  | 24.6%        |
| helio B0     | 0-1 s       | sparse 7-node fixture     | 99.0%        |
| helio B1-B3  | 10-3300 s   | sparse 7-node fixture     | 98.2-99.4%   |
| dsn_real_v1  | 1-84,725 s  | star, antenna multiplicity| 96.3%        |

B0 shares corpus_v3's owlt regime and shows none of its tiebreak
dominance. The load-bearing variable is arrival-tied route
MULTIPLICITY - topology density times window overlap - with owlt-0
quantization an amplifier that needs density to express. The original
pre-registered P-H1 ("tie rate collapses with OWLT scale") is
partially falsified: the collapse is topology-driven, and the OWLT
axis alone, at fixed sparse topology, does nothing. Registered for the
missing cell of the two-by-two (dense topology at large owlt), from
mechanism: HETEROGENEOUS large owlts break ties even in dense
topologies (the DSN evidence), HOMOGENEOUS large owlts preserve them -
the variable is arrival-value degeneracy across parallel routes, which
owlt-0 guarantees and equal owlts at any scale reproduce.

The design statement this licenses, named: SABR's four keys are a
fixed lexicographic order, but which key is load-bearing is a property
of the plan's multiplicity structure, which the standard never indexes
- a quarter of decisions by arrival on the dense quantized mesh,
near-all by arrival everywhere else, with the "tiebreak" tail doing
75% of the deciding in the first world and ~1-4% in the others. The
standard is written as if one priority ordering serves all regimes;
the corpora show it serves them completely differently. Arrival
primacy is not wrong - its INFORMATIVENESS is regime-contingent, and
the standard treats a collapsed objective identically to a
discriminating one. (This partially answers the key-1-primacy
question without the volume layer; whether arrival optimality
predicts delivery outcomes under contention still lives there.)

## The engine measures underspecification directly

Filed as convergence, better read as localization: across regimes,
the differential disagreement signal concentrates exactly where the
text is silent or self-contradictory. The implementation-disagreement
set and the deferred-degrees-of-freedom set are the same set,
discovered independently - profiles diverge in the quantized regime
(where the unpinned candidate list decides) and along the margin axis
(where the ops-defined value decides), and converge everywhere the
text actually specifies. Consequence for the original ION headline:
the 12.5% key-2 excess was entirely a quantized-regime phenomenon; in
deep space ION and this implementation agree, and the durable
deep-space findings are the standard's, not ION's - the margin axis
moving 12.3% of real-corpus arrivals, and the acyclicity
contradiction. Any writeup sorts accordingly: deferred degrees of
freedom as the spine, implementation deviations as the regime-indexed
appendix. The instrument generalizes: run two or more faithful
implementations across regimes and the disagreement atlas maps where
any routing standard's text does less work than it appears to.

One methodological sentence worth keeping: the audit handles the
margin by grading each implementation in its declared margin frame and
labeling cross-frame comparisons - exactly the explicitness about a
deferred parameter that the standard fails to apply to itself. The fix
is known and cheap; the instrument already practices it.

## The volume layer is a binary question

Action-determinism at every latent tie means representational residue
has exactly one path to behavioral divergence: §3.2.8.1.2 MTV
decrements against the stored route object. So the EVL/volume build is
not an open-ended layer - it answers one question: does post-selection
volume-state evolution amplify route-object divergence into different
delivery outcomes under contention, or does action-determinism keep
deliveries identical despite divergent stored state? If the latter,
the reliability question collapses to "settled, modulo the four
deferred parameters"; if the former, reliability genuinely lives in
the volume layer and the residue analysis says exactly where to look.

## Artifacts

- `scripts/diffharness/predict.py` - both mirrors, predict/score phases,
  own-list scan; mechanism citations in the header.
- `scripts/diffharness/instrument.py` (v3) - filter-c grading, thread
  bounds, per-dispatch dump, prediction cross-check.
- `scripts/diffharness/le4field.py` - 4-key binary field run and the
  version-differential scoring.
- `scripts/diffharness/s5field.py` - the distribution-swap leg over the
  DSN-real corpus; corpus builder in dsn-scraper
  (`code/build_contact_corpus.py`), output `out_s5/`.
- `out_diff_v3/predictions.jsonl`, `predictions_ownlist.jsonl`,
  `predictions_le4.jsonl` (route predictions, frozen before scoring),
  `prediction_score.json` (4093/4093 both sides), `grades.jsonl`
  (per-dispatch), `instrumentation_report.json` (aggregates, bounds,
  claim checks), `le4_results.jsonl` + `le4_field_report.json` (the
  rebuilt binary's field run).
