# DSN relay-sourced volume replay: residue opens, nothing fires

Status: runs predate 2026-06-09; this note is the tracked record,
written when a review pass found the artifacts unreported. The paper's
§7 relay paragraph cited only the corpus_v3 relay runs; the dsn_real_v1
relay runs existed in `out_evl_relay/` with no note and no paper
mention, and §7's endpoint sentence ("no ties, nothing to store
divergently, the channel closed upstream by the regime") overclaimed -
the absence of ties on dsn_real_v1 is a property of the endpoint
dispatch set, not of the corpus, as these runs show. Paper corrected in
the same commit as this note.

## Runs

Two-ledger volume replay (`scripts/diffharness/evl.py`), relay traffic
mode (every node sources), over the 55-plan `dsn_real_v1` corpus at
contention 2.0 and 8.0, depth cap 3 - the corpus_v3 relay runs'
protocol on the real corpus. Command shape (reconstructed from the
evl.py CLI and the artifact naming; the original invocations were not
captured in `out_evl_relay/run.log`, which covers the corpus_v3 runs
only - a provenance gap this note closes going forward):

```sh
python3 scripts/diffharness/evl.py run --corpus <dsn_real_v1 root> \
    --glob 'dsn_real_v1_plan_*' --traffic relay --contention 2.0 \
    --out out_evl_relay/dsn_relay_c2.jsonl
python3 scripts/diffharness/evl.py analyze \
    --results out_evl_relay/dsn_relay_c2.jsonl \
    --out out_evl_relay/dsn_relay_c2_report.json
# same at --contention 8.0 -> dsn_relay_c8.jsonl / _report.json
```

## Result

| metric | contention 2.0 | contention 8.0 |
|---|---:|---:|
| plans | 55 | 55 |
| errors | 0 | 0 |
| plans with residue events | 37 | 37 |
| residue events total | 4785 | 4785 |
| plans diverged | 0 | 0 |
| diverged entry / found-none | 0 / 0 | 0 / 0 |
| truncated enumerations | 747830 | 747830 |

Dispatches per plan run 2184 to 38640 (959,928 per contention run) -
the relay protocol scales with the plan's node count, and DSN
day-plans vary widely.

The residue profile is identical across the two contentions, and that
is expected rather than suspicious: residue events are full-tuple-tie
charge splits, ties are a plan-and-dispatch property, and contention
scales only the bundle size charged onto them. The two runs are
distinct artifacts (different file hashes, bundle sizes ~4x apart,
different parallel completion order), not a copy.

## What it establishes

- dsn_real_v1 does hold full-tuple ties: relay sourcing opens residue
  on 37 of 55 plans, 4,785 events. The endpoint replay's "zero residue
  events" was a fact about its dispatch set (the plan query pairs),
  not about the corpus.
- None of it fires: zero divergences at either contention. The volume
  channel's firing is indexed by plan structure as well as traffic
  shape - the quantized mesh fires under relay sourcing (36-82 of
  1000, depth-4-adjudicated), the real deep-space corpus absorbs the
  same protocol.
- The absorption anatomy on dsn_real_v1 is not traced per-event here;
  the paper marks it presumed (tuple-equivalent fallbacks) rather than
  measured.

## Paper deltas in this commit

- §7 endpoint sentence rescoped to its dispatch set.
- §7 relay paragraph gains the dsn_real_v1 runs.
- Abstract, §1 contribution list, §7 verdict, and §9 characterization
  carry the corpus-indexed firing (quantized mesh fires, real-DSN
  absorbs).
- §8 stale sentence ("ION leg awaits margin-frame grading") replaced
  with the current state (live-validated and graded, §3; no ION leg on
  the helio bands).
- Appendix B artifact index gains `out_evl_relay/`.
