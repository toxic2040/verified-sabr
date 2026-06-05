# What Schedule-Aware Bundle Routing pins down, and what it defers: a regime-indexed characterization of CCSDS 734.3-B-1

J. Councilman — draft v0.1, 2026-06-05. Working copy; every number in
this draft is reproducible from the repository's committed harness and
the corpora described in §2.

## Abstract

We set out to certify the reliability of SABR route selection (CCSDS
734.3-B-1) with a machine-checked reference implementation, an
independent-oracle conformance audit, and differential measurement
against deployed ION 4.1.4. The certification question dissolved under
the instrument, and what replaced it is a closure claim about the
standard itself: we enumerate the complete set of places where two
conformant SABR implementations can differ in behavior, and there are
four, all in the text - the population of the candidate-routes list
(mandated complete in one clause, permitted singleton in another), the
OWLT margin value (normative arithmetic, operator-chosen value, moving
delivered arrival on 12.3% of a real Deep Space Network corpus), the
route class (pinned three incompatible ways), and the contact graph's
declared acyclicity (false under its own construction rule on any
bidirectional plan). Everything else is pinned: selection is
action-deterministic at every tie the text cannot break (a full
four-key tie forces the same forwarding action), and the one remaining
channel from stored-state divergence to behavior - volume bookkeeping
against the stored route object - is real in principle and inert on
physical traffic. We construct a witness in which two conformant
systems disagree on whether a bundle is deliverable at all, then show
in a two-ledger replay rigged in amplification's favor (contention to
eight times the tightest pass volume, charges that never decay) that
the divergence never fires on naturally shaped traffic, for a
structural reason: the route multiplicity that creates divergent state
is the same multiplicity that supplies the tuple-equivalent fallbacks
absorbing it. Along the way we show that which of the standard's four
selection keys does the deciding is a property of the contact plan's
route multiplicity - the "tiebreak" tail decides 75% of dispatches on
a quantized cislunar mesh and 1-4% everywhere else, flat across three
orders of magnitude of light time - a regime dependence the standard
never indexes. Fix the four deferred points and two faithful
implementations of this standard are behaviorally identical on
physical traffic, in selection and delivery, from cislunar to
interplanetary range. The reliability risk was never in the
implementations; it is exactly where the text stops speaking.

## 1. Introduction

Schedule-Aware Bundle Routing is the CCSDS recommended standard for
routing over scheduled contacts in delay-tolerant networks. Its core
is a best-route selection: among candidate routes to a destination,
choose by earliest projected arrival, then fewest contacts, then
latest termination time, then smallest entry node number
(§3.2.8.1.4 a). The order is total, the text is precise about it, and
implementations of it fly.

This work began as a certification program: formalize the selection in
Lean 4, prove soundness and optimality, and use the verified artifact
to audit a deployed implementation. The program kept producing a
different kind of result. Each time a deviation surfaced, mechanism
tracing moved the cause out of the implementation under test and into
either the measurement frame or the standard's text, until the
original question - is the routing reliable - stopped being open at
the routing layer and the remaining variation was accounted for by
choices the standard explicitly or implicitly leaves to others. The
durable findings are about the text and about how its effective
behavior changes across operating regimes, not about whether any
particular implementation has a bug.

The thesis is a closure claim. The four deferred points of §4 are not
four caveats on a reliability finding; on the evidence of §5-§7 they
are the complete set of behavioral degrees of freedom the standard
leaves open. The witness of §7 is the necessity half of that claim -
it exhibits the one further channel the text permits, divergence
through volume state, as real - and the field measurement is the
inertness half: on physical traffic the channel never fires, for a
mechanism-level reason. Fix the four and two conformant
implementations are behaviorally identical on natural traffic, in
selection and in delivery, across the measured OWLT range.

Concretely, this paper establishes:

- **A four-member class of deferred or contradictory degrees of
  freedom in the text, argued complete** (§4, §5, §7): the
  candidate-list population is mandated complete in one clause and
  permitted singleton in another; the OWLT margin is part of the
  normative arrival computation with its value left to operations; the
  route class is pinned three incompatible ways; and the contact graph
  is declared acyclic while its construction rule produces 2-cycles on
  every bidirectional plan. Conformance verdicts below the first key
  are undefined until a reader resolves all four - and no measured
  disagreement traces to anything outside them.
