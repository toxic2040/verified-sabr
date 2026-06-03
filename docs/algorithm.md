# SABR route-search algorithm — pinned from the normative standard

This document fixes the exact route-computation procedure that the Lean model
formalizes. It is the single reference every later Lean definition cites by
section number. The intent is line-by-line traceability: a reviewer should be
able to diff a Lean definition against the cited section here, and this section
against the cited Blue Book clause, without trusting the author.

## Normative source and edition

**CCSDS 734.3-B-1, *Schedule-Aware Bundle Routing*, Recommended Standard,
Issue 1, Blue Book, July 2019.** Downloaded from
`https://public.ccsds.org/Pubs/734x3b1.pdf` (kept in `docs/sources/`, not
committed). This is the current edition: the CCSDS Blue Books register lists no
734.3-B-2, and the five-year review clause (page ii) had not produced a revised
issue as of this writing. All clause references below (of the form "§3.2.x")
are to this document. The route definition, contact-graph definition, and the
route-computation and forwarding procedures are normative (mandatory in the
PICS proforma, Annex A4.1); the supplementary procedures in Annex C and the
security/patent material in Annex B are informative.

Context sources (non-normative, used only to cross-check and to supply a
published worked example):

- Fraire, De Jonckère, Burleigh, "Routing in the Space Internet: A contact
  graph routing tutorial," *Journal of Network and Computer Applications* 174
  (2021) 102884. Open copy obtained from HAL (`hal-03494106`), full text,
  kept in `docs/sources/`. Cited below as **[Tutorial]**.
- Caini, De Cola, Persampieri, "Schedule-Aware Bundle Routing: Analysis and
  enhancements," *Int. J. Satellite Communications and Networking* 39 (2021)
  237–249, DOI 10.1002/sat.1384. **Paywalled (Wiley); no open postprint was
  located** at IRIS UniBo, HAL, or author pages. Not used as a source for any
  statement in this document; the Blue Book is normative and the tutorial
  supplies the worked example, so its absence does not affect the model. (An
  older, related conference deck by Bezirgiannidis & Caini was retrieved but is
  a different paper and is not relied on.)

Where the Blue Book and the tutorial use different names for the same quantity,
the Blue Book term governs. The tutorial's BDT ("best-case delivery time") is
the Blue Book's "best-case delivery time" (§3.2.4.2); the tutorial's RVL/EVL
naming matches the Blue Book's RVL (§3.2.6.8.10) — the tutorial notes this
correspondence explicitly.

---

## 1. Contact plan model

A contact plan comprises **contacts** and **range intervals** (§2.3.1, and the
definition of "contact plan" in §1.4).

A **contact** (§2.3.1; definition in §1.4) is an interval during which data is
expected to be transmitted by a sending node and received by a receiving node.
The Blue Book characterizes each contact by:

| Field | Blue Book term | §1.4 / §2.3.1 |
|-------|----------------|----------------|
| sending node | "the contact's sending node" (node A) | §2.3.1 |
| receiving node | "the contact's receiving node" (node B) | §2.3.1 |
| start time | "its start time" | §2.3.1 |
| end time | "its end time" | §2.3.1 |
| data rate | "the mean rate at which data are expected to be transmitted" | §2.3.1 |

Derived per-contact quantities the standard names:

- **duration** = end time − start time (§1.4, §2.3.1).
- **volume** = duration × data transmission rate (§1.4, §2.3.1, §2.4 family).
- A contact is **terminated** if its end time is not later than the current
  time (§2.3.1).

Contacts are **unidirectional**. A bidirectional link is represented by a pair
of unidirectional contacts; because of light time, the reverse contact's window
is offset by the one-way light time (Tutorial §III; consistent with the
contact-graph "from/to" asymmetry the Blue Book builds on in §3.2.1). Contacts
on the same link are non-overlapping by definition — they "tile" the timeline
(§2.3.1 NOTE).

A **range interval** (§2.3.1; definition in §1.4) is a period during which the
displacement between two nodes A and B varies by less than one light second from
a stated distance. It carries: the two node identities, a start time, an end
time, and the anticipated distance **in light seconds** (the *range* / OWLT).
Range is therefore a property of a node pair over a time interval, not a field
inside the contact record; the standard joins the two by node pair and time when
computing arrival (§3.2.4.1.2). Figures 3-2 (contacts) and 3-3 (range intervals)
in the Blue Book are separate tables for exactly this reason.

