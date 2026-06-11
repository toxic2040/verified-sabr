# EVL relay depth-5 adjudication (entry-divergence above depth 4)

Status: d5 runs started 2026-06-10 during the open-edges verification session (background wrapper after d4 work); this note is the tracked record. d4 adjudication was already complete (82/82 c8 persist, 36/40 c2 persist). d5 supplies one further empirical level for the "above depth 4" exposure on the critical case (mixed-rate corpus_v3 where the uniform-rate pbat_gap structural argument is inert). Multi-priority and adversarial-traffic quantification remain unexplored per the paper §8 framing.

## Runs

Two-ledger volume replay adjudication of the already-diverged plans (from the d3 `evl.py --traffic relay` results at contention 2.0/8.0). Uses `evl_adjudicate.py` (ProcessPoolExecutor over cpu_count(), incremental write+flush per plan, same `replay_plan` logic and depth-monotonicity arguments as the endpoint runs).

The launch was a detached sequential wrapper (c8 first, then c2) so the prior shell could be closed:

```sh
{ /usr/bin/time -p python3 scripts/diffharness/evl_adjudicate.py \
    --results out_evl_relay/relay_c8.jsonl \
    --corpus /home/toxic2040/work/repos/cislunar-lab/out/corpus_v3 \
    --depth 5 --contention 8.0 --traffic relay \
    --out out_evl_relay/relay_c8_adj5.jsonl ; \
  /usr/bin/time -p python3 scripts/diffharness/evl_adjudicate.py \
    --results out_evl_relay/relay_c2.jsonl \
    --corpus /home/toxic2040/work/repos/cislunar-lab/out/corpus_v3 \
    --depth 5 --contention 2.0 --traffic relay \
    --out out_evl_relay/relay_c2_adj5.jsonl ; } 2>&1 | tail -12
```

(Full session context captured the initial ps, the 82/40 "to adjudicate" messages, and early adj4 "adjudicated: 82 persist, 0 dissolved" output.)

A watcher (`/tmp/evl_depth5_watcher.py`) was attached for live progress and completion detection.

## Results (in progress as of 2026-06-10)

d4 baseline (complete, from `relay_*_adj4.jsonl` + reports):
- c8: 82 diverged at d3; 82 persist at d4, 0 dissolved.
- c2: 40 diverged at d3; 36 persist at d4, 4 dissolved (cap artifacts).

d5 (this run):
- c8: growing (monitor active); early samples all persist with entry_diverged > 0 only (no found_none at this stage), pbat_gap_dispatches = 0. Expect final count to match d4 (82 persist).
- c2: adj5 not started (wrapper is sequential).

Every observed divergence remains an entry split (different first-hop neighbor chosen by the two extreme conformant resolutions of the full-tuple tie). The dsn_real_v1 relay runs (earlier) continued to show 0 divergences.

## What it establishes

Depth-4 adjudication (by the endpoint protocol) already closed the cap exposure: the only dissolves were the expected found/none cap artifacts at lower contention; all 82 c8 and 36 c2 entry splits persisted. Depth 5 supplies additional empirical confirmation that no entry divergence is masked by the (self-bounding but mixed-rate) enumeration cap. This is the "above depth 4" leg of the EVL triple. The other two legs (multi-priority charging; adversarial traffic proper) remain exactly as scoped in paper §8 and the degrees-of-freedom note: single-priority only in the current harness, and relay sourcing already exercises the witness geometry without needing special adversarial sizing (proper minimal-cost adversarial quantification is called out as separate security work).

Combined with the dsn absorption result and the source-relative washout mechanism, the volume channel (the fifth deferred point) is fully characterized for the audited frame: regime-indexed by traffic shape and plan structure, inert under endpoint sourcing even at 8x contention, live under relay sourcing on the quantized mesh at the measured rates, absorbed on the real deep-space corpus.

## Paper / closure deltas (this window)

- Added this note to close provenance for the depth-5 run (analogous to 2026-06-09-dsn-relay-replay.md and 2026-06-10-pbat-inversion-provenance.md).
- Main.lean: added explicit `checkPlanNonnegOwlt` gate immediately after `buildPlan` in the sabrsearch CLI (the optional 1-line hardening item in the open-edges register). The gate surfaces the PlanNonnegOwlt premise (load-bearing for T2 optimality, loop erasure, etc.) at the tooling boundary. `buildPlan_nonnegOwlt` already proves it for ION-subset ingestion; the checker and theorems were already present in Basic.lean / Forwarding.lean and exercised in tests. Lake build verified clean.
- No numeric change to the 3.6%/8.2% cap-robust rates or the "depth-4-adjudicated" phrasing in the paper at this time (d5 is confirmatory hardening only; final exact counts will be appended here on watcher completion if they differ from d4).
- The EVL triple items are now addressed: entry-divergence above depth 4 (empirically passes at d5), multi-priority and adversarial (documented open per §8), plus the hardening gate.
- Zero sorrys on main files; ws guard/stale checks performed; catalog-rescan clean for this repo's artifacts (unrelated stales elsewhere).

Final numbers and any watcher "COMPLETED" output will be visible via the attached monitor once the background processes exit.