- **A localization result** (§5): run two independently developed,
  faithful implementations across regimes and their disagreement
  concentrates exactly on that class. The differential is an
  instrument that measures textual underspecification directly.
- **A regime field** (§6): which key of the fixed lexicographic order
  is load-bearing is determined by the plan's arrival-tied route
  multiplicity. We anchor the field at three measured families -
  a quantized cislunar mesh, a sparse heliocentric fixture swept from
  0 to 3300 s OWLT, and contact plans built from two months of real
  DSN tracking - and show the driver is multiplicity, not OWLT:
  arrival decides 24.6% of route identity on the first family and
  96-99% on the others, flat across three orders of magnitude of
  light time.
- **An irreducible-residue anatomy and a determinism theorem-pair**
  (§6.2): the standard's order observes a route only through (arrival,
  length, minimum end time, first hop); two routes differing strictly
  between the first hop and the destination, with the binding minimum
  outside the differing segment, are indistinguishable to it. The
  realized incidence is 2 of 4093 dispatches; both are invisible to
  the forwarding action, because a full tie forces the same entry
  node. Selection is therefore action-deterministic at every tie the
  text cannot break.
- **The volume layer's two-sided answer** (§7): action-determinism
  leaves exactly one path from stored-route divergence to behavioral
  divergence - MTV decrements under §3.2.8.1.2. The witness shows the
  path is real: two conformant systems disagree on deliverability. The
  replay, with every knob set in amplification's favor, shows it is
  inert on natural traffic, and both enumeration-cap exposures are
  closed structurally rather than by sampling. Permitted but inert,
  with the mechanism for the inertness - the pair, not either half, is
  the result.

The methods that make these claims auditable are themselves a
contribution (§2-3): a kernel-checked reference whose theorems are
treated as falsifiable hypotheses inside strictly larger oracle
frames; route-exact mechanism mirrors of every implementation
generation measured (four constructions, exact on 4093/4093 dispatches
each, then revalidated on two further corpora); pre-registered
predictions with frozen artifacts; and a provenance discipline that,
on two occasions, falsified a plausible causal story - once our own,
once an external reviewer's - by showing the proposed mechanism was
not present in the binary that produced the data.

## 2. The instrument

### 2.1 Formal core

The reference implements §3.2.8.1.4 selection as a best-first search
over contact chains with the deployed-practice visited-contact list.
Kernel-checked results (Lean 4, zero `sorry`): returned routes are
valid (T1); the selected candidate is minimal in the full four-key
order over the frontier (T2a); on plans with nonnegative OWLT the
returned arrival is globally optimal over the unbounded route class,
contact-reusing competitors included, by a loop-erasure argument
(T2b); and the search returns `none` exactly when no valid route
exists (completeness). The nonnegative-OWLT hypothesis is load-bearing
and witnessed: with a negative OWLT, T2b is false.

The formal results deliberately stop at key 1 globality: keys 2-4 are
correct over the explored frontier, and what reaches the frontier is
decided by the visited list. That gap is not papered over; it is where
the field measurement starts.

### 2.2 Oracles, with the frame-relaxation principle

Theorems proved inside a model bind only the model. The audit
therefore grades both the reference and ION against oracles whose
assumptions strictly relax the reference's frame, so its theorems sit
inside the oracle's search space as falsifiable hypotheses:

- **Key-1 oracle**: time-dependent label correction over node states.
  No route objects, no visited list, reuse irrelevant by construction;
  complete over the unbounded class because monotone relaxation on the
  finite lattice of expressible arrivals terminates with no depth cap
  and no positive-OWLT requirement. It is two-sided: it can refute a
  recorded optimum, and when it agrees it confirms one. It agreed on
  all 4093 + 6935 + 5016 dispatches across the three corpus families,
  found and none alike.
