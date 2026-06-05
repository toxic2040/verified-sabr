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
  cases hs : searchLoop cp src dst ((cp.length + 1) * (cp.length + 1) + 1)
      [{ hops := [], arrival := t₀ }] [] with
  | none => simp [hs] at h
  | some hloop =>
      by_cases hv : isValidRoute cp src dst t₀ hloop = true
      · simp only [hs, hv, reduceIte, Option.some.injEq] at h
        subst h
        exact hv
      · simp [hs, hv] at h

/-- Any hop in a valid route is drawn from the route's contact plan. This is
    the Prop-level bridge for `isValidRoute`'s executable `contains` check.
    [algorithm.md §2, §10.3] -/
theorem validRoute_hops_mem {cp : ContactPlan} {src dst : Node} {t₀ : Time}
    {hops : List Contact} (hv : isValidRoute cp src dst t₀ hops = true) :
    ∀ c ∈ hops, c ∈ cp := by
  simp only [isValidRoute, Bool.and_eq_true] at hv
  obtain ⟨⟨⟨⟨⟨_, _⟩, _⟩, _⟩, hmem⟩, _⟩ := hv
  rw [List.all_eq_true] at hmem
  intro c hc
  exact (List.contains_iff_mem).1 (hmem c hc)

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

/-- Arrival monotonicity with feasibility antitonicity, in one statement:
    departing earlier keeps every window of a feasible hop list feasible and
    never worsens the final arrival. The §3.2.4.1.1 test `max t start ≤ end`
    is antitone in `t`, and the §3.1 arrival recursion is monotone in `t`.
    This is the load-bearing lemma for both T2b reductions (loop erasure and
    the history-divergence discharge). [algorithm.md §10.3] -/
theorem arrivalTime_mono : ∀ {hops : List Contact} {t t' a' : Time}, t ≤ t' →
    arrivalTime t' hops = some a' →
    ∃ a, arrivalTime t hops = some a ∧ a ≤ a' := by
  intro hops
  induction hops with
  | nil =>
      intro t t' a' hle h
      simp only [arrivalTime, Option.some.injEq] at h
      exact ⟨t, rfl, h ▸ hle⟩
  | cons c rest ih =>
      intro t t' a' hle h
      simp only [arrivalTime] at h ⊢
      have htx : max t c.tStart ≤ max t' c.tStart :=
        max_le_max hle le_rfl
      split at h
      · rename_i hw'
        have hw : max t c.tStart ≤ c.tEnd := le_trans htx hw'
        rw [if_pos hw]
        exact ih (add_le_add htx le_rfl) h
      · exact absurd h (by simp)

/-- `arrivalTime` over an append: thread the prefix, then the suffix from the
    prefix's arrival. Generalizes the single-contact `arrivalTime_append`.
    [algorithm.md §3, §10.3] -/
theorem arrivalTime_append_bind (t : Time) (l₁ l₂ : List Contact) :
    arrivalTime t (l₁ ++ l₂)
      = (arrivalTime t l₁).bind fun a => arrivalTime a l₂ := by
  induction l₁ generalizing t with
  | nil => simp [arrivalTime]
  | cons c rest ih =>
      simp only [List.cons_append, arrivalTime]
      by_cases hc : max t c.tStart ≤ c.tEnd
      · simp [hc, ih]
      · simp [hc]

/-- Threading nonneg-owlt contacts never moves time backward: the departure
    time is a lower bound on any defined arrival. This is the only place the
    T2b nonneg-owlt hypothesis bites. [algorithm.md §10.3] -/
theorem departure_le_arrivalTime : ∀ {l : List Contact} {t a : Time},
    (∀ c ∈ l, 0 ≤ c.owlt) → arrivalTime t l = some a → t ≤ a := by
  intro l
  induction l with
  | nil =>
      intro t a _ h
      simp only [arrivalTime, Option.some.injEq] at h
      exact le_of_eq h
  | cons c rest ih =>
      intro t a hnn h
      simp only [arrivalTime] at h
      split at h
      · have h1 : t ≤ max t c.tStart + c.owlt :=
          le_trans (le_max_left t c.tStart)
            (le_add_of_nonneg_right (hnn c List.mem_cons_self))
        exact le_trans h1 (ih (fun d hd => hnn d (List.mem_cons_of_mem _ hd)) h)
      · exact absurd h (by simp)

/-- A chain splits around a middle element: the prefix chained through `x`
    and `x` chained into the suffix, independently. [algorithm.md §2, §10.3] -/
