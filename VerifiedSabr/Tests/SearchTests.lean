import VerifiedSabr.Search

-- Sub-namespace avoids name collision with other test namespaces
namespace VerifiedSabr.Tests.Search

-- `#guard` is the test idiom of this repo: assertions check at compile time.
set_option linter.hashCommand false

open VerifiedSabr

def cAB : Contact := { source := "A", dest := "B", tStart := 0, tEnd := 10, owlt := 1 }
def cBC : Contact := { source := "B", dest := "C", tStart := 5, tEnd := 20, owlt := 2 }
def cAC : Contact := { source := "A", dest := "C", tStart := 30, tEnd := 40, owlt := 1 }
def plan : ContactPlan := [cAB, cBC, cAC]

-- two-hop route arrives at 7; direct contact only at 31. Search must pick the two-hop.
#guard routeSearch plan "A" "C" 0 == some [cAB, cBC]
-- start at t₀=25: cAB tx=25>10 infeasible; cAC tx=30 ≤ 40, arrive 31.
#guard routeSearch plan "A" "C" 25 == some [cAC]
-- unreachable destination
#guard routeSearch plan "A" "Z" 0 == none
-- src = dst: no route needed; defined as none (no hops). [algorithm.md §3]
#guard routeSearch plan "A" "A" 0 == none
-- whatever is returned passes the validity check
#guard (routeSearch plan "A" "C" 0).all (isValidRoute plan "A" "C" 0)

-- Worked example: Tutorial Fig. 3, A→E, t₀ = 0. [algorithm.md §6]
-- All contacts: rate = 1, owlt = 1.
def c12 : Contact :=
  { source := "A", dest := "B", tStart := 0, tEnd := 60, owlt := 1, rate := 1 }
def c34 : Contact :=
  { source := "B", dest := "C", tStart := 0, tEnd := 60, owlt := 1, rate := 1 }
def c56 : Contact :=
  { source := "A", dest := "C", tStart := 0, tEnd := 60, owlt := 1, rate := 1 }
def c78 : Contact :=
  { source := "C", dest := "D", tStart := 0, tEnd := 30, owlt := 1, rate := 1 }
def c910 : Contact :=
  { source := "A", dest := "E", tStart := 10, tEnd := 20, owlt := 1, rate := 1 }
def c1112 : Contact :=
  { source := "D", dest := "E", tStart := 0, tEnd := 10, owlt := 1, rate := 1 }
def c1314 : Contact :=
  { source := "D", dest := "E", tStart := 30, tEnd := 40, owlt := 1, rate := 1 }
def c1516 : Contact :=
  { source := "D", dest := "E", tStart := 50, tEnd := 60, owlt := 1, rate := 1 }
def tutPlan : ContactPlan := [c12, c34, c56, c78, c910, c1112, c1314, c1516]

#guard routeSearch tutPlan "A" "E" 0 == some [c56, c78, c1112]   -- best route, BDT 3
#guard arrivalTime 0 [c56, c78, c1112] == some 3                 -- Route (1)
#guard arrivalTime 0 [c910]            == some 11                -- Route (2), direct
#guard arrivalTime 0 [c56, c78, c1314] == some 31                -- Route (3)
#guard arrivalTime 0 [c56, c78, c1516] == some 51                -- Route (4)

-- Visited-list pins. [algorithm.md §8]
-- A slower duplicate path into the same forwarding contact must not change
-- the result: B is reachable via dAB1 (arrive 1) and dAB2 (arrive 6); the
-- continuation dBC closes after first expansion and the answer stays the
-- earliest-arrival route.
def dAB1 : Contact := { source := "A", dest := "B", tStart := 0, tEnd := 10, owlt := 1 }
def dAB2 : Contact := { source := "A", dest := "B", tStart := 5, tEnd := 15, owlt := 1 }
def dBC : Contact := { source := "B", dest := "C", tStart := 0, tEnd := 30, owlt := 1 }
def dupPlan : ContactPlan := [dAB1, dAB2, dBC]

#guard ((routeSearch dupPlan "A" "C" 0).bind (arrivalTime 0)) == some 2
#guard routeSearch dupPlan "A" "C" 0 == some [dAB1, dBC]
-- regression: the tutorial expectation survives the visited-list refit
#guard ((routeSearch tutPlan "A" "E" 0).bind (arrivalTime 0)) == some 3