- **Grading oracle**: exhaustive chain enumeration with contact reuse
  permitted, depth-capped by the returned routes' own hop counts -
  self-bounding, because every graded question (minimal hops at the
  optimal arrival; latest termination and smallest entry at minimal
  hops) lives at depths no greater than the returned routes'. Reuse
  permission turned out to be the faithful reading of the text's own
  route definition (§4.3); at the graded optimum it is provably
  inert - at the globally minimal arrival, any reuse-bearing chain
  loop-erases to a no-reuse route with strictly fewer hops, so no
  reuse-bearing tuple exists at minimal hop count.

### 2.3 Route-exact mechanism mirrors

Counts convince no one; mechanisms predict. For every implementation
generation measured, we reimplemented its construction from source and
predicted its returned route per dispatch from nothing but the contact
plan and the dispatch instant, freezing predictions before scoring:

- ION 4.1.4's route construction (§A.1): exact on 4093/4093, including
  window-level resolution of all 217 dispatches whose recorded hop
  pairs were thread-ambiguous.
- The recording-era reference binary (two-key comparator): 4093/4093.
- The current reference, string entry order: 4093/4093 against a
  rebuilt binary.
- The current reference, numeric entry order: 4093/4093 against a
  rebuilt binary; revalidated route-exact on the DSN corpus
  (6935/6935).

Route identity implies grade identity, so every deviation count in
this paper is a theorem of a construction, not a statistic about one.

### 2.4 Corpora

- **corpus_v3** (cislunar-quantized): 1000 generated LunaNet-style
  plans, 13 nodes, ~398 contacts each, integer-second light times -
  73.1% of range entries are 0 s, because the Earth-Moon system spans
  1.3 light-seconds and the ionrc format quantizes to seconds. 4093
  found dispatches.
- **helio_regime_v1** (sparse fixture, OWLT-swept): four bands of 250
  plans (0-1 / 10-60 / 180-1320 / 1980-3300 s OWLT), fixed 7-node
  topology. 5016 dispatches.
- **dsn_real_v1** (deep-space-real): 55 day-plans reconstructed from
  two months of archived DSN Now tracking snapshots - real pass
  windows, real station multiplicity across the three complexes,
  per-interval median measured light times from 1 s (lunar) to
  84,725 s (Voyager 1), spacecraft-antenna-NOC topology over an
  always-on terrestrial backbone. 8912 dispatches (6935 found, 1977
  none, both verdicts oracle-confirmed two-sided).

### 2.5 The cap-killing technique

A recurring move deserves its name, because four results in this
paper rest on it: when a result depends on a bound, find the
monotonicity that makes the bound conservative, and the bound stops
being a caveat. The key-1 oracle is complete over the unbounded route
class because monotone relaxation on the finite lattice of expressible
arrivals terminates with no depth cap (and no positive-OWLT
hypothesis, which is what makes it cover the quantized regime where
the data lives). The grading oracle's depth cap is self-bounding
because every graded question lives at depths no greater than the
returned routes'. The volume replay's found/none adjudication is
closed because found-verdicts are monotone in enumeration depth. And
its entry-divergence exposure is closed because the depth-free oracle
bounds what any deeper route could achieve at key 1 (§7). In each
case the bounded computation plus the monotonicity argument yields an
unbounded conclusion.

### 2.6 Provenance discipline, with a worked example

Recorded artifacts carry the algorithm of the binary that produced
them, not of the source tree at analysis time. The audit's recorded
routes were produced by a binary that predates the reference's
four-key comparator: its selection was (arrival, hop count) only, with
everything below key 2 resolved by frontier order. That provenance
fact, established from binary timestamps against commit history,
falsified two causal attributions in succession. First our own: 49
key-4 deviations had been attributed to the comparator's
string-versus-numeric entry order, but the recording comparator had no
entry key at all - the pattern was frontier-order emergence, and the
attribution had "landed" for the wrong reason. Then an external
reviewer's: a red-team review asserted those 49 cases were the
measurable footprint of the string-order defect; the same provenance
shows the mechanism was absent from the binary that produced the data.
The string order's real footprint, measured later against a rebuilt
binary, is 106 dispatches; after replacing it with numeric order
(shorter-decimal-first, equal to numeric on canonical identifiers),
exactly 1 remains, and that one is closing-caused. An instrument that
can falsify its own author's attribution and a hostile reviewer's with
the same move is measuring something other than its authors'
expectations.

