import VerifiedSabr.Search
import Mathlib.Algebra.Order.Ring.Unbundled.Rat

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

/-- Appending one contact threads its window after the prefix's arrival.
    [algorithm.md §3] -/
theorem arrivalTime_append (t : Time) (l : List Contact) (c : Contact) :
    arrivalTime t (l ++ [c])
      = (arrivalTime t l).bind fun a =>
          if max a c.tStart ≤ c.tEnd then some (max a c.tStart + c.owlt)
          else none := by
  induction l generalizing t with
  | nil => simp [arrivalTime]
  | cons d rest ih =>
      simp only [List.cons_append, arrivalTime]
      by_cases hd : max t d.tStart ≤ d.tEnd
      · simp [hd, ih]
      · simp [hd]

/-- Appending one contact: the chain stays valid exactly when the prefix's last
    destination connects to the new contact's source. [algorithm.md §2] -/
theorem chainOk_append (l : List Contact) (c : Contact) :
    chainOk (l ++ [c])
      = (chainOk l && match l.getLast? with
                      | none => true
                      | some p => p.dest == c.source) := by
  induction l with
  | nil => simp [chainOk]
  | cons d rest ih =>
      cases rest with
      | nil => simp [chainOk]
      | cons e tl =>
          simp only [List.cons_append]
          conv_lhs => rw [chainOk]
          conv_rhs => rw [chainOk]
          rw [← List.cons_append, ih, List.getLast?_cons_cons, Bool.and_assoc]

/-- `pickMin` returns a member of the input list and a remainder of members.
    [algorithm.md §3.5] -/
theorem pickMin_mem : ∀ {l : List Cand} {m : Cand} {rest : List Cand},
    pickMin l = some (m, rest) → m ∈ l ∧ ∀ x ∈ rest, x ∈ l := by
  intro l
  induction l with
  | nil => intro m rest h; simp [pickMin] at h
  | cons c tl ih =>
      intro m rest h
      simp only [pickMin] at h
      cases hp : pickMin tl with
      | none =>
          rw [hp] at h
          simp only [Option.some.injEq, Prod.mk.injEq, List.nil_eq] at h
          obtain ⟨hm, hrest⟩ := h
          subst hm; subst hrest
          exact ⟨List.mem_cons_self, by intro x hx; simp at hx⟩
      | some mo =>
          obtain ⟨mm, others⟩ := mo
          rw [hp] at h
          dsimp only at h
          split at h
          · injection h with hpair
            injection hpair with hm hrest
            subst hm; subst hrest
            exact ⟨List.mem_cons_self, by intro x hx; exact List.mem_cons_of_mem _ hx⟩
          · injection h with hpair
            injection hpair with hm hrest
            subst hm; subst hrest
            obtain ⟨hmm, hoth⟩ := ih hp
            refine ⟨List.mem_cons_of_mem _ hmm, ?_⟩
            intro x hx
            rcases List.mem_cons.1 hx with h1 | h1
            · subst h1; exact List.mem_cons_self
            · exact List.mem_cons_of_mem _ (hoth x h1)

/-- `pickMin` answers `none` only on the empty frontier. [algorithm.md §3.5] -/
theorem pickMin_eq_none : ∀ {l : List Cand}, pickMin l = none → l = [] := by
  intro l h
  cases l with
  | nil => rfl
  | cons c tl =>
      simp only [pickMin] at h
      split at h
      · simp at h
      · split at h <;> simp at h

/-- Key-3 comparison is irreflexive. [algorithm.md §10.1] -/
theorem termLater_irrefl (a : Option Time) : termLater a a = false := by
  cases a with
  | none => rfl
  | some x => simp [termLater]

/-- Key-3 comparison is transitive. [algorithm.md §10.1] -/
theorem termLater_trans {a b c : Option Time} :
    termLater a b = true → termLater b c = true → termLater a c = true := by
  intro h₁ h₂
  cases a with
  | none =>
      cases c with
      | none =>
          cases b with
          | none => simp [termLater] at h₁
          | some y => simp [termLater] at h₂
      | some z => rfl
  | some x =>
      cases b with
      | none => simp [termLater] at h₁
      | some y =>
          cases c with
          | none => simp [termLater] at h₂
          | some z =>
              simp only [termLater, decide_eq_true_iff] at h₁ h₂ ⊢
              exact h₂.trans h₁

