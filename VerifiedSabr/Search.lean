import VerifiedSabr.Route

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

/-- Extract a minimal-arrival candidate from a nonempty frontier.
    NOTE (algorithm.md §3.5): this orders candidates on arrival time ONLY. The
    standard's full best-route tie-break (CCSDS §3.2.8.1.4 a) is the 4-key order
    (arrival ↑, hop-count ↑, termination-time ↓, entry-node ↑). Arrival-only is
    sufficient for T1 (soundness: any returned route is valid regardless of which
    earliest-arrival route is chosen). It MUST be replaced by the full 4-key
    order before T2 (optimality), where "returns THE best route" depends on it. -/
def pickMin : List Cand → Option (Cand × List Cand)
  | [] => none
  | c :: rest =>
      match pickMin rest with
      | none => some (c, [])
      | some (m, others) =>
          if c.arrival ≤ m.arrival then some (c, rest)
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

/-- Best-first loop: repeatedly take the earliest-arrival candidate; stop when
    it sits at the destination. Fuel guarantees termination; exhausting fuel
    returns none (sound: this is a may-answer search). [algorithm.md §3] -/
def searchLoop (cp : ContactPlan) (src dst : Node) :
    Nat → List Cand → Option (List Contact)
  | 0, _ => none
  | fuel + 1, frontier =>
      match pickMin frontier with
      | none => none
      | some (best, rest) =>
          if best.node src == dst && !best.hops.isEmpty then
            some best.hops.reverse
          else
            searchLoop cp src dst fuel (expand cp src best ++ rest)

/-- SABR-style earliest-arrival route search. Certifying pattern: the result
    is re-checked by `isValidRoute` before being returned. [algorithm.md §3] -/
def routeSearch (cp : ContactPlan) (src dst : Node) (t₀ : Time) :
    Option (List Contact) :=
  let fuel := (cp.length + 2) ^ (cp.length + 2)
  match searchLoop cp src dst fuel [{ hops := [], arrival := t₀ }] with
  | some hops =>
      if isValidRoute cp src dst t₀ hops then some hops else none
  | none => none

end VerifiedSabr