## 3. What the audit measured, regime-indexed

Grades are against the strong reading of the text (§4.1) at the
recorded optimal arrival, on the §3.2.6.9-filtered universe; the
back-to-the-forwarding-node filter changes zero graded optima on these
corpora, and route-level violations of it are zero in both
implementations.

Four constructions, one oracle truth, corpus_v3
(conformant / key-2 excess / key-3 / key-4 of 4093):

| construction                        | conf. | k2  | k3   | k4  |
|-------------------------------------|-------|-----|------|-----|
| reference, recording binary (2-key) | 2020  | 0   | 2024 | 49  |
| reference, 4-key, string entry      | 3777  | 0   | 210  | 106 |
| reference, 4-key, numeric entry     | 3882  | 0   | 210  | 1   |
| ION 4.1.4                           | 2526  | 512 | 1054 | 1   |

Mechanism decompositions (§A): the recording binary's 2024 key-3
deviations split 1841 comparator-caused (the spec-better route was in
the frontier; the two-key comparator never consulted termination)
against 183 closing-caused (the visited list killed the better
route's prefix); the four-key comparator eliminates every
comparator-caused case and leaves 210 closing-caused ones, with zero
new. ION's 512 key-2 excesses are the first-Dijkstra construction's
stale hop counts at arrival ties; its key-3 strength and single key-4
deviation are emergent, since its single-route construction never
consults either key (§A.1).

On dsn_real_v1 the current reference is conformant on 6935/6935.
ION's registered profile (mirror-predicted, frozen, awaiting live
validation), graded in ION's declared margin frame with the oracles
margined identically: key-1 confirmed two-sided in frame on all 8912
dispatches; 6905 conformant, key-2 excess 0, key-3 30, key-4 0 -
99.6% conformant in its own frame. The complementary profiles of the
quantized regime converge on real deep-space plans; what remains on
the margin axis is the value footprint of §4.2, kept cross-frame and
labeled. On the helio bands the reference is conformant on all 5016.

The table also functions as a version-regression probe: each
comparator change is a one-minute field re-run, and the stability of
the key-3 column across the last two rows while key-4 collapsed
106 to 1 is direct evidence the entry-order fix was surgical.

## 4. The standard's deferred degrees of freedom

SABR's text is total and precise about its comparison and silent or
self-contradictory about the objects the comparison ranges over. Four
instances, one species.

### 4.1 The candidate list is mandated complete and permitted singleton

§3.2.5.1 b): the candidate routes list "shall contain one entry for
each candidate route ..., that is, for each route that could result in
arrival of the bundle at node D." §3.2.6.9.1: "As long as the route
list contains no candidate routes," the next best route shall be
computed and added - and "identification of the conditions under which
the computing of additional routes must cease is an implementation
matter," with §3.2.6.10 fixing the generation order (next-best by
arrival, Yen's algorithm suggested). An implementation that stops at
the first candidate satisfies the second clause literally and presents
the four-key selection with a singleton list, making keys 2-4 vacuous.
ION 4.1.4 is that implementation: in the unloaded regime its
route-list machinery never iterates (every captured computation in
1000 plans contains exactly one route), and its faithful transcription
of the four keys ranges over that singleton. ION's entire deviation
profile above - 512/1054/1 - is the swing between the two clauses, and
under the cessation reading it is zero. The reference's deviations,
by contrast, survive every reading, including the weakest (graded
against its own enumerated frontier, it returns a dominated route on
1890/4093 dispatches under the recording comparator).

### 4.2 The OWLT margin is normative text with an operator value