/-- Key-3 comparison is total up to equality. [algorithm.md §10.1] -/
theorem termLater_total (a b : Option Time) :
    termLater a b = true ∨ termLater b a = true ∨ a = b := by
  cases a with
  | none =>
      cases b with
      | none => exact Or.inr (Or.inr rfl)
      | some y => exact Or.inl rfl
  | some x =>
      cases b with
      | none => exact Or.inr (Or.inl rfl)
      | some y =>
          rcases lt_trichotomy y x with h | h | h
          · exact Or.inl (by simp [termLater, h])
          · exact Or.inr (Or.inr (by simp [h]))
          · exact Or.inr (Or.inl (by simp [termLater, h]))

/-- Key-4 comparison is reflexive. [algorithm.md §10.1] -/
theorem entryLE_refl (a : Option Node) : entryLE a a = true := by
  cases a with
  | none => rfl
  | some s => simp [entryLE]

/-- Key-4 comparison is total. [algorithm.md §10.1] -/
theorem entryLE_total (a b : Option Node) :
    entryLE a b = true ∨ entryLE b a = true := by
  cases a with
  | none => exact Or.inl rfl
  | some s =>
      cases b with
      | none => exact Or.inr rfl
      | some t =>
          rcases le_total s t with h | h
          · exact Or.inl (by simp [entryLE, h])
          · exact Or.inr (by simp [entryLE, h])

/-- Key-4 comparison is transitive. [algorithm.md §10.1] -/
theorem entryLE_trans {a b c : Option Node} :
    entryLE a b = true → entryLE b c = true → entryLE a c = true := by
  intro h₁ h₂
  cases a with
  | none => rfl
  | some s =>
      cases b with
      | none => simp [entryLE] at h₁
      | some t =>
          cases c with
          | none => simp [entryLE] at h₂
          | some u =>
              simp only [entryLE, decide_eq_true_iff] at h₁ h₂ ⊢
              exact h₁.trans h₂

/-- The 4-key comparison is reflexive: a full tie resolves left.
    [algorithm.md §10.1] -/
theorem le4_refl (c : Cand) : c.le4 c = true := by
  simp [Cand.le4, termLater_irrefl, entryLE_refl]

/-- T2a totality: of any two candidates, one is at least as good as the
    other under the §3.2.8.1.4 order. [algorithm.md §10.2] -/
theorem le4_total (c m : Cand) : c.le4 m = true ∨ m.le4 c = true := by
  simp only [Cand.le4, Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_iff,
    beq_iff_eq]
  rcases lt_trichotomy c.arrival m.arrival with h1 | h1 | h1
  · exact Or.inl (Or.inl h1)
  · rcases lt_trichotomy c.hops.length m.hops.length with h2 | h2 | h2
    · exact Or.inl (Or.inr ⟨h1, Or.inl h2⟩)
    · rcases termLater_total c.termTime m.termTime with h3 | h3 | h3
      · exact Or.inl (Or.inr ⟨h1, Or.inr ⟨h2, Or.inl h3⟩⟩)
      · exact Or.inr (Or.inr ⟨h1.symm, Or.inr ⟨h2.symm, Or.inl h3⟩⟩)
      · rcases entryLE_total c.entry m.entry with h4 | h4
        · exact Or.inl (Or.inr ⟨h1, Or.inr ⟨h2, Or.inr ⟨h3, h4⟩⟩⟩)
        · exact Or.inr (Or.inr ⟨h1.symm, Or.inr ⟨h2.symm, Or.inr ⟨h3.symm, h4⟩⟩⟩)
    · exact Or.inr (Or.inr ⟨h1.symm, Or.inl h2⟩)
  · exact Or.inr (Or.inl h1)

/-- T2a transitivity of the 4-key comparison. [algorithm.md §10.2] -/
theorem le4_trans {c d e : Cand} (h₁ : c.le4 d = true) (h₂ : d.le4 e = true) :
    c.le4 e = true := by
  simp only [Cand.le4, Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_iff,
    beq_iff_eq] at h₁ h₂ ⊢
  rcases h₁ with h1 | ⟨e1, h1⟩
  · rcases h₂ with h2 | ⟨e2, _⟩
    · exact Or.inl (h1.trans h2)
    · exact Or.inl (h1.trans_eq e2)
  · rcases h₂ with h2 | ⟨e2, h2⟩
    · exact Or.inl (e1.trans_lt h2)
    · refine Or.inr ⟨e1.trans e2, ?_⟩
      rcases h1 with h1 | ⟨l1, h1⟩
      · rcases h2 with h2 | ⟨l2, _⟩
        · exact Or.inl (h1.trans h2)
        · exact Or.inl (h1.trans_eq l2)
      · rcases h2 with h2 | ⟨l2, h2⟩
        · exact Or.inl (l1.trans_lt h2)
        · refine Or.inr ⟨l1.trans l2, ?_⟩
          rcases h1 with h1 | ⟨t1, h1⟩
          · rcases h2 with h2 | ⟨t2, _⟩
            · exact Or.inl (termLater_trans h1 h2)
            · exact Or.inl (t2 ▸ h1)
          · rcases h2 with h2 | ⟨t2, h2⟩
            · exact Or.inl (t1.symm ▸ h2)
            · exact Or.inr ⟨t1.trans t2, entryLE_trans h1 h2⟩