-- §3.2.8.1.4 key 2 (fewest contacts) on an arrival tie: owlt-0 contacts make
-- both A→C paths arrive at 0; the 1-hop route must beat the 2-hop walk.
def zAB : Contact := { source := "A", dest := "B", tStart := 0, tEnd := 10, owlt := 0 }
def zBC : Contact := { source := "B", dest := "C", tStart := 0, tEnd := 10, owlt := 0 }
def zAC : Contact := { source := "A", dest := "C", tStart := 0, tEnd := 10, owlt := 0 }
def zeroPlan : ContactPlan := [zAB, zBC, zAC]

#guard routeSearch zeroPlan "A" "C" 0 == some [zAC]
#guard ((routeSearch zeroPlan "A" "C" 0).bind (arrivalTime 0)) == some 0

-- §3.2.8.1.4 key 3 (latest termination time). [algorithm.md §10.1]
-- Both A→C routes arrive at 3 with 2 hops; terminations 10 vs 8. The
-- term-10 route must win with the loser listed FIRST in the plan, so list
-- order cannot be the explanation.
def k3a1 : Contact := { source := "A", dest := "B1", tStart := 0, tEnd := 10, owlt := 1 }
def k3a2 : Contact := { source := "B1", dest := "C", tStart := 2, tEnd := 20, owlt := 1 }
def k3b1 : Contact := { source := "A", dest := "B2", tStart := 0, tEnd := 8, owlt := 1 }
def k3b2 : Contact := { source := "B2", dest := "C", tStart := 2, tEnd := 30, owlt := 1 }
def k3Plan : ContactPlan := [k3b1, k3b2, k3a1, k3a2]

#guard routeSearch k3Plan "A" "C" 0 == some [k3a1, k3a2]
#guard ((routeSearch k3Plan "A" "C" 0).bind (arrivalTime 0)) == some 3

-- §3.2.8.1.4 key 4 (smallest entry node). [algorithm.md §10.1]
-- Keys 1–3 all tie (arrival 3, 2 hops, termination 10); entry "B1" < "B2"
-- must decide, under both plan orderings.
def k4a1 : Contact := { source := "A", dest := "B1", tStart := 0, tEnd := 10, owlt := 1 }
def k4a2 : Contact := { source := "B1", dest := "C", tStart := 2, tEnd := 20, owlt := 1 }
def k4b1 : Contact := { source := "A", dest := "B2", tStart := 0, tEnd := 20, owlt := 1 }
def k4b2 : Contact := { source := "B2", dest := "C", tStart := 2, tEnd := 10, owlt := 1 }

#guard routeSearch [k4b1, k4b2, k4a1, k4a2] "A" "C" 0 == some [k4a1, k4a2]
#guard routeSearch [k4a1, k4a2, k4b1, k4b2] "A" "C" 0 == some [k4a1, k4a2]

-- le4 unit pins on hand-built candidates (hops most-recent-first).
-- [algorithm.md §10.1]
def candR1 : Cand := { hops := [k3a2, k3a1], arrival := 3 }  -- term 10, entry B1
def candR2 : Cand := { hops := [k3b2, k3b1], arrival := 3 }  -- term 8,  entry B2
def candS1 : Cand := { hops := [k4a2, k4a1], arrival := 3 }  -- term 10, entry B1
def candS2 : Cand := { hops := [k4b2, k4b1], arrival := 3 }  -- term 10, entry B2
def candRoot : Cand := { hops := [], arrival := 0 }

#guard candR1.termTime == some 10
#guard candR2.termTime == some 8
#guard candR1.entry == some "B1"
#guard candRoot.termTime == none
#guard candRoot.entry == none
#guard candR1.le4 candR2 == true      -- key 3 decides: 10 > 8
#guard candR2.le4 candR1 == false
#guard candS1.le4 candS2 == true      -- key 4 decides: "B1" ≤ "B2"
#guard candS2.le4 candS1 == false
#guard candS1.le4 candS1 == true      -- full tie resolves left (total)
#guard termLater none (some 10) == true   -- root outlasts any bounded term
#guard entryLE none (some "B1") == true   -- root ordered first

end VerifiedSabr.Tests.Search