§3.2.6.5-6 add "the applicable OWLT margin" to every arrival
computation and never fix it. ION computes it from a configured
maximum spacecraft speed; a margin-zero deployment is equally
conformant. On the real-DSN corpus the margin value alone moves the
delivered arrival on 851 of 6935 dispatches (12.3%) relative to a
margin-zero deployment. This is the sharpest deferred parameter
because it is regime-relevant exactly where interplanetary operations
live: conformance at key 1 itself - arrival - is undefined on one
dispatch in eight of a real deep-space corpus until an authority
outside the standard picks a number. Our handling is to grade each
implementation in its declared margin frame and label cross-frame
comparisons; the discipline costs one sentence per table and is
available to the standard itself.

### 4.3 The route class is pinned three incompatible ways

§1.4 defines a route as a sequence of contacts with chaining and one
weak temporal condition (contact i+1 ends no earlier than contact i
begins) - contact reuse and node revisits permitted. §3.2.1 declares
the contact graph acyclic (it is not; §4.4). §3.2.6.10 generates
routes as shortest paths through that graph - loopless by the
definition of path, so generated routes never reuse a contact. The
generation class is strictly narrower than the defined class, and
implementations necessarily follow the generation clause. At the
selection optimum the narrowing is provably invisible (the
loop-erasure argument of §2.2); in route-list generation semantics and
in any forwarding-loop analysis it is not, and the standard's own
§3.2.8.1 NOTE concedes loops at the forwarding layer.

### 4.4 The contact graph is declared acyclic and its construction is not

§3.2.1 defines the contact graph as "a conceptual directed acyclic
graph" whose edge rule d) places an edge wherever one contact's
receiving node is another's sending node - purely topological, no
temporal condition. For any bidirectional pair A->B, B->A, rule d)
yields edges in both directions: a 2-cycle. The declaration is false
on every plan in all three corpora and on any network with a two-way
link; the witness is two lines of any real contact plan. The
consequence threads back through §4.3: the generation procedure leans
on path-ness to terminate in a graph the text wrongly promises is
acyclic. Two one-line fixes are available (add the temporal guard the
prose assumes, or delete "acyclic" and state the loopless restriction
where §3.2.6.10 relies on it). This is the body of work's most
referee-proof sentence: it depends on the text and a two-line witness,
and on nothing else. It is maintained as a standalone erratum suitable
for the standards process.

## 5. The localization result

The four instances above were found by reading. Independently, the
differential measurement finds the same set: across regimes, the
disagreement between faithful implementations concentrates on exactly
those axes. In the quantized regime, where arrival ties are pervasive,
implementations disagree wherever the unpinned candidate list decides
(the complementary profiles of §3); on real deep-space plans the
profiles converge and the remaining behavioral freedom is the margin
axis (12.3% of arrivals) plus nothing. We found no disagreement, in
288,000 volume-replay evaluations and 18,000 audited dispatches, that
traces to anything other than a deferred degree of freedom or a
since-fixed implementation defect with a named mechanism.

That is a property worth stating as a method: a differential
conformance engine - two or more faithful implementations, mechanism
mirrors, regime-spanning corpora - measures where a standard's text
does less work than it appears to, and its output coincides with the
text's deferred choices. It generalizes to any routing standard with
multiple implementations.

## 6. The regime field

### 6.1 Which key decides is a plan property

For each dispatch, ask which key of §3.2.8.1.4 pins route identity,
given the complete candidate list:

| family       | OWLT        | topology                   | keys 1-2 | key 3 | key 4 | none |
|--------------|-------------|----------------------------|----------|-------|-------|------|
| corpus_v3    | 0-1 s       | dense 13-node mesh         | 24.6%    | 65.0% | 10.3% | 0.12% |
| helio B0     | 0-1 s       | sparse 7-node fixture      | 99.0%    | 0.9%  | 0.0%  | 0.1% |
| helio B1-B3  | 10-3300 s   | sparse 7-node fixture      | 98.2-99.4% | 0.6-1.4% | 0.0% | 0-0.3% |
| dsn_real_v1  | 1-84,725 s  | star, antenna multiplicity | 96.3%    | 0.6%  | 3.1%  | 0%   |