/-- T2a: the candidate `pickMin` extracts is §3.2.8.1.4-minimal over the
    whole frontier. [algorithm.md §10.2] -/
theorem pickMin_min : ∀ {l : List Cand} {m : Cand} {rest : List Cand},
    pickMin l = some (m, rest) → ∀ x ∈ l, m.le4 x = true := by
  intro l
  induction l with
  | nil => intro m rest h; simp [pickMin] at h
  | cons c tl ih =>
      intro m rest h x hx
      simp only [pickMin] at h
      cases hp : pickMin tl with
      | none =>
          rw [hp] at h
          dsimp only at h
          injection h with hpair
          injection hpair with hm _
          have htl := pickMin_eq_none hp
          subst htl
          rcases List.mem_cons.1 hx with h1 | h1
          · rw [← hm, h1]; exact le4_refl c
          · simp at h1
      | some mo =>
          obtain ⟨mm, others⟩ := mo
          rw [hp] at h
          dsimp only at h
          split at h
          · rename_i hc
            injection h with hpair
            injection hpair with hm _
            rcases List.mem_cons.1 hx with h1 | h1
            · rw [← hm, h1]; exact le4_refl c
            · rw [← hm]; exact le4_trans hc (ih hp x h1)
          · rename_i hc
            injection h with hpair
            injection hpair with hm _
            rcases List.mem_cons.1 hx with h1 | h1
            · rw [← hm, h1]
              rcases le4_total c mm with ht | ht
              · exact absurd ht hc
              · exact ht
            · rw [← hm]; exact ih hp x h1

/-- Invariant carried by every search candidate: its (reversed) hops form a
    plan-drawn chain departing `src`, and its cached arrival time is the real
    one. -/
def CandInv (cp : ContactPlan) (src : Node) (t₀ : Time) (cand : Cand) : Prop :=
  (∀ c ∈ cand.hops, c ∈ cp)
  ∧ chainOk cand.hops.reverse = true
  ∧ (match cand.hops.reverse with
     | [] => True
     | c :: _ => c.source = src)
  ∧ arrivalTime t₀ cand.hops.reverse = some cand.arrival

/-- The candidate's current node is the destination of the last hop in its
    forward (reversed) order, or `src` when no hops have been taken. -/
private theorem node_eq_getLast (cand : Cand) (src : Node) :
    (match cand.hops.reverse.getLast? with
     | none => src
     | some p => p.dest) = cand.node src := by
  unfold Cand.node
  rw [List.getLast?_reverse]
  cases cand.hops with
  | nil => simp
  | cons c rest => simp

/-- Every one-contact extension of an invariant-satisfying candidate again
    satisfies the invariant. [algorithm.md §3] -/
