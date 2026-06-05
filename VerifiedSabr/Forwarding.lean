import VerifiedSabr.Search
import Mathlib.Algebra.Order.Ring.Unbundled.Rat

namespace VerifiedSabr

/-- Strictly positive OWLT, the §7 loop-freedom hypothesis. `Contact.owlt`
    stays an unconstrained rational so theorem boundaries remain statable;
    this is the physical regime where propagation dominates.
    [algorithm.md §7, §11] -/
def PlanPosOwlt (cp : ContactPlan) : Prop :=
  ∀ c ∈ cp, 0 < c.owlt

/-- Executable checker for `PlanPosOwlt`, used at import/test boundaries.
    [algorithm.md §11] -/
def checkPlanPosOwlt (cp : ContactPlan) : Bool :=
  cp.all fun c => decide (0 < c.owlt)

theorem checkPlanPosOwlt_eq_true {cp : ContactPlan} :
    checkPlanPosOwlt cp = true ↔ PlanPosOwlt cp := by
  unfold checkPlanPosOwlt PlanPosOwlt
  rw [List.all_eq_true]
  constructor
  · intro h c hc
    exact of_decide_eq_true (h c hc)
  · intro h c hc
    exact decide_eq_true (h c hc)

/-- Strict positivity hands the T2 results their nonnegativity hypothesis.
    [algorithm.md §11] -/
theorem PlanPosOwlt.nonneg {cp : ContactPlan} (h : PlanPosOwlt cp) :
    PlanNonnegOwlt cp :=
  fun c hc => le_of_lt (h c hc)

/-- Outcome of a fuel-indexed forwarding run: delivery at the destination,
    a halt where no route exists, or fuel exhaustion (the artifact
    T3a-term eliminates for sufficient fuel). [algorithm.md §11] -/
inductive ForwardOutcome where
  | delivered (t : Time)
  | halted (node : Node) (t : Time)
  | exhausted (node : Node) (t : Time)
  deriving Repr, BEq, DecidableEq

/-- One §3.2.8 forwarding step from custodian `x` at local time `t`:
    route, then hand custody across the returned route's first hop at the
    §3.2.4.1 arrival. `none` when no route is returned. The empty-route
    arm is defensive: T1 guarantees returned routes are nonempty, and the
    arm is discharged when that fact is consumed (T3a line).
    [algorithm.md §11] -/
def forwardStep (cp : ContactPlan) (dst : Node) (x : Node) (t : Time) :
    Option (Node × Time) :=
  match routeSearch cp x dst t with
  | none => none
  | some [] => none
  | some (c :: _) => some (c.dest, max t c.tStart + c.owlt)

/-- Fuel-indexed forwarding trajectory: deliver at the destination before
    routing (Delta 6: `routeSearch` answers `none` for `src = dst`), halt
    when no route is returned, otherwise step and recurse.
    [algorithm.md §11] -/
def forward (cp : ContactPlan) (dst : Node) :
    Nat → Node → Time → ForwardOutcome
  | 0, x, t => .exhausted x t
  | fuel + 1, x, t =>
      if x = dst then .delivered t
      else
        match forwardStep cp dst x t with
        | none => .halted x t
        | some (y, t') => forward cp dst fuel y t'

end VerifiedSabr