The sweep was designed to trace a transition along the OWLT axis and
instead falsified the axis: band B0 shares corpus_v3's light-time
regime and shows none of its tiebreak load. The driver is arrival-tied
route MULTIPLICITY - topology density times window overlap - with
zero-OWLT quantization an amplifier that needs density to express. (A
pre-registered prediction of the original sweep plan, that tie rate
collapses with OWLT scale, is thereby partially falsified; the
registered prediction for the unmeasured dense-topology, large-OWLT
cell is that heterogeneous light times break ties and homogeneous ones
preserve them, the variable being arrival-value degeneracy across
parallel routes.)

The design statement this licenses: SABR's four keys are a fixed
lexicographic order, but which key is load-bearing is a property of
the plan, which the standard never indexes. On the dense quantized
mesh the standard's primary objective does a quarter of the deciding
and the "tiebreak" tail does three quarters; everywhere else arrival
does nearly all of it. Arrival primacy is not wrong; its
informativeness is regime-contingent, and the text treats a collapsed
objective identically to a discriminating one. A standard intending
one behavior across regimes would need either a regime-aware order or
a finer arrival representation where quantization collapses key 1.
SABR has neither.

### 6.2 Near-totality and the irreducible residue

Of 2497 equal-hop route disagreements between the two implementations
on corpus_v3, 2463 carry a determinate grade structure and exactly 2
are choices the standard itself permits - dispatches where both
returned routes are §3.2.8.1.4-equivalent through key 4 yet differ as
routes. Latently, 5 of 4093 dispatches admit two or more distinct
routes at the full optimal tuple. Both realized witnesses share one
anatomy: same entry contact, two parallel interior relays, arrival
equalized by waiting, and the route-minimum end time achieved on a
SHARED element (the common first contact in one; the day-horizon clip
in the other), so the differing segment is strictly termination-slack.
That is the general shape of what the order cannot see: it observes a
route only through (arrival, length, min-end, first hop).

Two corollaries. A full-tuple tie forces an equal entry node, and
§3.2.8.1.4 b) consumes only the entry node - so selection is
ACTION-deterministic at every tie the text cannot break; the residue
is representational. And under §3.2.8.1.2 the representation is
charged: the MTVs decremented are those of the stored route object's
contacts, so the residue becomes diverging volume state. Which is the
volume layer's question.

## 7. The volume layer: wash-out, with a witness

Action-determinism leaves exactly one path from representational
divergence to behavioral divergence. Queue backlog cannot carry it
(identical actions produce identical queues), and the four keys never
read MTV; the ledger reaches selection only through the §3.2.6.9 f)/g)
volume filters. The question is binary: does MTV evolution amplify the
residue into different selections - different entry, or found against
none - for some later bundle, or does action-determinism wash it out?

**Amplification is a theorem.** Witness: two tuple-equal routes
through a shared entry contact; one bundle charges the term-slack legs
divergently (each conformant system charges the route object it
stored); a second bundle sourced on a leg, sized between the charged
and uncharged remaining volume, is routable under one ledger and
unroutable under the other. Two systems, both conformant at every
step, disagree on deliverability.

**The field washes out, under conditions rigged against wash-out.**
The experiment turns every knob in amplification's favor: contention
to eight times the tightest pass volume, charges that never decay
(route expiry could only reduce amplification), ledgers charged along
the two EXTREME conformant resolutions of every tuple-tie class
(canonical minimum and maximum, bracketing every faithful
implementation pair), and full volume semantics - last-byte threading
per §3.2.6.3-7, successor-clipped effective stops and MTV/EVL/RVL per
§3.2.6.8, the no-fragmentation filters per §3.2.6.9 f)/g), §1.4
overhead. Under those conditions, on corpus_v3 at contention 2.0:
2 residue events, both washed out. At contention 8.0: 26 plans carry
44 residue events under depth-4 adjudication, and every action stream
is identical end to end. On dsn_real_v1: zero residue events at all -
no ties, nothing to store divergently, the channel closed upstream by
the regime. The divergence the standard permits did not occur on
naturally shaped traffic under stress exceeding any realistic
deployment, and the reason is structural, not statistical: the
multiplicity that creates residue is the same multiplicity that
supplies tuple-equivalent fallbacks to absorb it, and endpoint
traffic does not produce the witness geometry (a leg-sourced bundle
aimed into a charge gap).