theorem expand_inv (cp : ContactPlan) (src : Node) (t₀ : Time) (cand : Cand)
    (h : CandInv cp src t₀ cand) :
    ∀ cand' ∈ expand cp src cand, CandInv cp src t₀ cand' := by
  intro cand' hmem
  unfold expand at hmem
  rw [List.mem_map] at hmem
  obtain ⟨c, hc, hcand'⟩ := hmem
  rw [List.mem_filter] at hc
  obtain ⟨hcp, hcond⟩ := hc
  obtain ⟨hsrc, harr, hdep, harrcache⟩ := h
  rw [Bool.and_eq_true, Bool.and_eq_true] at hcond
  obtain ⟨⟨hcsrc, hwin⟩, _huse⟩ := hcond
  have hcsrc' : c.source = cand.node src := eq_of_beq hcsrc
  have hwin' : cand.arrival ⊔ c.tStart ≤ c.tEnd := of_decide_eq_true hwin
  subst hcand'
  unfold CandInv
  simp only [List.reverse_cons]
  refine ⟨?_, ?_, ?_, ?_⟩
  · -- new hop is plan-drawn; the rest by the prefix's invariant
    intro x hx
    rcases List.mem_cons.1 hx with h1 | h1
    · subst h1; exact hcp
    · exact hsrc x h1
  · -- chain stays valid: the prefix chains, and its last dest is `c.source`
    rw [chainOk_append, Bool.and_eq_true]
    refine ⟨harr, ?_⟩
    have hn := node_eq_getLast cand src
    cases hg : cand.hops.reverse.getLast? with
    | none => simp
    | some p =>
        rw [hg] at hn
        simp only at hn ⊢
        rw [hcsrc', ← hn]
        simp
  · -- departure node is unchanged: it is the head of a nonempty prefix, or
    -- `c.source = src` when the prefix is empty
    cases hr : cand.hops.reverse with
    | nil =>
        simp only [List.nil_append]
        rw [hcsrc']
        unfold Cand.node
        have he : cand.hops = [] := by
          have := congrArg List.reverse hr
          simpa using this
        rw [he]
    | cons d tail =>
        rw [hr] at hdep
        simp only [List.cons_append]
        exact hdep
  · -- cached arrival is the real one: thread the new window after the prefix
    rw [arrivalTime_append, harrcache]
    simp only [Option.bind_some]
    rw [if_pos hwin']

/-- Soundness invariant of the best-first loop: if every frontier candidate
    satisfies `CandInv` and the loop returns `hops`, then `hops` is a
    plan-drawn, adjacent chain with a defined arrival time. The closed list
    only removes candidates from consideration and never constructs one, so it
    is universally quantified and carries no invariant of its own.
    [algorithm.md §3, §8] -/
theorem searchLoop_sound (cp : ContactPlan) (src dst : Node) (t₀ : Time) :
    ∀ (fuel : Nat) (frontier : List Cand) (closed : List Contact)
      (hops : List Contact),
      (∀ cand ∈ frontier, CandInv cp src t₀ cand) →
      searchLoop cp src dst fuel frontier closed = some hops →
      (∀ c ∈ hops, c ∈ cp)
      ∧ chainOk hops = true
      ∧ (arrivalTime t₀ hops).isSome := by
  intro fuel
  induction fuel with
  | zero =>
      intro frontier closed hops _ hloop
      simp [searchLoop] at hloop
  | succ n ih =>
      intro frontier closed hops hfront hloop
      rw [searchLoop] at hloop
      cases hp : pickMin frontier with
      | none => rw [hp] at hloop; simp at hloop
      | some pr =>
          obtain ⟨best, rest⟩ := pr
          rw [hp] at hloop
          simp only at hloop
          obtain ⟨hbestmem, hrestmem⟩ := pickMin_mem hp
          have hbestinv : CandInv cp src t₀ best := hfront best hbestmem
          have hrestinv : ∀ cand ∈ rest, CandInv cp src t₀ cand :=
            fun cand hcand => hfront cand (hrestmem cand hcand)
          have hexpinv :
              ∀ cand ∈ expand cp src best ++ rest, CandInv cp src t₀ cand := by
            intro cand hcand
            rcases List.mem_append.1 hcand with h1 | h1
            · exact expand_inv cp src t₀ best hbestinv cand h1
            · exact hrestinv cand h1
          by_cases hret : (best.node src == dst && !best.hops.isEmpty) = true
          · -- returning `best`: read off all three conjuncts from `CandInv best`
            rw [if_pos hret] at hloop
            simp only [Option.some.injEq] at hloop
            subst hloop
            obtain ⟨hmem, hchain, _hdep, harrcache⟩ := hbestinv
            refine ⟨?_, hchain, ?_⟩
            · intro c hc
              exact hmem c (List.mem_reverse.1 hc)
            · rw [harrcache]
              exact Option.isSome_some
          · -- recursing: every branch shrinks to a frontier that preserves the
            -- invariant — expansion (root or newly closed head) or the popped
            -- remainder (already-closed head, dropped unexpanded)
            rw [if_neg hret] at hloop
            cases hh : best.hops with
            | nil =>
                rw [hh] at hloop
                simp only at hloop
                exact ih (expand cp src best ++ rest) closed hops hexpinv hloop
            | cons c tl =>
                rw [hh] at hloop
                simp only at hloop
                by_cases hcl : closed.contains c = true
                · rw [if_pos hcl] at hloop
                  exact ih rest closed hops hrestinv hloop
                · rw [if_neg hcl] at hloop
                  exact ih (expand cp src best ++ rest) (c :: closed) hops
                    hexpinv hloop

end VerifiedSabr
