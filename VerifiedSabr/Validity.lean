import VerifiedSabr.Search

namespace VerifiedSabr

/-- T1a: anything `routeSearch` returns passes the validity check.
    Near-definitional by the certifying pattern; stated as the public API
    guarantee. [algorithm.md §3] -/
theorem routeSearch_sound (cp : ContactPlan) (src dst : Node) (t₀ : Time)
    (hops : List Contact) (h : routeSearch cp src dst t₀ = some hops) :
    isValidRoute cp src dst t₀ hops = true := by
  unfold routeSearch at h
  simp only at h
  split at h
  · split at h
    · simp_all
    · simp_all
  · simp_all

end VerifiedSabr