**Both enumeration-cap exposures are closed by argument.** The replay
enumerates candidates to a depth cap, truncations counted, which
exposes two artifact channels; both are closed structurally. A
found/none divergence whose "none" side truncated could be a cap
artifact - the single depth-3 candidate was exactly that, its none
side holding a live four-hop fallback - and found-verdicts are
monotone in enumeration depth, so once adjudication at depth 4 shows
both sides routing, that divergence type cannot reappear at any
depth. An entry divergence could in principle hide above the cap (a
deeper route, earlier in projected arrival, live under one ledger
only); but the key-1 oracle is depth-free, so on a uniform-rate plan
the volume-unconstrained optimal PBAT is computable without any cap,
and a dispatch whose selections already sit at that optimum cannot be
beaten at key 1 by any deeper route, while deeper routes lose key 2
at equal PBAT. Measured across all 26 adjudicated plans: zero
dispatches sit above the unconstrained optimum. Entry divergence from
beyond the cap is impossible on this data, not merely unobserved.
This is the same cap-killing move used throughout the program (§2.5).

**Verdict on the founding question, as a closure claim.** Same
actions at every tie the text cannot break; same deliverability
through the volume layer, both regimes, under stress beyond any
realistic deployment, with both cap exposures closed structurally.
The volume channel is the candidate fifth degree of freedom and it is
permitted-but-inert: the witness proves the permission, the replay
and the absorption mechanism prove the inertness on physical inputs.
What remains is exactly the four deferred points of §4. Fix those and
two conformant implementations of this standard are behaviorally
identical on natural traffic, in selection and in delivery, across
the measured OWLT range. The residual reliability risk is textual,
not algorithmic.

## 8. Limitations

Every rate is regime-indexed; the three corpus families are three
points in a plan-structure space, and the dense-topology large-OWLT
cell is unmeasured (its prediction is registered, §6.1). The ION leg
on the real-DSN corpus awaits margin-frame grading; ION's profile
there is a frozen mirror prediction. Multi-priority charging and
fragmentation are unexplored. Adversarial traffic is out of scope by
design: witness-shaped traffic amplifies by construction, so the
adversarial question is an attack-cost question - how much control
over traffic shape buys a deliverability split between conformant
implementations - and belongs to a security framing of SABR, not to a
reliability characterization; we flag it as separate work. The
reference's §3.2.6.9 c) filter is enforced by measurement (zero
route-level violations) rather than implemented in the search;
implementing it re-scopes the kernel theorems to the filtered class
and is queued behind an audit for exactly the class-narrowing
circularity this program has repeatedly caught elsewhere. The corpora
contain no priority structure, no custody dynamics, and no link
failures; "reliability" here means determinism and deliverability of
selection under the standard's own semantics, not end-to-end network
resilience.

## 9. Why the closure claim should be believed

A reader of a result this null-shaped - "the implementations were
never the risk" - is owed an account of why the conclusion is not a
story fitted to the data. The account is that the program tried,
repeatedly and by design, to break its own claims, and the record of
those attempts is the evidence. Five times the object under
measurement dissolved when a control built against our own hypothesis
fired: the reference could not certify itself from inside its own
frame (caught by the strict-superset oracle requirement); a
mechanism attribution for 49 deviations was falsified by binary
provenance - the proposed mechanism was absent from the binary that
produced the data - once against our own account and once against an
external reviewer's; the tiebreak layer's apparent dominance
dissolved when a control cell sharing the light-time regime but not
the topology showed none of it; the planned OWLT transition curve
falsified its own axis; and the volume layer's single field
divergence died under adjudication, with the closure then made
structural rather than empirical. Each catch came from a
pre-registered prediction, a deliberately stronger oracle frame, or a
provenance check - instruments built to surface exactly the failure
they surfaced.

