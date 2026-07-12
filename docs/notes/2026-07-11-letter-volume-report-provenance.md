# Letter-semantics volume reports: regeneration and provenance

The 2026-07-10 reconciliation requantified every volume-channel number under
the SABR letter, and the conformance note
(`2026-07-10-cgr-conformance-note.md`) shipped with those numbers — but the
letter-semantics EVL reports themselves never landed in the tree.
`out_evl_relay/` still held only the operationalized (through v0.1.1) runs
(relay 40/82 at the depth-3 base), and the reconciliation's own run artifacts
are author-held outside the repository. Every letter number in the note
therefore lacked a committed report artifact. This note closes that gap and
sets the rule that created it: a number enters a note or paper only alongside
its report artifact, committed in the same repository.

## Regeneration (2026-07-11)

Full letter matrix rerun with the committed harness at v0.1.2 (`evl.py`
implements the letter as of d2b9f88): corpus_v3 (1000 cislunar-quantized
plans) and dsn_real_v1 (55 plans), relay and endpoint sourcing, contention
2.0 and 8.0. Depth-3 base runs; depth-5 adjudication of every diverged set
via `evl_adjudicate.py`. Artifacts land under `out_evl_relay/` with the
`_letter` suffix. The dsn endpoint 8.0 leg is new (the reconciliation ran
dsn endpoint at 2.0 only), so the note's "both traffic shapes and both
contentions" sentence for dsn_real_v1 is now fully measured rather than
partially inherited.

## Results

| run | residue plans | diverged (d3) | persist (d5) |
|---|---|---|---|
| corpus_v3 relay c2.0 | 896 | 27 | **26** (25 entry + 1 found/none) |
| corpus_v3 relay c8.0 | 878 | 40 | **40** (all entry) |
| corpus_v3 endpoint c2.0 | 45 | 3 | **3** (all entry) |
| corpus_v3 endpoint c8.0 | 67 | 0 | — |
| dsn_real_v1 relay c2.0 | 37/55 | 0 | — |
| dsn_real_v1 relay c8.0 | 37/55 | 0 | — |
| dsn_real_v1 endpoint c2.0 | 0 | 0 | — |
| dsn_real_v1 endpoint c8.0 | 0 | 0 | — |

Composition detail, matching the shipped note exactly: the relay c2.0
dissolve is plan_000365 (found/none cap artifact); plan_000352 is the one
found/none whose route-less side still truncates at depth 5 — counted,
flagged, not claimed cap-proof. The endpoint c2.0 fires are plans 000080,
000083, 000907 (all entry splits, persisting at depth 5).
`pbat_gap_dispatches` = 0 on every adjudicated record. Zero errors on all
eight runs.

## Agreement with the reconciliation instrument

The reconciliation used an independently patched copy of the harness; this
rerun uses the committed `evl.py` itself. Five artifacts reproduce the
reconciliation outputs byte-identically (endpoint c2/c8 reports, endpoint c2
depth-5 adjudication, dsn relay reports — including the c2/c8
byte-identical-pair datum); the relay reports agree exactly in aggregates
and divergence sets with only record order differing (worker completion
order). The conformance note's numbers are confirmed verbatim.

## Index: note number → committed artifact (sha256 prefix)

| number in the note | artifact |
|---|---|
| relay 26/1000 at c2.0 | `relay_c2_letter_report.json` (81b853d46aa8e3e9), `relay_c2_letter_adj5.jsonl` (56ca9c13d66420ae) |
| relay 40/1000 at c8.0 | `relay_c8_letter_report.json` (54b9b6eb3817ab53), `relay_c8_letter_adj5.jsonl` (05495d47e335bceb) |
| endpoint 3/1000 at c2.0, depth-5 stable | `endpoint_c2_letter_report.json` (76d93b7d9c92b3e6), `endpoint_c2_letter_adj5.jsonl` (4e90ab51138ab6fc) |
| endpoint none at c8.0 | `endpoint_c8_letter_report.json` (5197727925a98c44) |
| dsn 37/55 residue, zero fire | `dsn_relay_c2_letter_report.json` / `dsn_relay_c8_letter_report.json` (2c38b29457fae208, byte-identical pair) |
| dsn endpoint quiet | `dsn_endpoint_c2_letter_report.json` (9313ed58875ddef7), `dsn_endpoint_c8_letter_report.json` (d8981e205a5f0e12) |

Base-run jsonls (`*_letter.jsonl`) sit beside each report. The
operationalized-semantics history (36/82 relay) keeps its original artifacts
(`relay_c2.jsonl`, `relay_c8.jsonl`, adjudications) and the dated 2026-06-10
depth-5 note.
