import VerifiedSabr.LoopSearch

-- Sub-namespace avoids name collision with other test namespaces.
namespace VerifiedSabr.Tests.LoopSearch

-- `#guard` is the test idiom of this repo: assertions check at compile time.
set_option linter.hashCommand false

open VerifiedSabr VerifiedSabr.LoopSearch

-- T3b-extended mechanical search outcome: EXHAUSTION. [algorithm.md §11.1]
-- The real `forward` produced no node revisit over any of the three engineered
-- tie families. These guards pin the zero-revisit result and the family sizes
-- so a regression in `routeSearch`/`forwardStep` that introduced a revisit
-- would fail the build.

-- Family I (nodes A–E, broad menu): no revisit over the running trajectories.
#guard hitsI.length == 0
#guard plansI.length == 49152
#guard ranI.length == 22272

-- Family II (numeric nodes 1–4, key-3/key-4 targeted): no revisit, and the
-- family is NON-VACUOUS — 432 running plans carry the engineered arm-tie to
-- the join node (long arm 1→2→3→4, 3 hops, arrival-tied with short arm 1→4,
-- 1 hop). The tie the obstruction names is present; it just never flips a
-- first hop backward.
#guard hitsII.length == 0
#guard plansII.length == 27648
#guard ranII.length == 12744
#guard tieII.length == 432

-- Family III (per-contact asymmetric owlt): no revisit.
#guard hitsIII.length == 0
#guard plansIII.length == 4374
#guard ranIII.length == 4374

-- vPlan, the §8.3 route-shape identity witness, lifts to a clean forward walk:
-- the returned 4-hop route [p1,p2,s,t] forwards A→B→C→D→E with no revisit. The
-- route-shape finding does NOT become a forwarding loop. [algorithm.md §11.1]
def vP1 : Contact := mkC "A" "B" 0 100 1
def vP2 : Contact := mkC "B" "C" 0 100 1
def vQ1 : Contact := mkC "A" "C" 0 100 3
def vS : Contact := mkC "C" "D" 0 100 1
def vT : Contact := mkC "D" "E" 5 100 1
def vPlan : ContactPlan := [vP1, vP2, vQ1, vS, vT]
#guard trajNodes vPlan "E" 30 "A" 0 == ["A", "B", "C", "D", "E"]
#guard hasRevisit vPlan "E" "A" 0 30 == false

-- Mechanism pin (the obstruction, made concrete). A single search CAN return a
-- backward first hop: with B's forward edge B→C closed by B's arrival time,
-- B's own search to D goes back through A — [B→A, A→C, C→D]. But the trajectory
-- from A NEVER routes through B: A's arrival-optimal route is [A→C, C→D], so
-- custody skips B entirely and the would-be loop is unreachable. This is why
-- the search exhausts: custody only lands on the first hop of a complete route
-- the predecessor already selected, and the configuration that makes a node
-- route backward (no open forward edge) is exactly the one that removes it from
-- every complete route the predecessor could pick. [algorithm.md §11.1]
def mAB : Contact := mkC "A" "B" 0 100 1
def mBA : Contact := mkC "B" "A" 0 100 1
def mAC : Contact := mkC "A" "C" 0 100 1
def mBC : Contact := mkC "B" "C" 0 0 1     -- B→C open only at exactly t=0
def mCD : Contact := mkC "C" "D" 0 100 1
def forcedPlan : ContactPlan := [mAB, mBA, mAC, mBC, mCD]
-- B in isolation routes backward (B arrives at 1, B→C already closed):
#guard routeSearch forcedPlan "B" "D" 1 == some [mBA, mAC, mCD]
-- the trajectory from A routes around B — no revisit:
#guard trajNodes forcedPlan "D" 20 "A" 0 == ["A", "C", "D"]
#guard hasRevisit forcedPlan "D" "A" 0 20 == false
#guard routeSearch forcedPlan "A" "D" 0 == some [mAC, mCD]

end VerifiedSabr.Tests.LoopSearch