What survived that process is the claim of this paper. The program
set out to find reliability risk in implementations, built
instruments designed to surface it, and those instruments instead
localized all variation to four places in the standard's text - a
conclusion we repeatedly tried and failed to break. For CCSDS
734.3-B-1 the surviving characterization is: a selection order that
is total and precise; action-deterministic at every tie it cannot
break; settled through the volume layer on physical traffic under
stress beyond realistic deployment, with the one permitted divergence
channel exhibited by construction and shown inert by mechanism; and
ranging over a candidate list, a margin value, a route class, and a
graph that the text leaves to its implementers, its operators, and in
one case to a false declaration. The fix costs are small and named.
Until they are paid, two faithful implementations of this standard
agree exactly where the text speaks, and the map of their
disagreement is the map of where it does not.

## Appendix A. Implementation mechanism accounts

### A.1 ION 4.1.4

In the unloaded regime the returned route is the single first-Dijkstra
route of `computeDistanceToTerminus`: relaxation is strict `<` on
best-case arrival only, so an equal-arrival path never updates a work
area and recorded hop counts are first-improver artifacts; the next
current contact is chosen by (arrival, stale hop count) with ties to
contact-index order; the search stops at the first contact delivering
to the terminus. The Yen/Lawler registry never iterates because the
candidate-list walk stops when one candidate exists (§4.1), so
`tryRoute`'s verbatim four-key cascade ranges over a singleton. Key 1
is sound (oracle-confirmed two-sided); the 512 key-2 excesses are the
stale-hop-count approximation at arrival ties; key 3 is never
consulted and ION's relative key-3 strength is emergent; key 4 is
never consulted and the index-order tie bias yields a single
deviation. ION's OWLT margin is integer-arithmetic zero below 1491 s
of light time - all of corpus_v3 - and nonzero on the deep-space bands
(the 851-dispatch footprint of §4.2).

### A.2 Reference generations

Recording binary: two-key comparator, leftmost full ties, prepended
file-order expansions, visited-list closing. Everything below key 2 in
its recorded data is frontier order gated by the closed list:
2024 key-3 deviations (1841 comparator-caused, 183 closing-caused), 49
key-4 deviations (all comparator-caused frontier-order emergence; the
dominating smaller-entry candidate was enumerated every time). Current
source, string entry order: key-3 210 (all closing-caused, zero new),
key-4 106 (the 49 persist - on that subpopulation frontier order and
string order pick alike - plus 57 where string order actively picks
the digit-length-wrong entry). Current source, numeric entry order:
key-4 collapses to 1, closing-caused; key-3 unchanged at 210, which is
the visited list's true measured price.

### A.3 Thread-ambiguity bounds

ION's recorded hops are node pairs; window identity is threaded over
the plan. Hop count and entry node are thread-invariant, so of 217
multi-window dispatches only 85 can swing a grade; bounds across all
resolutions keep every headline claim intact at both extremes, and the
route-exact mirror resolves all 85 (to key-3 deviation), landing on
the bound least favorable to ION - which the claims survive.

### A.4 Reading exhaustion

Grades are invariant across the textual readings of the candidate
list: the §3.2.6.9 c) filter changes zero optima; the loopless and
reuse-permitted route classes grade identically at the optimum (loop
erasure); the per-neighbor reading collapses to the universal one (the
global optimum is its own neighbor's best). The two readings that do
move verdicts are the ones reported as findings: the cessation reading
(§4.1), under which ION is conformant by construction, and the
own-list reading, under which the recording reference still deviates
on 1890/4093.

## Appendix B. Artifact index

All artifacts live in this repository: the Lean reference and theorem
files; `scripts/diffharness/` (differential harness, two-oracle
instrument v3 with per-dispatch dump, mechanism mirrors with frozen
prediction files and scores, the 4-key field runner, the
distribution-swap runner, the two-ledger volume replay with embedded
witness selftest); per-corpus reports under `out_diff_v3/` and
`out_s5/`; the standalone acyclicity erratum and the working notes
(`docs/notes/`) from which this draft's numbers are drawn verbatim.
