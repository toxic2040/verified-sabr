import VerifiedSabr.Examples.Lunanet

-- Sub-namespace avoids name collision with other test namespaces
namespace VerifiedSabr.Tests.Lunanet

-- `#guard` is the test idiom of this repo: assertions check at compile time.
set_option linter.hashCommand false

open VerifiedSabr
open VerifiedSabr.Examples (lunanetPlan)

-- The generated lunar-relay plan loads with all 398 directed contacts.
#guard lunanetPlan.length == 398

/- Route searches run on the FULL generated day: the visited-contact list
   (algorithm.md §8) makes whole-plan search elaborate in seconds, where the
   v1 search exceeded 26 minutes and had to be guarded on a 5-row slice.
   The unreachable-endpoint check uses a junk SOURCE: a junk destination
   forces the search to exhaust the entire reachable space (the worst case,
   exercised in the differential harness), while a junk source exhausts
   immediately — same `none` contract, compile-time-friendly cost. -/

-- Surface-to-ground route exists through the relay layer from t₀ = 0.
#guard (routeSearch lunanetPlan "SHACKLETON" "CANBERRA" 0).isSome

-- The orbital-station-to-surface direction routes as well.
#guard (routeSearch lunanetPlan "GATEWAY" "SHACKLETON" 0).isSome

-- Whatever the search returns passes the validity predicate backing T1.
#guard (routeSearch lunanetPlan "SHACKLETON" "CANBERRA" 0).all
  (isValidRoute lunanetPlan "SHACKLETON" "CANBERRA" 0)
#guard (routeSearch lunanetPlan "GATEWAY" "SHACKLETON" 0).all
  (isValidRoute lunanetPlan "GATEWAY" "SHACKLETON" 0)

-- Unreachable endpoint name: search must return none, not a junk route.
#guard routeSearch lunanetPlan "NOSUCHNODE" "SHACKLETON" 0 == none

end VerifiedSabr.Tests.Lunanet
