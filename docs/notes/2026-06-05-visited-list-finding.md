# Finding: the visited set weakens the best-route order to explored routes

Status: pinned 2026-06-05, witness machine-checked (SearchTests, `vPlan`);
extended same day by the field conformance audit (instrument.py v2) —
see "Field audit" below, which generalizes this finding beyond key 2 and
finds it in BOTH implementations with complementary profiles.
Paper-staging note for the verified-sabr writeup; everything below is
backed by a kernel-checked theorem, a compile-time guard, or the audit
report in the tree.

## The observation as originally filed

Deployed CGR — ION and this model alike — prunes the best-first search
with a visited-contact list: the first time a candidate ending in contact
`c` is popped and expanded, `c` closes, and any later candidate ending in
`c` is dropped unexpanded (algorithm.md §8). The Blue Book does not
mention the device; §8.1 records that the standard neither requires nor
forbids it. The §8.3 caveat identified the mechanism by which it could in
principle cost more than work: candidates reaching `c` by different
histories exclude different continuations under the no-reuse rule, so the
closing candidate can be unable to use a continuation the dropped
candidate needed. Neither the standard nor the Tutorial remarks on this.

## What the formal results settle

On nonnegative-OWLT plans (`PlanNonnegOwlt`, physically vacuous, required
in earnest — see the §10.3 negative-owlt witness), the worry is dead at
the arrival level, unconditionally and kernel-checked:

- **Arrival is never hurt.** `routeSearch_optimal` (T2b): any returned
  route arrives no later than every valid route — contact-reusing and
  search-unreachable competitors included. The §10.3 proof dissolves the
  history-divergence mechanism rather than repairing it: a competitor's
  first open contact cannot lie in the all-closed history of the contact
  that closed the boundary, so the no-reuse rule never blocks the
  boundary extension.
- **Existence is never hurt.** `routeSearch_complete` and
  `routeSearch_none_iff` (§10.4): `none` exactly when no valid route
  exists. The "`none` where a route exists" branch of the original caveat
  cannot occur.

## What survives: route identity above key 1

The §3.2.8.1.4 a) best-route order has four keys: arrival, hop count,
termination time, entry node. The theorems above make key 1 global.
Selection correctness (T2a, `pickMin_min`) makes keys 2–4 correct *over
the frontier* — and the visited set decides what reaches the frontier.
The surviving finding, stated precisely:

> On plans with arrival ties, the search can return a route that is
> §3.2.8.1.4-worse at key 2 than an arrival-tied valid route it pruned.
> The standard's best-route order holds globally at key 1 and only
> explored-set-relatively at keys 2–4.

This is not a model artifact. ION closes contacts the same way, so both
sides explore the same restricted space (§8.3); the P6 differential's
3009 hop-sequence divergences, all at arrival ties, corroborate how much
route multiplicity lives exactly where the restriction bites.

## Witness

Five contacts, routing A→E from t₀ = 0 (windows `[0,100]` except `t`;
owlt as listed):

| id | edge | window | owlt |
|----|------|--------|------|
| p1 | A→B | [0,100] | 1 |
| p2 | B→C | [0,100] | 1 |
| q1 | A→C | [0,100] | 3 |
| s  | C→D | [0,100] | 1 |
| t  | D→E | [5,100] | 1 |

Two A→E routes: `[p1,p2,s,t]` (4 hops) and `[q1,s,t]` (3 hops). Both
arrive at 6 — the `t` window opens at 5, so the slower entry into D waits
it out and the tie is forced. Pop trace: root expands to `[p1]`@1 and
`[q1]`@3; `[p1]`@1 closes p1, yields `[p1,p2]`@2; `[p1,p2]`@2 closes p2,
yields `[p1,p2,s]`@3; the 3–3 tie resolves to `[q1]` on key 2, closing q1
and yielding `[q1,s]`@4; `[p1,p2,s]`@3 pops next and **closes s**,
yielding `[p1,p2,s,t]`@6; `[q1,s]`@4 pops with s closed and is dropped —
the 3-hop route dies here, never enumerated; `[p1,p2,s,t]`@6 returns.

