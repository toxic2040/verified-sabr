import VerifiedSabr.Route

-- Sub-namespace avoids name collision with BasicTests' cAB/cBC in VerifiedSabr.Tests
namespace VerifiedSabr.Tests.Route

-- `#guard` is the test idiom of this repo: assertions check at compile time.
set_option linter.hashCommand false

open VerifiedSabr

def cAB : Contact := { source := "A", dest := "B", tStart := 0, tEnd := 10, owlt := 1 }
def cBC : Contact := { source := "B", dest := "C", tStart := 5, tEnd := 20, owlt := 2 }
def cXY : Contact := { source := "X", dest := "Y", tStart := 0, tEnd := 1,  owlt := 1 }
def plan : ContactPlan := [cAB, cBC, cXY]

-- arrival: tx on cAB = max(0,0)=0 ≤ 10, arrive B at 1;
-- tx on cBC = max(1,5)=5 ≤ 20, arrive C at 7.
#guard arrivalTime 0 [cAB, cBC] == some 7
-- missed window: bundle reaches X only at t=5, cXY closed at 1.
#guard arrivalTime 5 [cXY] == none
-- adjacency
#guard chainOk [cAB, cBC] == true
#guard chainOk [cAB, cXY] == false
-- full validity
#guard isValidRoute plan "A" "C" 0 [cAB, cBC] == true
#guard isValidRoute plan "A" "C" 0 [] == false
#guard isValidRoute plan "A" "C" 0 [cAB] == false        -- wrong terminus
#guard isValidRoute plan "B" "C" 0 [cAB, cBC] == false   -- wrong origin
#guard isValidRoute [cAB] "A" "C" 0 [cAB, cBC] == false  -- cBC not in plan

def cAA : Contact := { source := "A", dest := "A", tStart := 0, tEnd := 100, owlt := 1 }
-- algorithm.md §10.3 nonneg-owlt necessity witness: negative-owlt self-loop
-- plus an exit contact whose window closes before any single pass arrives.
def cAAneg : Contact := { source := "A", dest := "A", tStart := -1000, tEnd := 100, owlt := -10 }
def cABlate : Contact := { source := "A", dest := "B", tStart := -1000, tEnd := -15, owlt := 0 }

-- loop erasure (§10.3): with nonneg owlt the splice arrives no later
#guard arrivalTime 0 [cAA, cAA, cAB] == some 3
#guard arrivalTime 0 [cAA, cAB] == some 2
-- §10.3 necessity: with negative owlt the looped route is valid and arrives
-- strictly earlier, while its splice misses the exit window entirely
#guard isValidRoute [cAAneg, cABlate] "A" "B" 0 [cAAneg, cAAneg, cABlate] == true
#guard arrivalTime 0 [cAAneg, cAAneg, cABlate] == some (-20)
#guard arrivalTime 0 [cAAneg, cABlate] == none

end VerifiedSabr.Tests.Route
