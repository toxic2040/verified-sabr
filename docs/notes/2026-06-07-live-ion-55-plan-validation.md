# Live-ION 55-plan differential validation on the real DSN corpus

Status: run completed 2026-06-07, exit 0. Full live-ION pass of the
differential harness (`scripts/diffharness/ion_node.py`) over the
`dsn_real_v1` corpus against ION 4.1.4 (`cgrfetch` dispatches on a
throwaway single node). This is the live validation the paper's §3
registered-profile result flagged as awaited (the mirror-predicted,
frozen profile, "awaiting live validation").

## Run

- Corpus: `dsn_real_v1` (`repos/dsn-scraper/out/dsn_real_v1`), 55 contact
  plans (`dsn_real_v1_plan_20260406` .. `_20260605`).
- Predictions: `out_s5/predictions.jsonl` (verified-sabr search output).
- Command:
  `python3 scripts/diffharness/ion_node.py validate --corpus ~/work/repos/dsn-scraper/out/dsn_real_v1 --predictions out_s5/predictions.jsonl --out out_s5/ion_live.jsonl`
- Output: `out_s5/ion_live.jsonl` (8967 rows = 8912 dispatch rows + 55
  `plan_done` markers). `out_s5/` is a differential-run byproduct and stays
  gitignored; this note is the tracked record of the outcome.

## Result

55/55 plans, 8912 dispatches, zero mismatches.

| metric        | count |
|---------------|------:|
| dispatches    | 8912  |
| route_exact   | 6935  |
| arrival_match | 6935  |
| none_match    | 1977  |
| mismatch      | 0     |

`route_exact == arrival_match` on every plan, and 6935 + 1977 = 8912:
every dispatch is either a route-and-arrival exact match against ION or a
two-sided none (the verified search and ION agree no route exists). No
`route_exact:false` or `arrival_match:false` rows, no errors or tracebacks,
and the run exited cleanly with no leaked ION processes.

## What it establishes

The verified search reproduces ION 4.1.4's route construction and arrival
times across the full real DSN corpus at dispatch scale — measured against
live ION output, not a mirror prediction. This closes the
"awaiting live validation" caveat on the registered-profile differential at
the corpus level. The agreement criterion is the harness route + arrival
comparison (`docs/algorithm.md` §9.3); the selection-key degrees of freedom
characterized in the paper are unaffected, since the unloaded real corpus
exercises the regime where the four selection keys coincide.
