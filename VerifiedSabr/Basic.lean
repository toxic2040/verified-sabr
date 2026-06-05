import Mathlib.Data.Rat.Defs

namespace VerifiedSabr

/-- Node identifier. String form of DTN endpoint IDs. [algorithm.md §1] -/
abbrev Node := String

/-- All times are exact rationals; keeps every comparison decidable and the
    whole model executable. [design spec, Model] -/
abbrev Time := ℚ

/-- A scheduled communication contact. [algorithm.md §1]
    `owlt` is the range (one-way light time) in light seconds for THIS contact's
    sending/receiving node pair over its window, pre-joined from the Blue Book's
    range-interval table (§2.3.1, looked up by §3.2.4.1.2). Forward and reverse
    contacts of one bidirectional link are distinct contacts; do not assume a
    node-symmetric constant. [algorithm.md §1, Lean modeling note]
    `rate` is reserved for the EVL decision (algorithm.md §4); unused by the
    baseline route search. -/
structure Contact where
  source : Node
  dest   : Node
  tStart : Time
  tEnd   : Time
  owlt   : Time
  rate   : ℚ := 0
  deriving Repr, DecidableEq, BEq, ReflBEq, LawfulBEq

/-- A contact plan is a finite list of contacts. [algorithm.md §1] -/
abbrev ContactPlan := List Contact

/-- Physical contact-plan invariant: every contact's range/OWLT is
    nonnegative. `Contact.owlt` remains a rational field so invalid
    counterexamples can state theorem boundaries directly. [algorithm.md §10.3] -/
def PlanNonnegOwlt (cp : ContactPlan) : Prop :=
  ∀ c ∈ cp, 0 ≤ c.owlt

/-- Executable checker for `PlanNonnegOwlt`, used at import/test boundaries.
    [algorithm.md §10.3] -/
def checkPlanNonnegOwlt (cp : ContactPlan) : Bool :=
  cp.all fun c => decide (0 ≤ c.owlt)

theorem checkPlanNonnegOwlt_eq_true {cp : ContactPlan} :
    checkPlanNonnegOwlt cp = true ↔ PlanNonnegOwlt cp := by
  unfold checkPlanNonnegOwlt PlanNonnegOwlt
  rw [List.all_eq_true]
  constructor
  · intro h c hc
    exact of_decide_eq_true (h c hc)
  · intro h c hc
    exact decide_eq_true (h c hc)

end VerifiedSabr
