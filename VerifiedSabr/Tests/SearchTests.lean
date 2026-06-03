import VerifiedSabr.Search

-- Sub-namespace avoids name collision with other test namespaces
namespace VerifiedSabr.Tests.Search

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
def c12   : Contact := { source := "A", dest := "B", tStart := 0,  tEnd := 60, owlt := 1 }
def c34   : Contact := { source := "B", dest := "C", tStart := 0,  tEnd := 60, owlt := 1 }
def c56   : Contact := { source := "A", dest := "C", tStart := 0,  tEnd := 60, owlt := 1 }
def c78   : Contact := { source := "C", dest := "D", tStart := 0,  tEnd := 30, owlt := 1 }
def c910  : Contact := { source := "A", dest := "E", tStart := 10, tEnd := 20, owlt := 1 }
def c1112 : Contact := { source := "D", dest := "E", tStart := 0,  tEnd := 10, owlt := 1 }
def c1314 : Contact := { source := "D", dest := "E", tStart := 30, tEnd := 40, owlt := 1 }
def c1516 : Contact := { source := "D", dest := "E", tStart := 50, tEnd := 60, owlt := 1 }
def tutPlan : ContactPlan := [c12, c34, c56, c78, c910, c1112, c1314, c1516]

#guard routeSearch tutPlan "A" "E" 0 == some [c56, c78, c1112]   -- best route, BDT 3
#guard arrivalTime 0 [c56, c78, c1112] == some 3                 -- Route (1)
#guard arrivalTime 0 [c910]            == some 11                -- Route (2), direct
#guard arrivalTime 0 [c56, c78, c1314] == some 31                -- Route (3)
#guard arrivalTime 0 [c56, c78, c1516] == some 51                -- Route (4)

end VerifiedSabr.Tests.Search
