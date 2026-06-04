import VerifiedSabr.Route
import Mathlib.Data.String.Basic

namespace VerifiedSabr

/-- A search candidate: hops in reverse order (most recent first) and the
    bundle's arrival time at the head's destination. [algorithm.md §3] -/
structure Cand where
  hops : List Contact
  arrival : Time
  deriving Repr

/-- Node where the candidate's bundle currently sits. [algorithm.md §3] -/
def Cand.node (cand : Cand) (src : Node) : Node :=
  match cand.hops with
  | [] => src
  | c :: _ => c.dest

/-- Candidate termination time: the earliest contact end time among its hops
    (§1.4 / §2.3.2.1); `none` for the root candidate, ordered as +∞ — no
    contact yet bounds the candidate's usability. [algorithm.md §10.1] -/
def Cand.termTime (cand : Cand) : Option Time :=
  cand.hops.foldr
    (fun c acc =>
      match acc with
      | none => some c.tEnd
      | some t => some (min c.tEnd t))
    none

/-- Candidate entry node: destination of the first hop — the node the bundle
    would be enqueued to (§3.2.8.1.4 b); `none` for the root candidate.
    Hops are stored most-recent-first, so the first hop is the last list
    element. [algorithm.md §10.1] -/
def Cand.entry (cand : Cand) : Option Node :=
  cand.hops.getLast?.map (·.dest)

/-- Key-3 strict comparison: `a` terminates later than `b`, with `none` as +∞
    (the root candidate outlasts every bounded one). [algorithm.md §10.1] -/
def termLater : Option Time → Option Time → Bool
  | none,   none   => false
  | none,   some _ => true
  | some _, none   => false
  | some x, some y => decide (y < x)

/-- Key-4 comparison: entry-node order with the root (`none`) first; node
    strings compare lexicographically (Delta 8). [algorithm.md §10.1] -/
def entryLE : Option Node → Option Node → Bool
  | none,   _      => true
  | some _, none   => false
  | some s, some t => decide (s ≤ t)

/-- The §3.2.8.1.4 a) best-route order as a total comparison on candidates:
    arrival ↑, hop count ↑, termination time ↓, entry node ↑. A full tie
    resolves to the left argument, instantiating the standard's
    "arbitrarily." [algorithm.md §3.5, §10.1] -/
def Cand.le4 (c m : Cand) : Bool :=
  decide (c.arrival < m.arrival)
  || (c.arrival == m.arrival
      && (decide (c.hops.length < m.hops.length)
          || (c.hops.length == m.hops.length
              && (termLater c.termTime m.termTime
                  || (c.termTime == m.termTime
                      && entryLE c.entry m.entry)))))

/-- Extract a minimal candidate from a nonempty frontier under the standard's
    full best-route order (CCSDS §3.2.8.1.4 a), via the total comparison
    `Cand.le4`. Either choice among tied candidates is T1-sound (any returned
    route is valid); the full order is load-bearing for T2 (§10.2). Key 2
    matters in practice: integer light-second plans carry owlt-0 contacts, so
    arrival ties are pervasive and arrival-only selection returns walk-shaped
    routes. [algorithm.md §3.5, §10.1] -/
def pickMin : List Cand → Option (Cand × List Cand)
  | [] => none
  | c :: rest =>
      match pickMin rest with
      | none => some (c, [])
      | some (m, others) =>
          if c.le4 m then some (c, rest)
          else some (m, c :: others)

/-- All feasible one-contact extensions of a candidate. A contact is feasible
    when it departs the candidate's node, its window is still open at the
    candidate's arrival time, and it is not already used by this candidate
    (no contact reuse on a route). [algorithm.md §3] -/
def expand (cp : ContactPlan) (src : Node) (cand : Cand) : List Cand :=
  (cp.filter fun c =>
      (c.source == cand.node src)
      && decide (max cand.arrival c.tStart ≤ c.tEnd)
      && !cand.hops.contains c)
    |>.map fun c =>
      { hops := c :: cand.hops, arrival := max cand.arrival c.tStart + c.owlt }

/-- Best-first loop with the visited-contact list of deployed CGR practice:
    repeatedly take the earliest-arrival candidate; stop when it sits at the
    destination. When the popped candidate's terminal contact is not yet
    closed, close it and expand; when it is already closed, drop the candidate
    unexpanded (a later arrival at a closed contact is dominated — see the
    history caveat in algorithm.md §8.3). The root candidate (no hops) is
    never subject to closing. Fuel guarantees termination; exhausting fuel
    returns none (sound: this is a may-answer search). [algorithm.md §3, §8] -/
def searchLoop (cp : ContactPlan) (src dst : Node) :
    Nat → List Cand → List Contact → Option (List Contact)
  | 0, _, _ => none
  | fuel + 1, frontier, closed =>
      match pickMin frontier with
      | none => none
      | some (best, rest) =>
          if best.node src == dst && !best.hops.isEmpty then
            some best.hops.reverse
          else
            match best.hops with
            | [] => searchLoop cp src dst fuel (expand cp src best ++ rest) closed
            | c :: _ =>
                if closed.contains c then
                  searchLoop cp src dst fuel rest closed
                else
                  searchLoop cp src dst fuel (expand cp src best ++ rest)
                    (c :: closed)

/-- SABR-style earliest-arrival route search. Certifying pattern: the result
    is re-checked by `isValidRoute` before being returned. [algorithm.md §3]
    Fuel: with the closed list, each contact is expanded at most once, each
    expansion inserts at most `cp.length` candidates, and the root adds one,
    so total pops are bounded by `cp.length² + cp.length + 1`;
    `(cp.length + 1)² + 1` dominates that. Tight bound is T2-line work.
    [algorithm.md §8.4] -/
def routeSearch (cp : ContactPlan) (src dst : Node) (t₀ : Time) :
    Option (List Contact) :=
  let fuel := (cp.length + 1) * (cp.length + 1) + 1
  match searchLoop cp src dst fuel [{ hops := [], arrival := t₀ }] [] with
  | some hops =>
      if isValidRoute cp src dst t₀ hops then some hops else none
  | none => none

end VerifiedSabr