Result: returned route 4 hops, pruned valid route 3 hops, arrivals tied
at 6. T2a holds (frontier-relative), T2b holds (arrival tied), key 2
fails globally. Guards pin the trace's endpoints in
`VerifiedSabr/Tests/SearchTests.lean` (`vPlan` block): the returned
route, its arrival, the pruned route's validity and equal arrival, and
the hop counts.

## Reading for practice

Consumers of arrival alone — earliest-delivery forwarding, EVL-style
admission — lose nothing to the visited set. Consumers that ride on the
tie-break tail lose the standard's guarantee silently: fewest-hops as a
proxy for buffer occupancy or custody transfers, latest-termination as a
robustness margin, entry-node preferences for policy. A deployment that
needs keys 2–4 globally must either drop the visited set (and pay the
§8 worst case) or re-rank arrival-tied returns by a second pass over
candidates it retained. The paper should state the weakened contract as
the price of the standard-silent optimization, with the witness above as
the two-route example.

## Field audit (instrument.py v2, corpus_v3, 2026-06-05)

Independent oracles (a state-space earliest-arrival oracle for key 1,
complete over the unbounded reuse class; an exhaustive reuse-allowed
enumerator for keys 2–4, self-bounded by the graded question) graded
both implementations against §3.2.8.1.4 read verbatim — the order is
total through key 4, with the caveat that the text quantifies over an
unpinned candidate list (the strong all-valid-routes reading is graded;
the list-relative reading is the conformance escape hatch and is itself
a finding about the standard).

Results, 4093 dispatches: lean 2020 conformant / 0 key-2 excess / 2024
key-3 deviations / 49 key-4 deviations; ION 2526 conformant / 512 key-2
excess / 1054 key-3 / 1 key-4 (thread ambiguity bounded and then
resolved by mechanism — see below). So the finding generalizes: keys
2–4 are explored-set-relative in BOTH implementations, with
complementary profiles — the search holds key 2 perfectly and pays at
keys 3–4; ION's route-list does the reverse. Equal-hop tie divergences
decompose as 1691 lean-deviates / 614 ion-deviates / 156 both / 2
genuinely arbitrary. The key-1 oracle agreed with the recorded optimum
on all 4093 dispatches: the arrival guarantee (T2b) is confirmed
two-sided over the unbounded class, and everything above key 1 is where
conformance lives.

Provenance correction (2026-06-05, after the source reads): the routes
the audit graded were produced by the binary built at 66948c9, whose
pickMin is two-key (arrival, hop count) — the full 4-key comparison
(3e4d2a0) postdates the recording. Two consequences, both established
by route-exact mirrors of each construction (predict.py, 4093/4093 on
both sides):

- The 2024 key-3 deviations decompose as 1841 comparator-caused (the
  spec-better route sat in the frontier at return; the recording
  comparator never consulted termination) + 183 closing-caused (the
  visited list killed the better route's prefix). The visited list's
  measured field price at key 3 is 183 dispatches; the §8.3 history
  mechanism is real but accounts for under a tenth of the recorded
  deviations.
- The earlier attribution of the 49 key-4 cases to the Delta-8 string
  order was wrong for this data: the recording comparator had no entry
  key. The {10,11,12}-over-{2,8} pattern is frontier-order emergence
  (prepended expansions reverse the plan file's numeric to-node order);
  the dominating smaller-entry candidate was enumerated every time.
  The string-order mechanism remains a property of the current source
  (pinned by SearchTests), and its field behavior is now measured: the
  rebuilt 4-key binary deviates at key 4 on 106 dispatches - the same
  49 plus 57 new digit-length cases the frontier order had gotten
  right - while key-3 deviations collapse to the 210 closing-caused
  ones and conformance rises to 3777/4093.

Full mechanism accounts, the clause-level location of the standard's
underspecification (§3.2.5.1 b) vs §3.2.6.9.1), the quantifier-reading
exhaustion, and the thread-ambiguity bounds live in
2026-06-05-sabr-degrees-of-freedom.md.

## Boundary

Everything here assumes `PlanNonnegOwlt`. With a negative owlt the
stronger statements fail first: T2b itself is false (§10.3 witness:
looping through a time-reversing contact lowers arrival without bound,
and the no-reuse search cannot follow). ION-subset ingestion satisfies
the hypothesis by construction (`buildPlan_nonnegOwlt`).