The **one-way light time (OWLT)** used in arrival computation is the range, in
light seconds, between the contact's sending and receiving nodes during the
contact (§3.2.4.1.2). An **OWLT margin** (§2.4.2) may be added to cover change
in distance while the bundle is in transit; it is mission-specific and "in
practice it may be simplest to assume a worst-case constant" (§2.4.2). For v1 we
take OWLT margin = 0 (see §3 below and the EVL decision in §4).

### Lean modeling note (§1)

A `Contact` carries `source`, `dest`, `tStart`, `tEnd`, and `owlt` (the range in
light seconds for this contact's node pair and window, pre-joined from the range
interval table), plus `rate` for the EVL decision. Time is ℚ. Modeling `owlt`
as a per-contact field is a *faithful pre-join* of §2.3.1's range-interval table
against the contacts: each contact's `owlt` is the range that §3.2.4.1.2 looks
up by sending/receiving node and time. The model must not silently assume
symmetric OWLT — forward and reverse contacts of one link may carry the same
range value but are distinct contacts. This is recorded because it is the first
place a strawman could creep in (treating range as a node-symmetric constant).

---

## 2. Contact graph construction

The model's route search runs over the **contact graph for node D at node X**, a
conceptual directed acyclic graph (§3.2.1). Critically — and this is the most
counterintuitive part of the standard — **vertices are contacts, not nodes**
(§3.2.1 NOTE):

**Vertices** (§3.2.1):
- a **root vertex**: a notional contact from node X (the local node) to itself;
- a **terminal vertex**: a notional contact from node D to itself;
- one vertex for each contact in the plan that lies on some path that goes
  (directly or indirectly) *from* X and (directly or indirectly) *to* D.

**Edges** (§3.2.1.d): there is an edge from the vertex for contact P to the
vertex for contact Q exactly when **P's receiving node = Q's sending node** —
i.e., P signifies transmission *to* some node and Q signifies transmission
*from* that same node. An edge represents an episode of data retention at the
shared node while it waits for the next contact to start (§3.2.1 NOTE).

