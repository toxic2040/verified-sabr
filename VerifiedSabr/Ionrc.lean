import VerifiedSabr.Search

/-!
Tooling, not a model of the standard: ingestion of the ION-style contact-plan
subset emitted by the scenario generator (integer `a contact` / `a range` line
pairs, relative times) plus the query/answer protocol for the `sabrsearch`
executable. Formats and pairing rules: algorithm.md §9.1; output protocol:
algorithm.md §9.3 context.
-/

namespace VerifiedSabr

/-- One parsed ionrc line, contact or range. Fields mirror the line shape
    `a {contact|range} +S +E FROM TO V`. [algorithm.md §9.1] -/
structure RawLine where
  isContact : Bool
  s : Nat
  e : Nat
  a : String
  b : String
  v : Nat
  deriving Repr

/-- Relative-time field: `+N` for natural N; anything else is malformed. -/
def parseRel? (w : String) : Option Nat :=
  if w.startsWith "+" then (w.drop 1).toNat? else none

/-- Parse one line of the ionrc subset; `none` for comments, blanks, and
    malformed lines (skipped, never repaired). Inputs are generator- and
    harness-controlled, so token splitting on single spaces suffices.
    [algorithm.md §9.1] -/
def parseLine? (line : String) : Option RawLine := do
  match (line.splitOn " ").filter (· ≠ "") with
  | ["a", kind, s, e, a, b, v] =>
      if kind == "contact" || kind == "range" then do
        let s ← parseRel? s
        let e ← parseRel? e
        let v ← v.toNat?
        pure ⟨kind == "contact", s, e, a, b, v⟩
      else none
  | _ => none

/-- Join contact lines against range lines by exact (FROM, TO, START) match;
    a contact with no matching range gets owlt 0. [algorithm.md §9.1] -/
def buildPlan (lines : List RawLine) : ContactPlan :=
  let contacts := lines.filter (fun l => l.isContact)
  let ranges := lines.filter (fun l => !l.isContact)
  contacts.map fun c =>
    let owlt : Time :=
      match ranges.find? (fun r => r.a == c.a && r.b == c.b && r.s == c.s) with
      | some r => (r.v : Time)
      | none => 0
    { source := c.a, dest := c.b, tStart := (c.s : Time), tEnd := (c.e : Time),
      owlt := owlt, rate := (c.v : ℚ) }

/-- ION-subset ingestion always produces nonnegative OWLT plans: parsed range
    values are naturals, and a missing range defaults to zero. [algorithm.md §9.1,
    §10.3] -/
theorem buildPlan_nonnegOwlt (lines : List RawLine) :
    PlanNonnegOwlt (buildPlan lines) := by
  unfold PlanNonnegOwlt buildPlan
  intro c hc
  rw [List.mem_map] at hc
  obtain ⟨raw, _hraw, hcdef⟩ := hc
  subst hcdef
  simp only
  split
  · rename_i r hr
    exact_mod_cast Nat.zero_le r.v
  · simp

/-- Render one hop as `FROM:TO:TSTART` (tStart is an integer rational on
    generator plans; the numerator is the integer). -/
def renderHop (c : Contact) : String :=
  s!"{c.source}:{c.dest}:{c.tStart.num}"

/-- Answer one query as a machine-parseable line:
    `RESULT src dst t0num/t0den NONE` or
    `RESULT src dst t0num/t0den FOUND arrnum/arrden nhops h;h;...`. -/
def answer (cp : ContactPlan) (src dst : Node) (t₀ : Time) : String :=
  match routeSearch cp src dst t₀ with
  | none => s!"RESULT {src} {dst} {t₀.num}/{t₀.den} NONE"
  | some hops =>
      let arr := ((arrivalTime t₀ hops).map
        (fun a => s!"{a.num}/{a.den}")).getD "?"
      s!"RESULT {src} {dst} {t₀.num}/{t₀.den} FOUND {arr} {hops.length} "
        ++ String.intercalate ";" (hops.map renderHop)

/-- Run query lines `src dst t0num [t0den]`; malformed lines are skipped. -/
def runQueries (cp : ContactPlan) (queryLines : List String) : List String :=
  queryLines.filterMap fun line =>
    match (line.splitOn " ").filter (· ≠ "") with
    | [src, dst, num] =>
        num.toNat?.map fun n => answer cp src dst (n : Time)
    | [src, dst, num, den] =>
        match num.toNat?, den.toNat? with
        | some n, some d =>
            if d == 0 then none
            else some (answer cp src dst ((n : Time) / (d : Time)))
        | _, _ => none
    | _ => none

end VerifiedSabr
