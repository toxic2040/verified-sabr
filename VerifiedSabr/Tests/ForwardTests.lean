import VerifiedSabr.Forwarding

-- Sub-namespace avoids name collision with other test namespaces
namespace VerifiedSabr.Tests.Forward

-- `#guard` is the test idiom of this repo: assertions check at compile time.
set_option linter.hashCommand false

open VerifiedSabr

-- Forwarding fixture. [algorithm.md §11; T3a plan anchors]
-- f1+f2 (arrival 5) beats the direct f3 (arrival 9); custody A→B at 2,
-- B→C at 5, delivered. Positive owlt throughout.
def f1 : Contact := { source := "A", dest := "B", tStart := 0, tEnd := 100, owlt := 2 }
def f2 : Contact := { source := "B", dest := "C", tStart := 0, tEnd := 100, owlt := 3 }
def f3 : Contact := { source := "A", dest := "C", tStart := 0, tEnd := 100, owlt := 9 }
def fwdPlan : ContactPlan := [f1, f2, f3]

#guard checkPlanPosOwlt fwdPlan == true
#guard checkPlanPosOwlt [f1, { f2 with owlt := 0 }] == false

#guard routeSearch fwdPlan "A" "C" 0 == some [f1, f2]
#guard forwardStep fwdPlan "C" "A" 0 == some ("B", 2)
#guard forwardStep fwdPlan "C" "B" 2 == some ("C", 5)
#guard forward fwdPlan "C" 10 "A" 0 == ForwardOutcome.delivered 5
-- termination-bound sanity: delta = 2, Tmax = 100, bound 51 ≥ 2 steps used
#guard forward fwdPlan "C" 51 "A" 0 == ForwardOutcome.delivered 5
-- fuel exhaustion is observable below the bound
#guard forward fwdPlan "C" 1 "A" 0 == ForwardOutcome.exhausted "B" 2
-- a custodian with no route halts; delivered-at-start needs no fuel beyond one
#guard forward fwdPlan "C" 10 "Z" 0 == ForwardOutcome.halted "Z" 0
#guard forward fwdPlan "C" 10 "C" 7 == ForwardOutcome.delivered 7

end VerifiedSabr.Tests.Forward