theorem chainOk_middle (l₁ l₂ : List Contact) (x : Contact) :
    chainOk (l₁ ++ x :: l₂) = (chainOk (l₁ ++ [x]) && chainOk (x :: l₂)) := by
  induction l₁ with
  | nil => simp [chainOk]
  | cons d rest ih =>
      cases rest with
      | nil => simp [chainOk]
      | cons e tl =>
          simp only [List.cons_append]
          conv_lhs => rw [chainOk]
          conv_rhs => rw [chainOk]
          rw [← List.cons_append, ← List.cons_append, ih, Bool.and_assoc]

/-- Any list with a duplicate splits as `pre ++ x :: (mid ++ x :: post)`.
    [algorithm.md §10.3] -/
private theorem exists_splice_decomp {α : Type*} {l : List α}
    (h : ¬l.Nodup) : ∃ pre x mid post, l = pre ++ x :: (mid ++ x :: post) := by
  induction l with
  | nil => exact absurd List.nodup_nil h
  | cons c rest ih =>
      by_cases hc : c ∈ rest
      · obtain ⟨mid, post, hsplit⟩ := List.append_of_mem hc
        exact ⟨[], c, mid, post, by rw [hsplit, List.nil_append]⟩
      · have hr : ¬rest.Nodup := fun hn => h (List.nodup_cons.mpr ⟨hc, hn⟩)
        obtain ⟨pre, x, mid, post, hrest⟩ := ih hr
        exact ⟨c :: pre, x, mid, post, by rw [hrest, List.cons_append]⟩

/-- One splice: cutting a feasible hop list between two occurrences of a
    repeated contact keeps it feasible and never worsens arrival, provided
    the erased segment moves time forward (nonneg owlt). The splice enters
    `x :: post` at the prefix's arrival, no later than the original's entry
    after `x :: mid`, so `arrivalTime_mono` carries it. [algorithm.md §10.3] -/
theorem arrivalTime_splice {t₀ a : Time} {pre mid post : List Contact}
    {x : Contact} (hnn : ∀ c ∈ x :: mid, 0 ≤ c.owlt)
    (h : arrivalTime t₀ (pre ++ x :: (mid ++ x :: post)) = some a) :
    ∃ a', arrivalTime t₀ (pre ++ x :: post) = some a' ∧ a' ≤ a := by
  rw [← List.cons_append, arrivalTime_append_bind] at h
  cases hp : arrivalTime t₀ pre with
  | none => rw [hp] at h; simp at h
  | some tp =>
      rw [hp] at h
      simp only [Option.bind_some] at h
      rw [arrivalTime_append_bind] at h
      cases hm : arrivalTime tp (x :: mid) with
      | none => rw [hm] at h; simp at h
      | some tm =>
          rw [hm] at h
          simp only [Option.bind_some] at h
          have htp : tp ≤ tm := departure_le_arrivalTime hnn hm
          obtain ⟨a', ha', hle⟩ := arrivalTime_mono htp h
          refine ⟨a', ?_, hle⟩
          rw [arrivalTime_append_bind, hp]
          simp only [Option.bind_some]
          exact ha'

/-- Length-bounded loop erasure, the induction engine behind `loop_erasure`:
    each splice strictly shortens the hop list. [algorithm.md §10.3] -/
