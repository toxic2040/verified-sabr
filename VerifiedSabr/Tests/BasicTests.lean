import VerifiedSabr.Basic

namespace VerifiedSabr.Tests

open VerifiedSabr

def cAB : Contact :=
  { source := "A", dest := "B", tStart := 0, tEnd := 10, owlt := 1 }

#guard cAB.source == "A"
#guard cAB.tEnd == (10 : Time)
#guard ([cAB] : ContactPlan).length == 1

end VerifiedSabr.Tests
