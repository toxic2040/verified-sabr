import VerifiedSabr.Ionrc

/-!
`sabrsearch`: command-line driver answering route queries over an ION-style
contact plan with the verified `routeSearch`. Tooling, not a model of the
standard; formats in algorithm.md §9.
-/

open VerifiedSabr

def main (args : List String) : IO UInt32 := do
  match args with
  | [planPath, queriesPath] =>
      let plan ← IO.FS.readFile planPath
      let queries ← IO.FS.readFile queriesPath
      let cp := buildPlan ((plan.splitOn "\n").filterMap parseLine?)
      for out in runQueries cp ((queries.splitOn "\n").filter (· ≠ "")) do
        IO.println out
      pure 0
  | _ => do
      IO.eprintln "usage: sabrsearch <plan.ionrc> <queries.txt>"
      pure 2
