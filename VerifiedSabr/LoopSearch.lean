import VerifiedSabr.Forwarding

/-!
T3b-extended mechanical loop-construction search. Enumerates the engineered
tie families of algorithm.md §11.1 and runs the real `forward` per candidate,
detecting node revisits. Tooling, not a model of the standard: it computes
over the verified `forward`/`routeSearch`, so any revisit it reports is a fact
about those definitions. Outcome (2026-06-05): exhaustion — no revisit over
the family. Reading in docs/notes/2026-06-05-t3b-extended-search.md.
-/

namespace VerifiedSabr.LoopSearch

open VerifiedSabr

/-- The custodian-node sequence of a §11 trajectory, capped by `fuel`.
    [algorithm.md §11.1] -/
def trajNodes (cp : ContactPlan) (dst : Node) :
    Nat → Node → Time → List Node
  | 0, x, _ => [x]
  | fuel + 1, x, t =>
      if x = dst then [x]
      else
        match forwardStep cp dst x t with
        | none => [x]
        | some (y, t') => x :: trajNodes cp dst fuel y t'

/-- Does a §11 trajectory from `(src, t₀)` toward `dst` revisit a node?
    Steps the real `forwardStep`; a revisit is the first hand-off to a node
    already in the visited prefix. [algorithm.md §11.1] -/
def hasRevisit (cp : ContactPlan) (dst src : Node) (t₀ : Time)
    (fuel : Nat) : Bool :=
  let rec go : Nat → Node → Time → List Node → Bool
    | 0, _, _, _ => false
    | fuel + 1, x, t, seen =>
        if x = dst then false
        else
          match forwardStep cp dst x t with
          | none => false
          | some (y, t') => (x :: seen).contains y || go fuel y t' (x :: seen)
  go fuel src t₀ []

/-- Convenience contact builder for the search families. -/
def mkC (s d : Node) (ts te o : Time) : Contact :=
  { source := s, dest := d, tStart := ts, tEnd := te, owlt := o }

/-- Power set, used to enumerate present/absent menu contacts. -/
def subsets {α : Type} : List α → List (List α)
  | [] => [[]]
  | x :: xs => (subsets xs).flatMap (fun s => [s, x :: s])

/-! ## Family I — node alphabet A–E, dst E, broad menu

Forward edges, back edges, a join node C reached two ways, and a gated final
contact D→E (the `vPlan` tie-forcer). Window gate `g` and owlt `o1`/`o2`
parameterized. [algorithm.md §11.1] -/

def menuI (g o1 o2 : Time) : List Contact := [
  mkC "A" "B" 0 100 o1, mkC "A" "C" 0 100 o2, mkC "B" "C" 0 100 o1,
  mkC "B" "A" g 100 o1, mkC "C" "A" g 100 o1, mkC "C" "B" g 100 o1,
  mkC "C" "D" 0 100 o1, mkC "B" "D" 0 100 o2, mkC "D" "E" g 100 o1,
  mkC "C" "E" 0 100 o2 ]

def owltVals : List Time := [0, 1, 2, 3]
def gateValsI : List Time := [0, 2, 5]

def settingsI : List (Time × Time × Time) :=
  gateValsI.flatMap (fun g =>
    owltVals.flatMap (fun o1 => owltVals.map (fun o2 => (g, o1, o2))))

def plansI : List (List Contact) :=
  settingsI.flatMap (fun s => subsets (menuI s.1 s.2.1 s.2.2))

/-! ## Family II — numeric nodes 1–4, dst 9, key-3/key-4 targeted

Two arms to join node 4 of differing hop count (long 1→2→3→4, short 1→4),
arrival-tied through gated final 4→9; back edges from 4; termination times
varied to drive key 3, numeric ids to drive key 4. [algorithm.md §11.1] -/

def menuII (g o te1 te2 : Time) : List Contact := [
  mkC "1" "2" 0 te1 o, mkC "2" "3" 0 te2 o, mkC "3" "4" 0 te1 o,
  mkC "1" "4" 0 te2 o, mkC "4" "1" g te1 o, mkC "4" "2" g te2 o,
  mkC "4" "3" g te1 o, mkC "2" "4" 0 te2 o, mkC "4" "9" g 100 o,
  mkC "3" "9" 0 100 o ]

def owltValsII : List Time := [0, 1, 2]
def gateValsII : List Time := [0, 3, 6]
def teVals : List (Time × Time) := [(10, 20), (20, 10), (50, 50)]

def settingsII : List (Time × Time × (Time × Time)) :=
  gateValsII.flatMap (fun g =>
    owltValsII.flatMap (fun o => teVals.map (fun te => (g, o, te))))

def plansII : List (List Contact) :=
  settingsII.flatMap (fun s => subsets (menuII s.1 s.2.1 s.2.2.1 s.2.2.2))

/-- Engineered arm-tie present: the long arm 1→2→3→4 (3 hops) and the short
    arm 1→4 (1 hop) both exist and arrive at the join node at the same time —
    the differing-hop-count interior tie the obstruction names. Makes the
    family non-vacuous. [algorithm.md §11.1] -/
def hasEngineeredTie (cp : ContactPlan) : Bool :=
  let c12 := cp.find? (fun c => c.source == "1" && c.dest == "2")
  let c23 := cp.find? (fun c => c.source == "2" && c.dest == "3")
  let c34 := cp.find? (fun c => c.source == "3" && c.dest == "4")
  let c14 := cp.find? (fun c => c.source == "1" && c.dest == "4")
  match c12, c23, c34, c14 with
  | some a, some b, some c, some d =>
      match arrivalTime 0 [a, b, c], arrivalTime 0 [d] with
      | some x, some y => decide (x = y)
      | _, _ => false
  | _, _, _, _ => false

/-! ## Family III — per-contact asymmetric owlt

Each of six edges over nodes 1–3 (with dst 9) draws its owlt independently,
stressing custody-shift's owlt dependence; gated final 3→9. [algorithm.md §11.1] -/

def edgeShapesIII : List (Node × Node × Time × Time) := [
  ("1","2",0,100), ("2","3",0,100), ("1","3",0,100),
  ("2","1",0,100), ("3","1",0,100), ("3","2",0,100) ]

def finalsIII (g o : Time) : List Contact := [ mkC "3" "9" g 100 o, mkC "2" "9" 0 100 o ]

def owltValsIII : List Time := [0, 1, 2]
def gateValsIII : List Time := [0, 4]

/-- All length-6 owlt assignments over `owltValsIII`. -/
def owltAssignments : List (List Time) :=
  let rec go : Nat → List (List Time)
    | 0 => [[]]
    | n + 1 => (go n).flatMap (fun rest => owltValsIII.map (fun o => o :: rest))
  go 6

def buildPlanIII (assign : List Time) (g of : Time) : ContactPlan :=
  (edgeShapesIII.zip assign).map
    (fun p => mkC p.1.1 p.1.2.1 p.1.2.2.1 p.1.2.2.2 p.2) ++ finalsIII g of

def plansIII : List (List Contact) :=
  gateValsIII.flatMap (fun g =>
    owltValsIII.flatMap (fun of => owltAssignments.map (fun a => buildPlanIII a g of)))

/-! ## Search results

`#eval` reports rather than `#guard`: the counts document the searched family.
Guard pins (the load-bearing zero-revisit assertions and the non-vacuity
witness) live in `Tests/LoopSearchTests.lean`. -/

def ranI : List (List Contact) := plansI.filter (fun cp => (forwardStep cp "E" "A" 0).isSome)
def hitsI : List (List Contact) := ranI.filter (fun cp => hasRevisit cp "E" "A" 0 30)

def ranII : List (List Contact) := plansII.filter (fun cp => (forwardStep cp "9" "1" 0).isSome)
def hitsII : List (List Contact) := ranII.filter (fun cp => hasRevisit cp "9" "1" 0 40)
def tieII : List (List Contact) := ranII.filter hasEngineeredTie

def ranIII : List (List Contact) := plansIII.filter (fun cp => (forwardStep cp "9" "1" 0).isSome)
def hitsIII : List (List Contact) := ranIII.filter (fun cp => hasRevisit cp "9" "1" 0 40)

set_option linter.hashCommand false

#eval s!"Family I:   {plansI.length} plans, {ranI.length} ran, {hitsI.length} revisits"
#eval s!"Family II:  {plansII.length} plans, {ranII.length} ran, {hitsII.length} revisits"
#eval s!"Family II engineered ties (non-vacuity): {tieII.length}"
#eval s!"Family III: {plansIII.length} plans, {ranIII.length} ran, {hitsIII.length} revisits"

end VerifiedSabr.LoopSearch
