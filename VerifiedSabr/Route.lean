import VerifiedSabr.Basic

namespace VerifiedSabr

/-- Earliest time the bundle is available at the final node after threading
    the given hops, starting available at time `t`; `none` if any contact
    window is missed. First-byte semantics: transmission duration ignored,
    only window feasibility and light time. [algorithm.md §3] -/
def arrivalTime (t : Time) : List Contact → Option Time
  | [] => some t
  | c :: rest =>
      let tx := max t c.tStart
      if tx ≤ c.tEnd then arrivalTime (tx + c.owlt) rest
      else none

/-- Consecutive hops connect: each contact's destination is the next
    contact's source. [algorithm.md §2] -/
def chainOk : List Contact → Bool
  | [] => true
  | [_] => true
  | c₁ :: c₂ :: rest => (c₁.dest == c₂.source) && chainOk (c₂ :: rest)

/-- Route validity: nonempty, departs `src`, terminates at `dst`, hops are
    adjacent, all hops drawn from the plan, and every window is met starting
    from `t₀`. [algorithm.md §2–§3] -/
def isValidRoute (cp : ContactPlan) (src dst : Node) (t₀ : Time)
    (hops : List Contact) : Bool :=
  !hops.isEmpty
  && (hops.head?.map (·.source) == some src)
  && (hops.getLast?.map (·.dest) == some dst)
  && chainOk hops
  && hops.all (cp.contains ·)
  && (arrivalTime t₀ hops).isSome

end VerifiedSabr
