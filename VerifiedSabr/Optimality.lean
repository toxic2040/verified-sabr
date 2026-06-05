import VerifiedSabr.Validity
import Mathlib.Data.List.Nodup

namespace VerifiedSabr

/-- The 4-key order respects key 1: a smaller candidate never has a larger
    arrival. [algorithm.md §10.1] -/
theorem le4_arrival_le {c m : Cand} (h : c.le4 m = true) :
    c.arrival ≤ m.arrival := by
  simp only [Cand.le4, Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_iff,
    beq_iff_eq] at h
  rcases h with h | ⟨h, _⟩
  · exact le_of_lt h
  · exact le_of_eq h

/-- `pickMin` is an exact extraction: every input member is the minimum or a
    remainder member. [algorithm.md §3.5] -/
theorem pickMin_cover : ∀ {l : List Cand} {m : Cand} {rest : List Cand},
    pickMin l = some (m, rest) → ∀ x ∈ l, x = m ∨ x ∈ rest := by
  intro l
  induction l with
  | nil => intro m rest h; simp [pickMin] at h
  | cons c tl ih =>
      intro m rest h x hx
      simp only [pickMin] at h
      cases hp : pickMin tl with
      | none =>
          rw [hp] at h
          simp only [Option.some.injEq, Prod.mk.injEq, List.nil_eq] at h
          obtain ⟨hm, hrest⟩ := h
          have htl := pickMin_eq_none hp
          subst htl
          rcases List.mem_cons.1 hx with h1 | h1
          · exact Or.inl (h1.trans hm)
          · simp at h1
      | some mo =>
          obtain ⟨mm, others⟩ := mo
          rw [hp] at h
          dsimp only at h
          split at h
          · injection h with hpair
            injection hpair with hm hrest
            rcases List.mem_cons.1 hx with h1 | h1
            · exact Or.inl (h1.trans hm)
            · right; rw [← hrest]; exact h1
          · injection h with hpair
            injection hpair with hm hrest
            rcases List.mem_cons.1 hx with h1 | h1
            · right; rw [← hrest, h1]; exact List.mem_cons_self
            · rcases ih hp x h1 with h2 | h2
              · exact Or.inl (h2.trans hm)
              · right; rw [← hrest]; exact List.mem_cons_of_mem _ h2

/-- Expansion never lowers arrival on a nonneg-owlt plan: pop order is
    nondecreasing. [algorithm.md §10.3] -/