The graph is acyclic by construction (§3.2.1 calls it a DAG). Note the edge
condition is *adjacency only* (receiver of P = sender of Q); temporal
feasibility (whether Q's window is still open when the bundle arrives) is **not**
an edge-existence condition here. Temporal feasibility enters in route
computation (§3.2.4.1.1), not in graph construction. This matters for the model:
the contact graph's edge relation is the purely structural adjacency relation;
window feasibility is checked along a candidate path during search.

### Route well-formedness (§1.4 "route", §2.3.2)

The Blue Book defines a **route** (§1.4) for a bundle at node X destined for D as
a sequence of contacts such that:

- (a) the sending node of the first contact is X;
- (b) the receiving node of the last contact is D;
- (c) the receiving node of contact *i* is the sending node of contact *i+1*
  (adjacency — same as the edge condition above);
- (d) **the end time of contact *i+1* is no earlier than the start time of
  contact *i*.**

Condition (d) is a weak ordering constraint (it does *not* require
window-by-window arrival feasibility; that is the job of §3.2.4.1.1 during
computation). It is stated here so the Lean `Route` well-formedness predicate
can carry exactly (a)–(d) and no more, with the stronger arrival feasibility
factored into the search/arrival function.

The **termination time of a route** is the earliest end time among all contacts
in the route (§1.4, §2.3.2.1). A route is **terminated** if its termination time
is not greater than the current time (§2.3.2.1). Termination time is one of the
tie-break keys in §3 — pin it now.

The **entry node** of a route is the receiving node of its first contact (§1.4).
(Equivalently, the neighbor of X that the bundle is forwarded to first.)

### Lean modeling note (§2)

`chainOk` models conditions (a)/(c)/(d)-adjacency. The contact graph itself need
not be reified as a separate data structure for v1 search: the search enumerates
successors on the fly via the edge condition "P.dest = Q.source" (§3.2.1.d),
which is the executable form of the graph. Reviewers tracing the model should
read §3.2.1.d as the edge relation and §1.4(a)–(d) as route well-formedness.

---

## 3. Route search procedure

**Transcribed from §3.2.4, §3.2.6, and §3.2.8 of CCSDS 734.3-B-1** (read from
the PDF text, not reconstructed). The standard frames the per-route arrival
computation in two equivalent passes: a *time-only* pass that defines earliest
transmission/arrival per contact (§3.2.4.1), and a *bundle-aware* pass that adds
backlog and bundle size to get first/last-byte times (§3.2.6.2–§3.2.6.7). The v1
model formalizes the §3.2.4.1 time-only pass (zero backlog, zero bundle size,
OWLT margin 0); §4 argues why that is a faithful restriction.

### 3.1 Earliest transmission and arrival (recursion) — §3.2.4.1

Per §3.2.4.1.1 and §3.2.4.1.2, for a route's contact sequence
`c₁, c₂, …, cₙ` with current time `t₀`:

```
earliestTx(c₁)      = max(c₁.start, t₀)                       -- §3.2.4.1.1, first contact
earliestArr(c₁)     = earliestTx(c₁) + range(c₁) + owltMargin -- §3.2.4.1.2
earliestTx(cᵢ₊₁)    = max(cᵢ₊₁.start, earliestArr(cᵢ))        -- §3.2.4.1.1, subsequent
earliestArr(cᵢ₊₁)   = earliestTx(cᵢ₊₁) + range(cᵢ₊₁) + owltMargin   -- §3.2.4.1.2
```

where `range(c)` is the OWLT in light seconds (§2.3.1 range interval, §3.2.4.1.2)
and `owltMargin` is the §2.4.2 safety margin (= 0 in v1).

The **best-case delivery time** of the route is `earliestArr(cₙ)` — the earliest
arrival time of the contact that immediately precedes the terminal vertex
(§3.2.4.2). (In a route, `cₙ` is the last real contact; the terminal vertex is
the notional D→D contact, so the route's delivery time is `earliestArr(cₙ)`.)

### 3.2 Window feasibility — open vs closed at the contact end time

**§3.2.4.1.1, last sentence (verbatim):** *"No contact whose end time is before
its earliest transmission time (i.e., before the earliest arrival time for the
preceding contact in the route under consideration) shall be included in a
route."*

A contact `c` is **excluded** iff `c.end < earliestTx(c)`. Therefore a contact is
**feasible** (includable) iff:

> **`earliestTx(c) ≤ c.end`**

This is a **closed** interval at the end time: transmission may begin *exactly
at* the end time. The exclusion test is strict-less-than (`<`) on the end time,
so its negation — the feasibility test — is less-than-**or-equal** (`≤`). The
Lean arrival function must use `tx ≤ c.tEnd`, not `tx < c.tEnd`. (Edge note: a
zero-duration transmission at the instant the contact closes is feasible under
the letter of the standard; this is a deliberate pin, not an oversight. See the
baseline audit at the bottom.)

There is no analogous lower-bound exclusion separate from `max(c.start, …)`:
arriving before `c.start` is handled by waiting, since `earliestTx` takes the max
with `c.start`. A contact in the *past* relative to the current time is removed
earlier, in route pruning (§3.2.3.2: "every contact whose end time is in the past
shall be deleted").

### 3.3 The search: shortest path on the contact graph — §3.2.6.10

**§3.2.6.10 (verbatim):** *"The next best route from X to D through the contact
graph for node D shall be computed by identifying the shortest path from X to D
(that is, beginning at the root of the graph and ending at the terminal vertex)
excluding all previously identified paths. For this purpose, the cost of edge N
shall be the earliest arrival time of the contact that is the vertex in which
edge N terminates."*

So the search is a shortest-path computation on the contact graph where the
**cost of an edge into contact-vertex `c` is `earliestArr(c)`** (the §3.2.4.1.2
quantity). Because `earliestArr` is monotonically non-decreasing along a route
(each step takes `max` with a non-decreasing arrival and adds a non-negative
range), this cost admits a Dijkstra-style earliest-arrival search — exactly the
"adapted Dijkstra profiting from a monotonically increasing time-related cost
function" the Tutorial attributes to Segui et al. and uses in its Alg. 1/2.

Pseudocode (best-first / earliest-arrival, the executable form of §3.2.6.10 +
§3.2.4.1):

```
routeSearch(plan, X, D, t₀):
    -- candidate = (reversed hop list, arrival time at current node)
    frontier ← { (hops=[], arrival=t₀) }       -- root: notional X→X, arrival t₀
    loop:
        if frontier empty: return none
        best ← candidate in frontier with minimal arrival      -- §3.2.6.10 cost
        remove best from frontier
        node ← (best.hops = [] ? X : best.hops.head.dest)
        if node = D and best.hops ≠ []:
            return reverse(best.hops)           -- terminal vertex reached
        for each contact c in plan with:
                c.source = node                          -- §3.2.1.d edge
                and max(best.arrival, c.start) ≤ c.tEnd  -- §3.2.4.1.1 feasibility (≤)
                and c ∉ best.hops:                       -- no contact reuse (see below)
            arr' ← max(best.arrival, c.start) + c.owlt + owltMargin   -- §3.2.4.1.2
            add (hops = c :: best.hops, arrival = arr') to frontier
```

**No contact reuse on a route.** The contact graph is a DAG (§3.2.1) and the
shortest-path computation is over loopless paths — §3.2.6.10's reference [4] is
Yen's "K Shortest *Loopless* Paths" algorithm, and §3.2.6.9(c) additionally
forbids any route that includes a contact transmitting *to* X (no return to the
source). Forbidding contact reuse within a route is therefore faithful to the
standard's loopless-path search; it is also what makes the fuel bound and the
no-revisit reasoning tractable. (Vertex/contact non-reuse is the conservative
reading; §3.2.6.9(c) is the only explicit in-route exclusion, and it concerns X
specifically. The model forbids reusing any contact, which is strictly inside
the loopless-paths regime the standard's cited algorithm computes.)

### 3.4 Candidate-route filters — §3.2.6.9

Before a computed route becomes a *candidate*, §3.2.6.9 ignores routes failing
any of:

- (a) best-case delivery time after the bundle's expiration time (deadline);
- (b) entry node on the excluded-nodes list;
- (c) the route includes a contact transmitting **to X** (unless D = X);
- (d) earliest transmission opportunity after the initial contact's end time;
- (e) projected bundle arrival time after the bundle's expiration time;
- (f) the route is *depleted* w.r.t. the bundle's priority (volume — see §4);
- (g) (no-fragmentation bundles) RVL < bundle EVC (volume — see §4).

For v1's time-only model: (a)/(e) are the **deadline check** (modeled if a
deadline is supplied; otherwise vacuous); (c) is the **no-return-to-source**
constraint (subsumed by no-contact-reuse plus the fact the search starts at X);
(b) is the excluded-neighbor mechanism (out of v1 scope — single-bundle, no
custody refusal); (d) collapses to the §3.2.4.1.1 window-feasibility test when
backlog = 0; (f)/(g) are the **volume/EVL** filters whose in/out status is the
subject of §4.

### 3.5 Tie-breaking among candidate routes — §3.2.8.1.4 a)

**This is the exact, ordered tie-break the standard specifies** (§3.2.8.1.4 a),
verbatim structure):

1. **Earliest projected bundle arrival time.** If one candidate route has an
   earlier projected arrival time than all others, it is the best route.
   *(In the time-only model, projected arrival time = best-case delivery time =
   `earliestArr(cₙ)`.)*
2. **Fewest contacts.** Otherwise, among routes tied on earliest arrival, if one
   has a smaller number of contacts (hops) than every other, it wins.
3. **Latest termination time.** Otherwise, among routes tied on arrival and hop
   count, the one with a *later* termination time than every other wins.
   (Termination time = earliest contact end time in the route, §1.4 / §2.3.2.1;
   a later termination time means the route stays usable longer.)
4. **Smallest entry node number.** Otherwise, the route with the smallest entry
   node number is chosen arbitrarily to break the remaining tie.

Order, verbatim: **(arrival ↑, hop-count ↑, termination-time ↓, entry-node ↑)**.
Keys 1–2 are minimized, key 3 is *maximized*, key 4 is minimized. The Lean
optimality theorem (T2) and any "the search returns *the* best route" claim must
use this 4-key order — not arrival alone. The v1 search's `pickMin` currently
breaks ties only on arrival; see the baseline audit. For T1 (soundness) the
tie-break is irrelevant (any returned route is valid); it becomes load-bearing
at T2.

### 3.6 Forwarding and the src = dst case

Forwarding (§3.2.8) enqueues the bundle to the entry node of the best candidate
route and decrements MTVs. The multi-node forwarding model (T3) lives in a later
plan. For v1's single search, note: the standard computes routes *to* D; if X = D
there is nothing to route (the contact-plan check §3.2.2 and the loopback caveat
§3.2.6.9(c) are the only places D = X appears). The model returns `none` for the
empty/no-hop case. Routes are nonempty by definition: §1.4 defines route as a
sequence of contacts satisfying (a)–(d), which presuppose a first and last contact.

---

## 4. EVL decision — volume in or out of v1 route search?

**Question.** §3.2.6 ("populating the candidate routes list") is **mandatory**
(PICS item SABR-CGR-05, Annex A4.1, status M). It contains the entire
volume machinery: estimated volume consumption (EVC), maximum transmission
volume (MTV), effective volume limit (EVL, §3.2.6.8.9), route volume limit (RVL,
§3.2.6.8.10), and the depletion filters §3.2.6.9(f)/(g). A time-feasibility-only
route search omits all of it. Is the omission a faithful restriction, or a
strawman?

**The argument that volume must be IN (it's a strawman without it).**
The volume filters are normative and mandatory, not optional — only anticipatory
fragmentation (§3.2.8.2) is marked O in the PICS. §3.2.6.9(f) ignores any
*depleted* route and §3.2.6.9(g) ignores any route whose RVL is below the
bundle's EVC; both can change *which route is selected*, not merely annotate it.
A model that always returns the earliest-arrival time-feasible route will, on
plans where that route is volume-depleted, return a route the conforming
implementation would have rejected — a behavioral divergence on the standard's
own mandatory selection logic. If the artifact's headline is "we formalized the
standardized route search," silently dropping a mandatory selection constraint
invites the exact strawman criticism the project is built to avoid. Differential
testing against a real implementation (§5) would surface these as disagreements.

**The argument that volume can be OUT for v1 (faithful restriction).**
The volume layer is parameterized by the *bundle* (its EVC, its priority) and by
*queue state* (backlog, prior reservations) — quantities that are explicitly
"only available at forwarding time" (Tutorial §IV; Blue Book §3.2.6.2 backlog,
§3.2.6.8.2 reservations). With **one bundle, empty queues, and unlimited
contact volume**, every contact's MTV equals its full volume, no route is
depleted (§3.2.6.8.11 requires RVL ≤ 0), RVL ≥ EVC trivially, and filters
§3.2.6.9(f)/(g) are vacuously satisfied. Under that boundary condition the
mandatory §3.2.6 procedure *reduces exactly* to the §3.2.4.1 time-only
computation — the time-only model is the standard restricted to the
infinite-volume / single-bundle case, not a different algorithm. The earliest-
arrival recursion (§3.2.4.1), the shortest-path cost (§3.2.6.10), and the
tie-break (§3.2.8.1.4) are *all* volume-independent; volume only ever *removes*
candidates. So the time-only search computes the same route the full procedure
would, on any plan where contact volumes are not the binding constraint.

**Decision (2026-06-03): OUT for v1, with the restriction stated as an explicit
hypothesis in the theorems.** Justification passage: §3.2.6.8.8 — "The initial
value of MTV of a given contact, for all levels of priority, is the volume of
the contact" — combined with the depletion definition §3.2.6.8.11 (depleted iff
RVL ≤ 0). The honest framing is not "we ignore volume" but "we formalize the
standard's route search under the hypothesis that no contact is volume-binding
(single bundle, empty queues), which §3.2.6.8.8/§3.2.6.8.11 make precise," and
the theorem statements carry that hypothesis. This keeps v1 a *faithful
restriction* rather than a strawman, defers the bundle/queue state machine (out
of v1 scope per the design spec), and leaves a clean seam: EVL re-enters as an
additional filter on the candidate set without touching the arrival recursion or
the tie-break.

---

## 5. Oracle choice for differential testing

### Reference-implementation facts (Step 3)

| Implementation | URL | License | Language | Activity | SABR/CGR fidelity |
|----------------|-----|---------|----------|----------|-------------------|
| **µD3TN** | gitlab.com/d3tn/ud3tn | BSD-3-Clause | C | Active (D3TN GmbH; space-tested; regular releases) | CGR routing module; explicit SABR/CCSDS lineage; small, POSIX-targeted |
| **ION-DTN** | github.com/nasa-jpl/ION-DTN (moved from SourceForge mirror, Nov 2025) | "ION Open Source" (permissive, JPL/Caltech) | C | Active (NASA/JPL; the de-facto reference deployment) | CGR is ION's native routing; the implementation SABR was standardized from |
| **HDTN** | github.com/nasa/HDTN | NASA Open Source Agreement v1.3 | C++ | Active (v2.0.0, Sep 2025; ~2700 commits) | Router runs Dijkstra on the contact plan; CGR-style; newer, high-rate focus |
| **pyCGR** | bitbucket.org/juanfraire/pycgr | (companion to the Tutorial; check repo) | Python | Tutorial companion (2020–2021); low ongoing activity | Pedagogical; algorithm naming mirrors the Tutorial's Alg. 1/2; closest to the time-only model |

### Decision (2026-06-03): **ION-DTN** as the primary oracle, with **pyCGR** as a
bring-up sanity oracle.

Rationale:

- **Fidelity.** ION is the implementation from which SABR (CCSDS 734.3-B-1) was
  standardized — its CGR is the reference behavior the Blue Book codifies.
  Agreement with ION is the strongest "we match the standard" evidence, and any
  disagreement is a genuine finding (model bug *or* a known ION quirk worth
  citing). This is the prediction-class check the design spec's reality bridge
  requires.
- **License.** ION's open-source license is permissive and poses no obstacle to
  using it as an external oracle (we run it, we don't redistribute it).
- **Driving it programmatically.** ION ingests contact plans as text
  (`ionrc`/`cpcommand` contact and range entries) and exposes route computation;
  a harness can write a generated plan, run the CGR route lister, and parse the
  result. This is more setup than pyCGR but is the realistic path to a
  defensible oracle.
- **Why pyCGR as a second, lighter oracle.** pyCGR is Python, mirrors the
  Tutorial's algorithm structure, and is the *easiest* to drive
  programmatically — ideal for the first end-to-end harness wiring (P6 bring-up)
  and for reproducing the §6 worked example before pointing the harness at ION.
  It is pedagogical, not space-grade, so it is a sanity oracle, not the headline
  one.
- **Why not µD3TN / HDTN as primary.** Both are well-maintained and active, but
  µD3TN's router and HDTN's Dijkstra-on-contact-plan are *re-implementations* of
  the CGR idea rather than the standardization source; HDTN's documentation does
  not foreground SABR conformance specifically. They are strong secondary cross-
  checks if ION agreement needs corroboration, and µD3TN's BSD license and small
  C core make it the easiest of the C implementations to build.

If ION build/drive cost proves high at P6, the documented fallback is pyCGR-
primary for v1 with an ION cross-check deferred — recorded so the decision is
explicit, not silent.

---

## 6. Worked example (machine-checkable test)

Source: **[Tutorial], Figure 3 (contact plan) and Figures 6–7 (routes and
metrics)**, the paper's running A→E example. The Tutorial states the route and
its best-case delivery time in the text (§IV) and confirms the metric in Fig. 7
and §IV (BDT = 3, tx_win = (0,8), R.volume = 8). This is a *published* optimal
route, which is exactly the cross-check the design spec asks for.

### Contact plan (Tutorial Fig. 3a)

Each `#x/y` in the figure is a bidirectional pair; the table gives the forward
(src→dst) direction. **All contacts: rate = 1, range (OWLT) = 1.** Current time
t₀ = 0. OWLT margin = 0.

| Contact | src | dst | start | end | rate | range (owlt) |
|---------|-----|-----|-------|-----|------|--------------|
| #1/2   | A | B | 0  | 60 | 1 | 1 |
| #3/4   | B | C | 0  | 60 | 1 | 1 |
| #5/6   | A | C | 0  | 60 | 1 | 1 |
| #7/8   | C | D | 0  | 30 | 1 | 1 |
| #9/10  | A | E | 10 | 20 | 1 | 1 |
| #11/12 | D | E | 0  | 10 | 1 | 1 |
| #13/14 | D | E | 30 | 40 | 1 | 1 |
| #15/16 | D | E | 50 | 60 | 1 | 1 |

(The reverse directions B→A, C→B, C→A, D→C, E→A, E→D exist as the paired
contacts but are irrelevant to A→E routing and are omitted from the model plan,
except that they would be present in a literal transcription. The forward-only
plan above is sufficient and is what the Tutorial uses for the A→E routes.)

### Expected result: routing A → E, t₀ = 0

The Tutorial highlights four A→E routes, ordered by best delivery time. The
**optimal (best) route is Route (1)** (Tutorial §IV, verbatim):

> Route (1) R^{A→E} = { C^{0,60}_{A,C}, C^{0,30}_{C,D}, C^{0,10}_{D,E} },
> with **BDT = 3**, tx_win = (0,8), R.volume = 8.

In this model's terms:

- **Expected route:** `[#5/6 (A→C), #7/8 (C→D), #11/12 (D→E)]`
- **Expected best-case delivery (arrival) time at E:** **3**
- **Hop count:** 3

Hand computation via the §3.1 recursion (owltMargin = 0):

| step | contact | earliestTx = max(start, prevArr) | feasible? (tx ≤ end) | earliestArr = tx + owlt |
|------|---------|----------------------------------|----------------------|--------------------------|
| 1 | #5/6 A→C  | max(0, 0) = 0 | 0 ≤ 60 yes | 0 + 1 = 1 |
| 2 | #7/8 C→D  | max(0, 1) = 1 | 1 ≤ 30 yes | 1 + 1 = 2 |
| 3 | #11/12 D→E| max(0, 2) = 2 | 2 ≤ 10 yes | 2 + 1 = 3 |

Best-case delivery time = `earliestArr(#11/12) = 3`, matching the Tutorial's BDT = 3.

The three other A→E routes the Tutorial draws, for completeness (the model should
*not* return these as best, since Route (1) has the earliest arrival):

- **Route (2):** `[#9/10 (A→E)]`, direct. earliestTx = max(10, 0) = 10 ≤ 20,
  arrival = 10 + 1 = **11**. One hop, but arrives later than Route (1).
- **Route (3):** `[#5/6, #7/8, #13/14 (D→E)]`, storage at D until 30.
  arrival at D = 2, then #13/14: tx = max(30, 2) = 30 ≤ 40, arrival = **31**.
- **Route (4):** `[#5/6, #7/8, #15/16 (D→E)]`. tx = max(50, 2) = 50 ≤ 60,
  arrival = **51**.

Ordering by best delivery time: Route(1)=3 < Route(2)=11 < Route(3)=31 <
Route(4)=51 — matching the Tutorial's "ordered by best delivery time" caption.

**Test assertions for Lean (P2 / Task 5):**

- `routeSearch plan "A" "E" 0 = some [#5/6, #7/8, #11/12]`
- `arrivalTime 0 [#5/6, #7/8, #11/12] = some 3`
- `arrivalTime 0 [#9/10] = some 11`
- `arrivalTime 0 [#5/6, #7/8, #13/14] = some 31`
- `arrivalTime 0 [#5/6, #7/8, #15/16] = some 51`

These are exact-rational equalities; they fail loudly if the model's interval
test, recursion, or tie-break diverges from the standard.

---

## 7. T3a candidate statement (informs the loop plan)

Each node runs `routeSearch` over its own contact plan and forwards the bundle to
the entry node (first-hop receiver) of the best candidate route (§3.2.8). The
standard's selected route is, by §3.2.6.10 + §3.2.4.1, a *loopless* shortest
path whose per-vertex cost is `earliestArr`, and `earliestArr` is **strictly
monotonic along any route** when every contact's range (OWLT) is positive
(`earliestArr(cᵢ₊₁) = max(cᵢ₊₁.start, earliestArr(cᵢ)) + range(cᵢ₊₁) >
earliestArr(cᵢ)` whenever `range > 0`). The candidate T3a claim:

> **Under identical, accurate contact plans at every node and strictly positive
> OWLT on every contact, the sequence of earliest-arrival times along the actual
> forwarding path is strictly increasing; hence the bundle visits each contact at
> most once and therefore visits each node at most once between scheduled
> contacts — no routing loop occurs.**

The boundary the counterexample family (T3b) lives outside: drop "identical
plans" (plan inconsistency between nodes lets node Y compute a route that sends
the bundle back toward node X under a stale view) or drop "positive OWLT"
(zero-range contacts permit equal arrival times and thus a tie the
strict-monotonicity argument no longer rules out). T3a's contribution is the
precise hypothesis boundary, and T3b reproduces the loop phenomenology the
literature patches heuristically (the §3.2.8.1 NOTE's "history list" remark is
the standard acknowledging this exact failure mode). This paragraph is a
candidate statement to be sharpened during the proof, not a fixed theorem.

---

## Baseline audit (internal)

Comparison of §1–§3 above against the pre-Blue-Book baseline Lean code in
`docs/plans/2026-06-03-verified-sabr-v1-core.md`, Tasks 3–5. Deltas found are
listed here and have been amended in the plan file's code blocks.

**Delta 1 — interval test at contact end time (Task 4, `arrivalTime`): CORRECT,
confirmed.** Baseline uses `if tx ≤ c.tEnd then …`. The standard's §3.2.4.1.1
excludes a contact iff `c.end < earliestTx(c)`, so feasibility is
`earliestTx(c) ≤ c.end` — a **closed** interval at the end time. Baseline `≤`
matches. No change. (Flagged because this is the single most likely off-by-one;
it is right in the baseline, and §3.2 above documents *why* `≤` and not `<`.)

**Delta 2 — `owlt` / range field (Task 3, `Contact`): name/semantics
clarified, no code change.** Baseline `owlt : Time` is the §3.2.4.1.2 range in
light seconds. Confirmed faithful as a pre-join of the §2.3.1 range-interval
table. The baseline comment should note that `owlt` is the range for *this
contact's* node pair and window (forward/reverse contacts are distinct), to
forestall a symmetric-OWLT strawman. Documentation-only; no structural change.

**Delta 3 — arrival recursion (Task 4, `arrivalTime`): CORRECT, confirmed.**
Baseline computes `tx = max t c.tStart`, then `arrivalTime (tx + c.owlt) rest`.
This is exactly §3.2.4.1.1 (`max` with start / preceding arrival) and §3.2.4.1.2
(`+ range`), with owltMargin = 0. No change. The `t` threaded through is the
preceding contact's `earliestArr`, matching the standard's recursion.

**Delta 4 — `Cand.node` / expand edge condition (Task 5, `expand`): CORRECT,
confirmed.** Baseline filters successors on `c.source == cand.node src` (the
§3.2.1.d edge "P.dest = Q.source"), window `max cand.arrival c.tStart ≤ c.tEnd`
(§3.2.4.1.1, closed), and `!cand.hops.contains c` (no contact reuse — faithful to
the §3.2.6.10 loopless-paths search, see §3.3). All three match. No change.

**Delta 5 — tie-break in `pickMin` (Task 5): DIVERGENCE (deferred, documented).**
Baseline `pickMin` selects the minimal-`arrival` candidate only. The standard's
full tie-break (§3.2.8.1.4 a) is the 4-key order
**(arrival ↑, hop-count ↑, termination-time ↓, entry-node ↑)** (§3.5 above).
For **T1 (soundness)** the tie-break is irrelevant — any returned route is valid,
which is all Task 6 proves — so the baseline is sound as written and **needs no
change for the P0–P3 plan**. The divergence becomes load-bearing only at **T2
(optimality)** in the second plan, where "the search returns *the* best route"
requires the full 4-key order. **Action taken:** added a `-- NOTE (algorithm.md
§3.5):` comment on `pickMin` in the plan flagging that the arrival-only order is
a T1-sufficient simplification and must be replaced by the 4-key order before T2.
No behavioral change to the P0–P3 code.

**Delta 6 — src = dst returns `none` (Task 5, `routeSearch` + SearchTests):
CORRECT, confirmed.** Baseline returns `none` for `"A" "A"` via the
`!best.hops.isEmpty` guard. Matches §1.4 (a route is one-or-more contacts) and
the §3.2.2 contact-plan-check framing. No change.

**Delta 7 — worked example (Task 5 Step 5 / Task 7): SPECIFIED.** The baseline
plan left the worked example as "transcribe from §6." §6 above now fixes it: the
Tutorial Fig. 3 plan, A→E, t₀ = 0, expected `[#5/6, #7/8, #11/12]`, arrival 3.
**Action taken:** noted in the plan that the §6 example is the Tutorial A→E case
with the exact assertions listed in §6.

**Net:** the time-only baseline is faithful to CCSDS 734.3-B-1 for the P0–P3
(T1 soundness) scope. The only standard-vs-baseline divergence is the
tie-break (Delta 5), which is correct to defer to T2 and is now flagged in the
plan. The volume layer (§4) is an explicit, documented restriction, not a
divergence. Field set, interval semantics (closed at end), and arrival recursion
all match the standard.
