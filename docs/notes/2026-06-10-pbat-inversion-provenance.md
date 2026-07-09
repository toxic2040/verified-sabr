# First-byte vs last-byte inversion rates: provenance restored

Status: the measurement predates this note (2026-06-05); this note is
the tracked record, written when an anomaly-log pass found the paper's
§8 numbers unpinned. The last-byte paragraph (commit f8de26b) cites
44099 routable dispatches and inversion rates of 16-23% at megabyte
bundles and 0-12 dispatches at kilobyte bundles, but the script that
produced them was a sandbox one-off (`<sandbox>/swarm/
measure_pbat.py`, never committed), the numbers appear in no
`docs/notes/` entry, and no output artifact existed in the repository -
Appendix B's claim that the draft's numbers are drawn verbatim from the
working notes was false for this paragraph.

## Recovery

The originating session's transcript (2026-06-05) holds both the
measurement script and its raw outputs. The algorithm: over every plan
in corpus_v3, take the first six sorted source-destination pairs from
`pairs.jsonl` and eight dispatch times at (k+1)/9 of the plan horizon;
enumerate candidate routes to depth 3 (contact-disjoint walks, route
observed as first-byte arrival, final-contact rate, hops, termination,
entry node); pick a winner under the §3.2.8.1.4 cascade with key 1
scored two ways - first-byte arrival, and last-byte arrival = first-byte
plus EVC/rate of the final contact in exact Fraction arithmetic - and
classify each winner change as a first-byte tie the last-byte key merely
re-resolves (equal first-byte arrival, already counted as route
multiplicity) or a genuine inversion (the last-byte winner is
first-byte-suboptimal).

## Generator, committed and re-verified

`scripts/diffharness/pbat_inversion.py` is the recovered algorithm,
unchanged, with the divergence measurement and the tie/inversion
decomposition folded into one pass. Re-run 2026-06-10 against
`cislunar-lab/out/corpus_v3` (report artifact:
`out_s5/pbat_inversion_report.json`); it reproduces the 2026-06-05
outputs exactly, zero plans skipped:

| EVC (bytes) | tie re-resolved | genuine inversion |
|-------------|-----------------|-------------------|
| 100         | 15320 (34.7%)   | 0 (0.0%)          |
| 10^4        | 15317 (34.7%)   | 12 (0.0%)         |
| 10^6        | 9601 (21.8%)    | 7093 (16.1%)      |
| 10^8        | 8443 (19.1%)    | 10203 (23.1%)     |

48000 dispatches, 44099 routable, every routable dispatch with
candidates through more than one entry node (multi_entry = 44099).

## Mapping to the §8 sentence

- "44099 routable dispatches" = the routable count over the 48000-query
  grid (1000 plans x 6 pairs x 8 dispatch times).
- "megabyte-scale bundles invert the key-1 winner on 16 to 23% of
  dispatches" = genuine inversions at EVC 10^6 (16.1%) and 10^8 (23.1%).
- "kilobyte-scale bundles on essentially none (0 to 12)" = genuine
  inversions at EVC 100 (0) and 10^4 (12).
- "the rest of the apparent divergence being first-byte ties already
  counted as route multiplicity" = the tie-re-resolved column.

The query grid is the measurement's own (denser than the 4100-query
recording run whose routable count is 4093); the two denominators are
different objects and the paper text already attributes 44099 to this
measurement, not to the audit's dispatch set.