private theorem loop_erasure_bounded (cp : ContactPlan) (src dst : Node)
    (t₀ : Time) : ∀ (n : Nat) (hops : List Contact) (a : Time),
    hops.length ≤ n → (∀ c ∈ hops, 0 ≤ c.owlt) →
    isValidRoute cp src dst t₀ hops = true →
    arrivalTime t₀ hops = some a →
    ∃ hops' a', hops'.Nodup ∧ (∀ c ∈ hops', c ∈ hops)
      ∧ isValidRoute cp src dst t₀ hops' = true
      ∧ arrivalTime t₀ hops' = some a' ∧ a' ≤ a := by
  intro n
  induction n with
  | zero =>
      intro hops a hlen _ hv _
      cases hops with
      | nil => simp [isValidRoute] at hv
      | cons c tl => simp only [List.length_cons] at hlen; omega
  | succ n ih =>
      intro hops a hlen hnn hv ha
      by_cases hnd : hops.Nodup
      · exact ⟨hops, a, hnd, fun _ hc => hc, hv, ha, le_rfl⟩
      · obtain ⟨pre, x, mid, post, hdec⟩ := exists_splice_decomp hnd
        subst hdec
        have hsubset : ∀ c ∈ pre ++ x :: post,
            c ∈ pre ++ x :: (mid ++ x :: post) := by
          intro c hc
          simp only [List.mem_append, List.mem_cons] at hc ⊢
          rcases hc with h1 | h1 | h1
          · exact Or.inl h1
          · exact Or.inr (Or.inl h1)
          · exact Or.inr (Or.inr (Or.inr (Or.inr h1)))
        have hnnseg : ∀ c ∈ x :: mid, 0 ≤ c.owlt := by
          intro c hc
          apply hnn
          simp only [List.mem_cons] at hc
          simp only [List.mem_append, List.mem_cons]
          rcases hc with h1 | h1
          · exact Or.inr (Or.inl h1)
          · exact Or.inr (Or.inr (Or.inl h1))
        obtain ⟨a₁, ha₁, hle₁⟩ := arrivalTime_splice hnnseg ha
        have hv' : isValidRoute cp src dst t₀ (pre ++ x :: post) = true := by
          simp only [isValidRoute, Bool.and_eq_true] at hv ⊢
          obtain ⟨⟨⟨⟨⟨_, e2⟩, e3⟩, e4⟩, e5⟩, _⟩ := hv
          refine ⟨⟨⟨⟨⟨?_, ?_⟩, ?_⟩, ?_⟩, ?_⟩, ?_⟩
          · cases pre <;> simp
          · have hhead : (pre ++ x :: post).head?
                = (pre ++ x :: (mid ++ x :: post)).head? := by simp
            rw [hhead]; exact e2
          · have hlast : (pre ++ x :: post).getLast?
                = (pre ++ x :: (mid ++ x :: post)).getLast? := by
              simp [List.getLast?_cons]
            rw [hlast]; exact e3
          · rw [chainOk_middle, Bool.and_eq_true] at e4 ⊢
            refine ⟨e4.1, ?_⟩
            have h2 := e4.2
            rw [← List.cons_append, chainOk_middle, Bool.and_eq_true] at h2
            exact h2.2
          · rw [List.all_eq_true] at e5 ⊢
            exact fun c hc => e5 c (hsubset c hc)
          · rw [ha₁]; exact Option.isSome_some
        have hlen' : (pre ++ x :: post).length ≤ n := by
          simp only [List.length_append, List.length_cons] at hlen ⊢
          omega
        obtain ⟨hops', a', hnd', hsub', hv'', ha'', hle''⟩ :=
          ih (pre ++ x :: post) a₁ hlen' (fun c hc => hnn c (hsubset c hc)) hv' ha₁
        exact ⟨hops', a', hnd', fun c hc => hsubset c (hsub' c hc), hv'', ha'',
          le_trans hle'' hle₁⟩

/-- T2b loop-erasure reduction: a valid route whose hops all carry
    nonnegative owlt admits a duplicate-free valid route, drawn from the
    same hops, arriving no later. Reduces the T2b competitor class from all
    valid routes to distinct-hop routes. [algorithm.md §10.3] -/
theorem loop_erasure {cp : ContactPlan} {src dst : Node} {t₀ : Time}
    {hops : List Contact} {a : Time} (hnn : ∀ c ∈ hops, 0 ≤ c.owlt)
    (hv : isValidRoute cp src dst t₀ hops = true)
    (ha : arrivalTime t₀ hops = some a) :
    ∃ hops' a', hops'.Nodup ∧ (∀ c ∈ hops', c ∈ hops)
      ∧ isValidRoute cp src dst t₀ hops' = true
      ∧ arrivalTime t₀ hops' = some a' ∧ a' ≤ a :=
  loop_erasure_bounded cp src dst t₀ hops.length hops a le_rfl hnn hv ha

/-- Plan-level T2b loop-erasure reduction: if the contact plan has
    nonnegative OWLT, every valid route over it can be loop-erased. This is
    the form used by the global optimality statement. [algorithm.md §10.3] -/
theorem loop_erasure_of_plan_nonneg {cp : ContactPlan} {src dst : Node}
    {t₀ : Time} {hops : List Contact} {a : Time}
    (hcp : PlanNonnegOwlt cp)
    (hv : isValidRoute cp src dst t₀ hops = true)
    (ha : arrivalTime t₀ hops = some a) :
    ∃ hops' a', hops'.Nodup ∧ (∀ c ∈ hops', c ∈ hops)
      ∧ isValidRoute cp src dst t₀ hops' = true
      ∧ arrivalTime t₀ hops' = some a' ∧ a' ≤ a :=
  loop_erasure (fun c hc => hcp c (validRoute_hops_mem hv c hc)) hv ha

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
