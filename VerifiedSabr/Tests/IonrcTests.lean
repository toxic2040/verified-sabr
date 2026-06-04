import VerifiedSabr.Ionrc

namespace VerifiedSabr.Tests.Ionrc

open VerifiedSabr

set_option linter.hashCommand false

/-- The tutorial plan (algorithm.md §6) in ionrc form, nodes A..E as 1..5 —
    same content as scripts/diffharness/fixtures/toy.ionrc. -/
def fixture : String :=
  "a contact +0 +60 1 2 1\na range +0 +60 1 2 1\n" ++
  "a contact +0 +60 2 3 1\na range +0 +60 2 3 1\n" ++
  "a contact +0 +60 1 3 1\na range +0 +60 1 3 1\n" ++
  "a contact +0 +30 3 4 1\na range +0 +30 3 4 1\n" ++
  "a contact +10 +20 1 5 1\na range +10 +20 1 5 1\n" ++
  "a contact +0 +10 4 5 1\na range +0 +10 4 5 1\n" ++
  "a contact +30 +40 4 5 1\na range +30 +40 4 5 1\n" ++
  "a contact +50 +60 4 5 1\na range +50 +60 4 5 1\n"

/-- Parsed form of the fixture. -/
def plan : ContactPlan :=
  buildPlan ((fixture.splitOn "\n").filterMap parseLine?)

#guard plan.length == 8
-- every contact picked up its paired range (owlt 1 everywhere in the fixture)
#guard plan.all (fun c => c.owlt == 1)
-- tutorial expectation in numbered form: 1→5 at t=0 arrives at 3
#guard (routeSearch plan "1" "5" 0).isSome
#guard ((routeSearch plan "1" "5" 0).bind (arrivalTime 0)) == some 3
-- malformed and comment lines are skipped, not fatal
#guard (buildPlan ((("# x\n\nnot a line\n" ++ fixture).splitOn "\n").filterMap
  parseLine?)).length == 8
-- a contact with no matching range line gets owlt 0
#guard (buildPlan (("a contact +0 +9 7 8 5".splitOn "\n").filterMap
  parseLine?)).all (fun c => c.owlt == 0)

end VerifiedSabr.Tests.Ionrc
