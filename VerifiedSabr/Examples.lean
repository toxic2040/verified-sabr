import VerifiedSabr.Search

namespace VerifiedSabr.Examples

open VerifiedSabr

-- Tutorial contact plan: Fraire-2021 Fig. 3 (forward contacts only).
-- All contacts: rate = 1, owlt = 1. [algorithm.md §6]
def tutorialPlan : ContactPlan := [
  -- tutorial contacts #1/2
  { source := "A", dest := "B", tStart :=  0, tEnd := 60, owlt := 1, rate := 1 },
  -- tutorial contacts #3/4
  { source := "B", dest := "C", tStart :=  0, tEnd := 60, owlt := 1, rate := 1 },
  -- tutorial contacts #5/6
  { source := "A", dest := "C", tStart :=  0, tEnd := 60, owlt := 1, rate := 1 },
  -- tutorial contacts #7/8
  { source := "C", dest := "D", tStart :=  0, tEnd := 30, owlt := 1, rate := 1 },
  -- tutorial contacts #9/10
  { source := "A", dest := "E", tStart := 10, tEnd := 20, owlt := 1, rate := 1 },
  -- tutorial contacts #11/12
  { source := "D", dest := "E", tStart :=  0, tEnd := 10, owlt := 1, rate := 1 },
  -- tutorial contacts #13/14
  { source := "D", dest := "E", tStart := 30, tEnd := 40, owlt := 1, rate := 1 },
  -- tutorial contacts #15/16
  { source := "D", dest := "E", tStart := 50, tEnd := 60, owlt := 1, rate := 1 }
]

-- Route A→E at t₀=0. Expected: some [#5/6, #7/8, #11/12], arrival 3. [algorithm.md §6]
set_option linter.hashCommand false in
#eval routeSearch tutorialPlan "A" "E" 0

end VerifiedSabr.Examples
