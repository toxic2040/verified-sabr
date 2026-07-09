import VerifiedSabr

/-!
Axiom audit for the two headline theorems.

`#print axioms` reports the kernel axioms each proof transitively depends on.
Both `routeSearch_sound` (Validity.lean) and `routeSearch_optimal`
(Optimality.lean) reduce to the standard classical trio — `propext`,
`Classical.choice`, `Quot.sound` — with no `sorryAx` and no project-local
axiom. This file is built on every `lake build`, so any drift in the axiom
footprint of the soundness or arrival-optimality proof surfaces in the build
output.
-/

set_option linter.hashCommand false

#print axioms VerifiedSabr.routeSearch_sound
#print axioms VerifiedSabr.routeSearch_optimal
