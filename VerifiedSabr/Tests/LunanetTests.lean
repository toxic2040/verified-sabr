import VerifiedSabr.Examples.Lunanet

-- Sub-namespace avoids name collision with other test namespaces
namespace VerifiedSabr.Tests.Lunanet

-- `#guard` is the test idiom of this repo: assertions check at compile time.
set_option linter.hashCommand false

open VerifiedSabr
open VerifiedSabr.Examples (lunanetPlan)

-- The generated lunar-relay plan loads with all 418 directed contacts.
#guard lunanetPlan.length == 418

/- Route searches below run on a slice, not the full plan: the v1 search
   enumerates routes without dominance pruning, and interpreter evaluation on
   the full 418-contact day exceeds practical elaboration time (>26 min
   observed). Full-plan search belongs to the compiled differential harness
   (plan 2). The first four slice rows are verbatim members of `lunanetPlan`
   (mechanically checked by the containment guard below), so the searched
   contacts are real generated data, plus one decoy that opens too late. -/
def lunanetSlice : ContactPlan := [
  { source := "GATEWAY", dest := "NAVSAT-3", tStart := 0, tEnd := 43192,
    owlt := 26/1000, rate := 314 },
  { source := "NAVSAT-3", dest := "SHACKLETON", tStart := 0, tEnd := 34369,
    owlt := 41/1000, rate := 940 },
  { source := "NAVSAT-4", dest := "CANBERRA", tStart := 0, tEnd := 19557,
    owlt := 1153/1000, rate := 16121978 },
  { source := "SHACKLETON", dest := "NAVSAT-4", tStart := 0, tEnd := 6399,
    owlt := 37/1000, rate := 1269 },
  -- decoy: window opens after the surface uplink above has closed
  { source := "SHACKLETON", dest := "NAVSAT-1", tStart := 50000, tEnd := 50001,
    owlt := 37/1000, rate := 1269 }
]

-- Every slice row except the decoy is a verbatim member of the full plan.
#guard (lunanetSlice.take 4).all (lunanetPlan.contains ·)

-- Surface-to-ground route exists through the relay layer from t₀ = 0.
#guard (routeSearch lunanetSlice "SHACKLETON" "CANBERRA" 0).isSome

-- The orbital-station-to-surface direction routes as well.
#guard (routeSearch lunanetSlice "GATEWAY" "SHACKLETON" 0).isSome

-- Whatever the search returns passes the validity predicate backing T1.
#guard (routeSearch lunanetSlice "SHACKLETON" "CANBERRA" 0).all
  (isValidRoute lunanetSlice "SHACKLETON" "CANBERRA" 0)

-- Unreachable endpoint name: search must return none, not a junk route.
#guard routeSearch lunanetSlice "SHACKLETON" "NOSUCHNODE" 0 == none

end VerifiedSabr.Tests.Lunanet