theorem expand_arrival_ge {cp : ContactPlan} {src : Node} {cand cand' : Cand}
    (hcp : PlanNonnegOwlt cp) (h : cand' ∈ expand cp src cand) :
    cand.arrival ≤ cand'.arrival := by
  unfold expand at h
  rw [List.mem_map] at h
  obtain ⟨c, hc, hcand'⟩ := h
  rw [List.mem_filter] at hc
  subst hcand'
  exact le_trans (le_max_left _ _) (le_add_of_nonneg_right (hcp c hc.1))

/-- Constructive membership in `expand`: any plan contact departing the
    candidate's node, window-open, and unused joins the frontier with the
    §3.2.4.1.2 arrival. [algorithm.md §3, §10.3] -/
theorem expand_mem_of {cp : ContactPlan} {src : Node} {cand : Cand}
    {c : Contact} (hc : c ∈ cp) (hsrc : c.source = cand.node src)
    (hwin : max cand.arrival c.tStart ≤ c.tEnd) (hnew : c ∉ cand.hops) :
    ({ hops := c :: cand.hops, arrival := max cand.arrival c.tStart + c.owlt }
      : Cand) ∈ expand cp src cand := by
  unfold expand
  rw [List.mem_map]
  refine ⟨c, ?_, rfl⟩
  rw [List.mem_filter]
  refine ⟨hc, ?_⟩
  rw [Bool.and_eq_true, Bool.and_eq_true]
  refine ⟨⟨beq_iff_eq.mpr hsrc, decide_eq_true hwin⟩, ?_⟩
  cases hb : cand.hops.contains c with
  | false => rfl
  | true => exact absurd ((List.contains_iff_mem).1 hb) hnew

/-- A chain's prefix chains. [algorithm.md §2] -/
theorem chainOk_of_append : ∀ {l₁ l₂ : List Contact},
    chainOk (l₁ ++ l₂) = true → chainOk l₁ = true := by
  intro l₁
  induction l₁ with
  | nil => intro l₂ _; rfl
  | cons d rest ih =>
      intro l₂ h
      cases rest with
      | nil => rfl
      | cons e tl =>
          simp only [List.cons_append] at h
          rw [chainOk] at h ⊢
          rw [Bool.and_eq_true] at h ⊢
          exact ⟨h.1, ih (by rw [List.cons_append]; exact h.2)⟩

/-- Adjacent hops in a chain link: destination meets source across the seam.
    [algorithm.md §2] -/
theorem chainOk_junction {A : List Contact} {z q : Contact} {B : List Contact}
    (h : chainOk ((A ++ [z]) ++ q :: B) = true) : z.dest = q.source := by
  rw [chainOk_middle, Bool.and_eq_true] at h
  have h1 := h.1
  rw [chainOk_append, Bool.and_eq_true] at h1
  have h2 := h1.2
  rw [List.getLast?_concat] at h2
  exact beq_iff_eq.mp h2

/-- Threading facts at an interior hop: the prefix arrival, the window test,
    and the suffix start. [algorithm.md §3] -/
theorem arrivalTime_through {t₀ aQ : Time} {Q₁ Q₂ : List Contact} {q : Contact}
    (h : arrivalTime t₀ (Q₁ ++ q :: Q₂) = some aQ) :
    ∃ e, arrivalTime t₀ Q₁ = some e ∧ max e q.tStart ≤ q.tEnd
      ∧ arrivalTime (max e q.tStart + q.owlt) Q₂ = some aQ := by
  rw [arrivalTime_append_bind] at h
  cases he : arrivalTime t₀ Q₁ with
  | none => rw [he] at h; simp at h
  | some e =>
      rw [he] at h
      simp only [Option.bind_some] at h
      simp only [arrivalTime] at h
      split at h
      · rename_i hw
        exact ⟨e, rfl, hw, h⟩
      · exact absurd h (by simp)

/-- Any list with a member outside `closed` splits at its first such member,
    with an all-closed prefix. [algorithm.md §10.3] -/
theorem exists_first_open {closed Q : List Contact}
    (h : ∃ y ∈ Q, y ∉ closed) :
    ∃ Q₁ q Q₂, Q = Q₁ ++ q :: Q₂ ∧ (∀ y ∈ Q₁, y ∈ closed) ∧ q ∉ closed := by
  induction Q with
  | nil =>
      obtain ⟨y, hy, _⟩ := h
      exact absurd hy List.not_mem_nil
  | cons c rest ih =>
      by_cases hc : c ∈ closed
      · have h' : ∃ y ∈ rest, y ∉ closed := by
          obtain ⟨y, hy, hyo⟩ := h
          rcases List.mem_cons.1 hy with h1 | h1
          · exact absurd (show y ∈ closed by rw [h1]; exact hc) hyo
          · exact ⟨y, h1, hyo⟩
        obtain ⟨Q₁, q, Q₂, hdec, hcl, hq⟩ := ih h'
        refine ⟨c :: Q₁, q, Q₂, by rw [hdec, List.cons_append], ?_, hq⟩
        intro y hy
        rcases List.mem_cons.1 hy with h1 | h1
        · rw [h1]; exact hc
        · exact hcl y h1
      · exact ⟨[], c, rest, by rw [List.nil_append],
          fun y hy => absurd hy List.not_mem_nil, hc⟩

/-- A feasible partial route shape: departs `src`, chains, draws from the
    plan. Arrival and duplicate facts travel separately. [algorithm.md §10.3] -/
def PartialOk (cp : ContactPlan) (src : Node) (P : List Contact) : Prop :=
  P.head?.map (·.source) = some src ∧ chainOk P = true ∧ ∀ y ∈ P, y ∈ cp

/-- `PartialOk` restricts to nonempty prefixes. [algorithm.md §10.3] -/
theorem PartialOk.of_append {cp : ContactPlan} {src : Node}
    {P R : List Contact} (h : PartialOk cp src (P ++ R)) (hne : P ≠ []) :
    PartialOk cp src P := by
  obtain ⟨hhead, hchain, hmem⟩ := h
  refine ⟨?_, chainOk_of_append hchain,
    fun y hy => hmem y (List.mem_append_left _ hy)⟩
  cases P with
  | nil => exact absurd rfl hne
  | cons a t =>
      simp only [List.cons_append, List.head?_cons] at hhead
      simp only [List.head?_cons]
      exact hhead

/-- Prop-level decode of `isValidRoute`'s Boolean conjuncts.
    [algorithm.md §2–§3] -/
theorem validRoute_decode {cp : ContactPlan} {src dst : Node} {t₀ : Time}
    {hops : List Contact} (hv : isValidRoute cp src dst t₀ hops = true) :
    hops.head?.map (·.source) = some src
      ∧ hops.getLast?.map (·.dest) = some dst
      ∧ chainOk hops = true
      ∧ ∃ a, arrivalTime t₀ hops = some a := by
  simp only [isValidRoute, Bool.and_eq_true] at hv
  obtain ⟨⟨⟨⟨⟨_, e2⟩, e3⟩, e4⟩, _⟩, e6⟩ := hv
  refine ⟨beq_iff_eq.mp e2, beq_iff_eq.mp e3, e4, ?_⟩
  cases ha : arrivalTime t₀ hops with
  | none => rw [ha] at e6; simp at e6
  | some a => exact ⟨a, rfl⟩

/-- Settled-contact facts carried per closed contact `z`: the closing
    arrival `aP` bounds every frontier arrival (pop order never decreases),
    bounds every duplicate-free feasible partial route ending in `z`
    (settled optimality), and every window-feasible extension of `z` by an
    open contact is frontier-resident. [algorithm.md §10.3] -/
def Settled (cp : ContactPlan) (src : Node) (t₀ : Time)
    (frontier : List Cand) (closed : List Contact) (z : Contact) : Prop :=
  ∃ aP,
    (∀ cand ∈ frontier, aP ≤ cand.arrival)
    ∧ (∀ Q aQ, PartialOk cp src Q → Q.Nodup → Q.getLast? = some z →
        arrivalTime t₀ Q = some aQ → aP ≤ aQ)
    ∧ (∀ q ∈ cp, q ∉ closed → q.source = z.dest →
        max aP q.tStart ≤ q.tEnd →
        ∃ cand ∈ frontier, cand.hops.head? = some q
          ∧ cand.arrival ≤ max aP q.tStart + q.owlt)

/-- The optimality invariant of the best-first loop: frontier candidates are
    well-formed with closed non-head history, every closed contact carries
    its `Settled` block, no closed contact lands on `dst` (a return preempts
    every close), and first hops out of `src` are covered by the root or by
    resident extensions. [algorithm.md §10.3] -/
structure LoopInv (cp : ContactPlan) (src dst : Node) (t₀ : Time)
    (frontier : List Cand) (closed : List Contact) : Prop where
  cands : ∀ cand ∈ frontier, CandInv cp src t₀ cand ∧ cand.hops.Nodup
            ∧ ∀ y ∈ cand.hops.tail, y ∈ closed
  settled : ∀ z ∈ closed, Settled cp src t₀ frontier closed z
  notDst : ∀ z ∈ closed, z.dest ≠ dst
  srcCover : (∃ cand ∈ frontier, cand.hops = [] ∧ cand.arrival ≤ t₀)
    ∨ (∀ q ∈ cp, q ∉ closed → q.source = src → max t₀ q.tStart ≤ q.tEnd →
        ∃ cand ∈ frontier, cand.hops.head? = some q
          ∧ cand.arrival ≤ max t₀ q.tStart + q.owlt)

/-- The popped minimum bounds every duplicate-free feasible partial route
    that still contains an open contact: the bound reads off the route's
    first open boundary, with no splice and no induction. The all-closed
    prefix ends at a settled contact whose residency block hands back a
    frontier candidate across the boundary. [algorithm.md §10.3] -/
theorem frontier_bound {cp : ContactPlan} {src dst : Node} {t₀ : Time}
    {frontier : List Cand} {closed : List Contact} {best : Cand}
    {rest : List Cand}
    (hcp : PlanNonnegOwlt cp)
    (hinv : LoopInv cp src dst t₀ frontier closed)
    (hpick : pickMin frontier = some (best, rest)) :
    ∀ Q aQ, PartialOk cp src Q → Q.Nodup → arrivalTime t₀ Q = some aQ →
      (∃ y ∈ Q, y ∉ closed) → best.arrival ≤ aQ := by
  intro Q aQ hQ hnd ha hopen
  obtain ⟨Q₁, q, Q₂, hdec, hcl, hq⟩ := exists_first_open hopen
  subst hdec
  obtain ⟨e, he, hw, hrest⟩ := arrivalTime_through ha
  have hq_cp : q ∈ cp := hQ.2.2 q (List.mem_append_right _ List.mem_cons_self)
  -- beyond the boundary, time only moves forward
  have hstep : max e q.tStart + q.owlt ≤ aQ := by
    refine departure_le_arrivalTime ?_ hrest
    intro d hd
    exact hcp d (hQ.2.2 d (List.mem_append_right _ (List.mem_cons_of_mem _ hd)))
  rcases List.eq_nil_or_concat Q₁ with hQ₁ | ⟨A, z, hQ₁⟩
  · -- boundary at the first hop: the source cover supplies the witness
    subst hQ₁
    have hsrc : q.source = src := by
      have h := hQ.1
      rw [List.nil_append, List.head?_cons] at h
      exact Option.some.inj h
    have he' : t₀ = e := by
      simpa [arrivalTime] using he
    subst he'
    rcases hinv.srcCover with ⟨root, hroot, _, hrootarr⟩ | hcov
    · have h1 := le4_arrival_le (pickMin_min hpick root hroot)
      have h2 : t₀ ≤ max t₀ q.tStart + q.owlt :=
        le_trans (le_max_left _ _) (le_add_of_nonneg_right (hcp q hq_cp))
      exact le_trans h1 (le_trans hrootarr (le_trans h2 hstep))
    · obtain ⟨cand, hcand, _, hbound⟩ := hcov q hq_cp hq hsrc hw
      have h1 := le4_arrival_le (pickMin_min hpick cand hcand)
      exact le_trans h1 (le_trans hbound hstep)
  · -- nonempty all-closed prefix ending at settled z
    rw [List.concat_eq_append] at hQ₁
    subst hQ₁
    have hz : z ∈ closed := hcl z (List.mem_append_right _ List.mem_cons_self)
    obtain ⟨aP, _, hMR, hres⟩ := hinv.settled z hz
    have hQ₁ok : PartialOk cp src (A ++ [z]) :=
      PartialOk.of_append hQ (by simp)
    have hndQ₁ : (A ++ [z]).Nodup := List.Nodup.of_append_left hnd
    have haP : aP ≤ e := hMR (A ++ [z]) e hQ₁ok hndQ₁ List.getLast?_concat he
    have hjun : z.dest = q.source := chainOk_junction hQ.2.1
    have hwz : max aP q.tStart ≤ q.tEnd := le_trans (max_le_max haP le_rfl) hw
    obtain ⟨cand, hcand, _, hbound⟩ := hres q hq_cp hq hjun.symm hwz
    have h1 := le4_arrival_le (pickMin_min hpick cand hcand)
    have h2 : max aP q.tStart + q.owlt ≤ max e q.tStart + q.owlt :=
      add_le_add (max_le_max haP le_rfl) le_rfl
    exact le_trans h1 (le_trans hbound (le_trans h2 hstep))

/-- Expansions of a well-formed candidate with fully closed hops are
    well-formed with closed non-head history. [algorithm.md §3, §10.3] -/
theorem expand_cands {cp : ContactPlan} {src : Node} {t₀ : Time}
    {closed' : List Contact} {best : Cand}
    (hbi : CandInv cp src t₀ best) (hbn : best.hops.Nodup)
    (hbc : ∀ y ∈ best.hops, y ∈ closed') :
    ∀ cand' ∈ expand cp src best, CandInv cp src t₀ cand' ∧ cand'.hops.Nodup
      ∧ ∀ y ∈ cand'.hops.tail, y ∈ closed' := by
  intro cand' h
  have hci := expand_inv cp src t₀ best hbi cand' h
  unfold expand at h
  rw [List.mem_map] at h
  obtain ⟨c, hc, hcand'⟩ := h
  rw [List.mem_filter] at hc
  obtain ⟨_, hcond⟩ := hc
  rw [Bool.and_eq_true, Bool.and_eq_true] at hcond
  obtain ⟨_, hnotin⟩ := hcond
  have hcontf : best.hops.contains c = false := by
    cases hb : best.hops.contains c with
    | false => rfl
    | true => rw [hb] at hnotin; exact absurd hnotin (by simp)
  have hcnotmem : c ∉ best.hops := by
    intro hmem
    rw [(List.contains_iff_mem).2 hmem] at hcontf
    exact absurd hcontf (by simp)
  subst hcand'
  exact ⟨hci, List.nodup_cons.mpr ⟨hcnotmem, hbn⟩, fun y hy => hbc y hy⟩

/-- Dropping a popped candidate whose head contact is already closed
    preserves the invariant: no surviving obligation pointed at it.
    [algorithm.md §8, §10.3] -/
theorem LoopInv.drop {cp : ContactPlan} {src dst : Node} {t₀ : Time}
    {frontier : List Cand} {closed : List Contact} {best : Cand}
    {rest : List Cand} {c : Contact}
    (hinv : LoopInv cp src dst t₀ frontier closed)
    (hpick : pickMin frontier = some (best, rest))
    (hhead : best.hops.head? = some c) (hc : c ∈ closed) :
    LoopInv cp src dst t₀ rest closed := by
  obtain ⟨_, hrestmem⟩ := pickMin_mem hpick
  refine ⟨fun cand hcand => hinv.cands cand (hrestmem cand hcand),
    ?_, hinv.notDst, ?_⟩
  · intro z hz
    obtain ⟨aP, hMF, hMR, hres⟩ := hinv.settled z hz
    refine ⟨aP, fun cand hcand => hMF cand (hrestmem cand hcand), hMR, ?_⟩
    intro q hqcp hqop hqsrc hqwin
    obtain ⟨cand, hcand, hqhead, hbound⟩ := hres q hqcp hqop hqsrc hqwin
    rcases pickMin_cover hpick cand hcand with h | h
    · exfalso
      rw [h, hhead] at hqhead
      exact hqop (Option.some.inj hqhead ▸ hc)
    · exact ⟨cand, h, hqhead, hbound⟩
  · rcases hinv.srcCover with ⟨root, hroot, hre, hra⟩ | hcov
    · left
      rcases pickMin_cover hpick root hroot with h | h
      · exfalso
        rw [h] at hre
        rw [hre] at hhead
        simp at hhead
      · exact ⟨root, h, hre, hra⟩
    · right
      intro q hqcp hqop hqsrc hqwin
      obtain ⟨cand, hcand, hqhead, hbound⟩ := hcov q hqcp hqop hqsrc hqwin
      rcases pickMin_cover hpick cand hcand with h | h
      · exfalso
        rw [h, hhead] at hqhead
        exact hqop (Option.some.inj hqhead ▸ hc)
      · exact ⟨cand, h, hqhead, hbound⟩

/-- Popping and expanding the root preserves the invariant: the source
    cover transfers from the root to its expansions. [algorithm.md §3, §10.3] -/
theorem LoopInv.root_step {cp : ContactPlan} {src dst : Node} {t₀ : Time}
    {frontier : List Cand} {closed : List Contact} {best : Cand}
    {rest : List Cand}
    (hcp : PlanNonnegOwlt cp)
    (hinv : LoopInv cp src dst t₀ frontier closed)
    (hpick : pickMin frontier = some (best, rest))
    (hroot : best.hops = []) :
    LoopInv cp src dst t₀ (expand cp src best ++ rest) closed := by
  obtain ⟨hbestmem, hrestmem⟩ := pickMin_mem hpick
  obtain ⟨hbi, hbn, _⟩ := hinv.cands best hbestmem
  have hexp := expand_cands (closed' := closed) hbi hbn
    (by rw [hroot]; intro y hy; exact absurd hy List.not_mem_nil)
  refine ⟨?_, ?_, hinv.notDst, ?_⟩
  · intro cand hcand
    rcases List.mem_append.1 hcand with h | h
    · exact hexp cand h
    · exact hinv.cands cand (hrestmem cand h)
  · intro z hz
    obtain ⟨aP, hMF, hMR, hres⟩ := hinv.settled z hz
    refine ⟨aP, ?_, hMR, ?_⟩
    · intro cand hcand
      rcases List.mem_append.1 hcand with h | h
      · exact le_trans (hMF best hbestmem) (expand_arrival_ge hcp h)
      · exact hMF cand (hrestmem cand h)
    · intro q hqcp hqop hqsrc hqwin
      obtain ⟨cand, hcand, hqhead, hbound⟩ := hres q hqcp hqop hqsrc hqwin
      rcases pickMin_cover hpick cand hcand with h | h
      · exfalso
        rw [h, hroot] at hqhead
        simp at hqhead
      · exact ⟨cand, List.mem_append_right _ h, hqhead, hbound⟩
  · rcases hinv.srcCover with ⟨root, hrootm, hre, hra⟩ | hcov
    · rcases pickMin_cover hpick root hrootm with h | h
      · -- the popped candidate is the root: its expansion covers directly
        right
        intro q hqcp _ hqsrc hqwin
        rw [h] at hre hra
        have hnode : best.node src = src := by simp [Cand.node, hroot]
        have hwin' : max best.arrival q.tStart ≤ q.tEnd :=
          le_trans (max_le_max hra le_rfl) hqwin
        refine ⟨⟨q :: best.hops, max best.arrival q.tStart + q.owlt⟩,
          List.mem_append_left _
            (expand_mem_of hqcp (by rw [hnode]; exact hqsrc) hwin' ?_),
          rfl, ?_⟩
        · rw [hroot]; exact List.not_mem_nil
        · exact add_le_add (max_le_max hra le_rfl) le_rfl
      · left
        exact ⟨root, List.mem_append_right _ h, hre, hra⟩
    · right
      intro q hqcp hqop hqsrc hqwin
      obtain ⟨cand, hcand, hqhead, hbound⟩ := hcov q hqcp hqop hqsrc hqwin
      rcases pickMin_cover hpick cand hcand with h | h
      · exfalso
        rw [h, hroot] at hqhead
        simp at hqhead
      · exact ⟨cand, List.mem_append_right _ h, hqhead, hbound⟩

/-- Closing a fresh contact and expanding the closer preserves the
    invariant. The new settled block reads optimality off `frontier_bound`
    on the pre-state — the contact being closed is still open there — and
    residency off the closer's expansion, where the no-reuse filter cannot
    block an open contact against an all-closed history. [algorithm.md §8,
    §10.3] -/
theorem LoopInv.close_step {cp : ContactPlan} {src dst : Node} {t₀ : Time}
    {frontier : List Cand} {closed : List Contact} {best : Cand}
    {rest : List Cand} {c : Contact} {tl : List Contact}
    (hcp : PlanNonnegOwlt cp)
    (hinv : LoopInv cp src dst t₀ frontier closed)
    (hpick : pickMin frontier = some (best, rest))
    (hshape : best.hops = c :: tl)
    (hfresh : c ∉ closed) (hcdest : c.dest ≠ dst) :
    LoopInv cp src dst t₀ (expand cp src best ++ rest) (c :: closed) := by
  obtain ⟨hbestmem, hrestmem⟩ := pickMin_mem hpick
  have hbestmin : ∀ x ∈ frontier, best.arrival ≤ x.arrival :=
    fun x hx => le4_arrival_le (pickMin_min hpick x hx)
  obtain ⟨hbi, hbn, hbc⟩ := hinv.cands best hbestmem
  have hallcl : ∀ y ∈ best.hops, y ∈ c :: closed := by
    intro y hy
    rw [hshape] at hy
    rcases List.mem_cons.1 hy with h1 | h1
    · rw [h1]; exact List.mem_cons_self
    · refine List.mem_cons_of_mem _ (hbc y ?_)
      rw [hshape]
      exact h1
  have hexp := expand_cands (closed' := c :: closed) hbi hbn hallcl
  have hnode : best.node src = c.dest := by simp [Cand.node, hshape]
  refine ⟨?_, ?_, ?_, ?_⟩
  · -- cands: expansions are closed'-historied; rest is monotone
    intro cand hcand
    rcases List.mem_append.1 hcand with h | h
    · exact hexp cand h
    · obtain ⟨hci, hcn, hcc⟩ := hinv.cands cand (hrestmem cand h)
      exact ⟨hci, hcn, fun y hy => List.mem_cons_of_mem _ (hcc y hy)⟩
  · -- settled
    intro z hz
    rcases List.mem_cons.1 hz with hzc | hzold
    · -- the newly closed contact
      subst hzc
      refine ⟨best.arrival, ?_, ?_, ?_⟩
      · intro cand hcand
        rcases List.mem_append.1 hcand with h | h
        · exact expand_arrival_ge hcp h
        · exact hbestmin cand (hrestmem cand h)
      · intro Q aQ hQok hQnd hQl hQa
        exact frontier_bound hcp hinv hpick Q aQ hQok hQnd hQa
          ⟨z, List.mem_of_getLast? hQl, hfresh⟩
      · intro q hqcp hqop hqsrc hqwin
        have hqnew : q ∉ best.hops := by
          intro hmem
          rw [hshape] at hmem
          rcases List.mem_cons.1 hmem with h1 | h1
          · exact hqop (by rw [h1]; exact List.mem_cons_self)
          · exact hqop (List.mem_cons_of_mem _
              (hbc q (by rw [hshape]; exact h1)))
        refine ⟨⟨q :: best.hops, max best.arrival q.tStart + q.owlt⟩,
          List.mem_append_left _
            (expand_mem_of hqcp (by rw [hnode]; exact hqsrc) hqwin hqnew),
          rfl, le_rfl⟩
    · -- previously closed contacts
      obtain ⟨aP, hMF, hMR, hres⟩ := hinv.settled z hzold
      refine ⟨aP, ?_, hMR, ?_⟩
      · intro cand hcand
        rcases List.mem_append.1 hcand with h | h
        · exact le_trans (hMF best hbestmem) (expand_arrival_ge hcp h)
        · exact hMF cand (hrestmem cand h)
      · intro q hqcp hqop hqsrc hqwin
        have hqop' : q ∉ closed := fun hm => hqop (List.mem_cons_of_mem _ hm)
        obtain ⟨cand, hcand, hqhead, hbound⟩ := hres q hqcp hqop' hqsrc hqwin
        rcases pickMin_cover hpick cand hcand with h | h
        · exfalso
          rw [h, hshape] at hqhead
          have h2 := Option.some.inj hqhead
          exact hqop (by rw [← h2]; exact List.mem_cons_self)
        · exact ⟨cand, List.mem_append_right _ h, hqhead, hbound⟩
  · -- notDst: the new contact cannot land on dst (a return preempts)
    intro z hz
    rcases List.mem_cons.1 hz with h1 | h1
    · rw [h1]; exact hcdest
    · exact hinv.notDst z h1
  · -- srcCover
    rcases hinv.srcCover with ⟨root, hrootm, hre, hra⟩ | hcov
    · left
      rcases pickMin_cover hpick root hrootm with h | h
      · exfalso
        rw [h] at hre
        rw [hre] at hshape
        simp at hshape
      · exact ⟨root, List.mem_append_right _ h, hre, hra⟩
    · right
      intro q hqcp hqop hqsrc hqwin
      have hqop' : q ∉ closed := fun hm => hqop (List.mem_cons_of_mem _ hm)
      obtain ⟨cand, hcand, hqhead, hbound⟩ := hcov q hqcp hqop' hqsrc hqwin
      rcases pickMin_cover hpick cand hcand with h | h
      · exfalso
        rw [h, hshape] at hqhead
        have h2 := Option.some.inj hqhead
        exact hqop (by rw [← h2]; exact List.mem_cons_self)
      · exact ⟨cand, List.mem_append_right _ h, hqhead, hbound⟩

/-- T2b for the loop: under the invariant, anything `searchLoop` returns
    arrives no later than any duplicate-free valid route. The return branch
    is `frontier_bound` — the competitor's last contact lands on `dst`,
    which `notDst` keeps open. [algorithm.md §10.3] -/
theorem searchLoop_optimal (cp : ContactPlan) (src dst : Node) (t₀ : Time)
    (hcp : PlanNonnegOwlt cp) :
    ∀ (fuel : Nat) (frontier : List Cand) (closed : List Contact)
      (hops : List Contact),
      LoopInv cp src dst t₀ frontier closed →
      searchLoop cp src dst fuel frontier closed = some hops →
      ∀ Q aQ, isValidRoute cp src dst t₀ Q = true → Q.Nodup →
        arrivalTime t₀ Q = some aQ →
        ∃ a, arrivalTime t₀ hops = some a ∧ a ≤ aQ := by
  intro fuel
  induction fuel with
  | zero =>
      intro frontier closed hops _ hloop
      simp [searchLoop] at hloop
  | succ n ih =>
      intro frontier closed hops hinv hloop
      rw [searchLoop] at hloop
      cases hp : pickMin frontier with
      | none => rw [hp] at hloop; simp at hloop
      | some pr =>
          obtain ⟨best, rest⟩ := pr
          rw [hp] at hloop
          simp only at hloop
          by_cases hret : (best.node src == dst && !best.hops.isEmpty) = true
          · -- return branch: the popped minimum bounds every competitor
            rw [if_pos hret] at hloop
            simp only [Option.some.injEq] at hloop
            subst hloop
            intro Q aQ hQv hQnd hQa
            obtain ⟨hbi, _, _⟩ := hinv.cands best (pickMin_mem hp).1
            obtain ⟨_, _, _, hcache⟩ := hbi
            refine ⟨best.arrival, hcache, ?_⟩
            obtain ⟨hh, hl, hch, _⟩ := validRoute_decode hQv
            cases hgl : Q.getLast? with
            | none => rw [hgl] at hl; simp at hl
            | some last =>
                have hldst : last.dest = dst := by
                  rw [hgl] at hl
                  exact Option.some.inj hl
                have hopen : ∃ y ∈ Q, y ∉ closed :=
                  ⟨last, List.mem_of_getLast? hgl,
                    fun hmem => hinv.notDst last hmem hldst⟩
                exact frontier_bound hcp hinv hp Q aQ
                  ⟨hh, hch, validRoute_hops_mem hQv⟩ hQnd hQa hopen
          · rw [if_neg hret] at hloop
            cases hh : best.hops with
            | nil =>
                rw [hh] at hloop
                simp only at hloop
                exact ih _ _ hops (hinv.root_step hcp hp hh) hloop
            | cons c tl =>
                rw [hh] at hloop
                simp only at hloop
                by_cases hcl : closed.contains c = true
                · rw [if_pos hcl] at hloop
                  exact ih _ _ hops
                    (hinv.drop hp (by simp [hh]) ((List.contains_iff_mem).1 hcl))
                    hloop
                · rw [if_neg hcl] at hloop
                  have hfresh : c ∉ closed := fun hmem =>
                    hcl ((List.contains_iff_mem).2 hmem)
                  have hcdest : c.dest ≠ dst := by
                    intro hd
                    apply hret
                    rw [Bool.and_eq_true]
                    refine ⟨?_, ?_⟩
                    · rw [beq_iff_eq]
                      simp [Cand.node, hh, hd]
                    · rw [hh]; rfl
                  exact ih _ _ hops
                    (hinv.close_step hcp hp hh hfresh hcdest) hloop

/-- The initial state satisfies the invariant: one root candidate at `t₀`,
    nothing closed. [algorithm.md §10.3] -/
theorem loopInv_init (cp : ContactPlan) (src dst : Node) (t₀ : Time) :
    LoopInv cp src dst t₀ [{ hops := [], arrival := t₀ }] [] := by
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro cand hcand
    rw [List.mem_singleton] at hcand
    subst hcand
    exact ⟨⟨fun c hc => absurd hc List.not_mem_nil, rfl, trivial, rfl⟩,
      List.nodup_nil, fun y hy => absurd hy List.not_mem_nil⟩
  · intro z hz
    exact absurd hz List.not_mem_nil
  · intro z hz
    exact absurd hz List.not_mem_nil
  · left
    exact ⟨_, List.mem_singleton.mpr rfl, rfl, le_rfl⟩

/-- T2b, public form: on a nonnegative-OWLT plan, any route `routeSearch`
    returns arrives no later than every valid route — including
    contact-reusing routes and routes the closed-list search never
    enumerates (§8.3). [algorithm.md §10.3] -/
theorem routeSearch_optimal {cp : ContactPlan} {src dst : Node} {t₀ : Time}
    {r Q : List Contact}
    (hcp : PlanNonnegOwlt cp)
    (hr : routeSearch cp src dst t₀ = some r)
    (hQ : isValidRoute cp src dst t₀ Q = true) :
    ∃ a aQ, arrivalTime t₀ r = some a ∧ arrivalTime t₀ Q = some aQ
      ∧ a ≤ aQ := by
  unfold routeSearch at hr
  cases hs : searchLoop cp src dst ((cp.length + 1) * (cp.length + 1) + 1)
      [{ hops := [], arrival := t₀ }] [] with
  | none => simp [hs] at hr
  | some hops =>
      by_cases hv : isValidRoute cp src dst t₀ hops = true
      · simp only [hs, hv, reduceIte, Option.some.injEq] at hr
        rw [← hr]
        obtain ⟨_, _, _, aQ, haQ⟩ := validRoute_decode hQ
        obtain ⟨Q', aQ', hnd', _, hv', ha', hle'⟩ :=
          loop_erasure_of_plan_nonneg hcp hQ haQ
        obtain ⟨a, har, hle⟩ := searchLoop_optimal cp src dst t₀ hcp _ _ _ _
          (loopInv_init cp src dst t₀) hs Q' aQ' hv' hnd' ha'
        exact ⟨a, aQ, har, haQ, le_trans hle hle'⟩
      · simp [hs, hv] at hr

end VerifiedSabr
