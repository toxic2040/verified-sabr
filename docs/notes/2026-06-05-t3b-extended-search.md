# T3b-extended mechanical loop search: exhaustion

Status: search executed 2026-06-05, outcome machine-checked (LoopSearch
module + LoopSearchTests guards). Seed evidence for the impossibility
branch (plan task 5). Backed by the real Lean `forward` on every candidate.

## Question

T3b-extended (plan, algorithm.md §7, §11.1): can visited-set pruning alone
— identical accurate plans, strictly positive (or just nonnegative) OWLT —
drive the *implemented* router (`routeSearch` forwarding via `forward`) to
revisit a node along a trajectory? A revisit would upgrade the §8.3 route-
shape identity finding (a single search returning a key-2-worse route) to
forwarding behavior: an extra physical transit.

## Family searched

Not generic random plans. The custody-shift obstruction (plan, "Hand-
construction obstruction") says a revisit needs an engineered interior
arrival TIE whose key-3/key-4 (termination, entry-node) asymmetry disagrees
with the one-hop count shift between consecutive custodians. Three families,
each a scaffold forcing such ties, varying the obstruction's live parameters;
each candidate plan run through the real `forward` (`hasRevisit`,
`VerifiedSabr/LoopSearch.lean`).

| family | nodes / dst | menu | varied | plans | ran | engineered ties | revisits |
|--------|-------------|------|--------|-------|-----|-----------------|----------|
| I | A–E / E | 10-contact menu, all subsets: fwd + back edges, join node C two ways, gated final D→E | gate ∈ {0,2,5}, owlt o1,o2 ∈ {0,1,2,3} | 49152 | 22272 | — | 0 |
| II | 1–4 / 9 | 10-contact menu, all subsets: long arm 1→2→3→4 vs short arm 1→4 to join node 4, back edges from 4, gated final 4→9 | gate ∈ {0,3,6}, owlt ∈ {0,1,2}, (tEnd1,tEnd2) ∈ {(10,20),(20,10),(50,50)} | 27648 | 12744 | 432 | 0 |
| III | 1–3 / 9 | 6 edges (fwd + back) each with independent owlt, gated final 3→9 | gate ∈ {0,4}, final owlt ∈ {0,1,2}, per-edge owlt ∈ {0,1,2} | 4374 | 4374 | — | 0 |

Totals: 81174 plans enumerated, 39390 ran a trajectory (source had a route),
**0 node revisits**. "Ran" filters plans where the source has no route at all.
"Engineered ties" (Family II) counts running plans where the long arm and
the short arm both reach the join node at the same arrival with different hop
counts — the differing-hop-count interior tie the obstruction targets. 432
such plans confirm the family is non-vacuous: the ties are present; none
flips a first hop backward. Window gates include the `vPlan` tie-forcer
pattern (a final edge opening late so a slower entry waits it out and the
arrival ties). The owlt-0 setting exercises the zero-range regime where
arrival ties are pervasive. Numeric ids make key 4 numeric (algorithm.md
§10.1, Delta 8).

## Where the obstruction absorbed every near-miss

The custody-shift invariance: custody is only ever handed to the first hop
of a *complete* route to the destination that the predecessor's search
already selected and validated. So when custody lands at node Y, a complete
forward route Y→…→dst existed in the (single, shared) plan — it is the
suffix of the predecessor's chosen route. Y's own arrival-optimal search
(key 1 global, T2b) therefore continues forward; the closing race can change
*which* arrival-tied forward route survives, but it cannot promote an
arrival-dominated backward route, because going backward then forward under
nonnegative OWLT never arrives earlier.

The sharp form, located by the search and pinned as a guard (the "forced"
probe, `forcedPlan` in LoopSearchTests): a single `routeSearch` **can**
return a backward first hop. With B's forward edge B→C closed by B's arrival
time, `routeSearch forcedPlan B D 1 = [B→A, A→C, C→D]` — B routes back
through A. But the trajectory from A is `[A, C, D]`: A's arrival-optimal
route is `[A→C, C→D]`, so custody skips B entirely. The configuration that
makes a node route backward (no open forward edge) is exactly the one that
removes it from every complete route the predecessor could pick. The
backward-routing capability is real but unreachable along a trajectory.

## Reading for the impossibility branch (plan task 5)

This is exhaustion, not a proof, but it points the formal effort precisely.
The conjecture to prove for the implemented router, from a weaker premise
than T3a-main's key-2 global optimality:

> On `PlanNonnegOwlt` plans, the `forward` trajectory never revisits a node.

Proof sketch the search supports: custody at step n+1 sits at the first-hop
receiver of `routeSearch cp xₙ dst tₙ`, whose returned route R is a complete
valid route xₙ→…→dst. Its tail (R minus the first hop) is a valid route
xₙ₊₁→…→dst feasible from tₙ₊₁ (the §3.2.4.1 arrival), so `routeSearch` at
xₙ₊₁ returns *some* route with arrival ≤ arrival(tail) ≤ R's arrival (T2b,
key-1 global, plus arrival monotonicity §10.3). Induct: the optimal arrival
to dst is non-increasing along the trajectory. A revisit to a node first
seen at time tᵢ < tₙ would, by §10.3 monotonicity (later departure cannot
arrive earlier), force the optimal arrival from that node to be equal at
both visits — but the later visit departs strictly later under positive OWLT,
contradiction; under zero OWLT the arrival can tie, and the key-2 descent
that T3a-main uses is unavailable (key 2 is not global here), so the zero-
OWLT case needs the closing-race argument above rather than descent. The
positive-OWLT case (the §7 hypothesis, PlanPosOwlt) is the clean target;
the zero-OWLT case is where the standard's own loop story is genuinely
thinner and the closing-race argument carries it.

This separation — positive OWLT closes by strict arrival monotonicity, zero
OWLT by the closing-race/reachability argument — is the shape task 5 should
take. The squeeze/descent core of T3a-main remains the abstract companion;
the implemented-router theorem replaces descent (which needs key-2 global)
with reachability (custody lands only on predecessor-selected forward hops).
