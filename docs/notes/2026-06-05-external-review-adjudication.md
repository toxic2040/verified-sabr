# Adjudication: two external reviews of the erratum and the closure claim

Status: adjudicated 2026-06-05 against the spec text
(docs/sources/734x3b1.txt), the ION source (bpv7/cgr/libcgr.c), the
Lean reference, and the harness artifacts. Two hostile reviews
arrived the same day: one attacking the standalone erratum as a
mislabeled and non-forced contradiction, one attacking the paper's
closure claim as overstrong with multiple candidate fifth degrees of
freedom. Each finding was verified or refuted at the anchor level
before any text changed. Actions taken are listed at the end.

## Review 1: the "contradiction" attack

**"Wrong contradiction label - §3.2.5.1 b)/§3.2.6.9.1 are not
acyclicity clauses" - refuted as aimed.** The standalone erratum
(2026-06-05-sabr-acyclicity-erratum.md) cites §3.2.1, edge rule d),
§3.2.6.10, §1.4, and the §3.2.8.1 NOTE; it never mentions §3.2.5.1 b)
or §3.2.6.9.1. The reviewer conflated the paper's §4.1 (candidate
list) with the erratum (§4.4, acyclicity). The recommended "split the
issues" is the standing structure: the erratum was extracted from
this note set precisely because it depends on nothing else.

**"§2.3.2.2 scopes the route list to computed routes" - confirmed,
and adopted.** Line-level check: the route list is "all routes ...
that (a) have been computed and (b) are not terminated," and
§3.2.6.9 h) deems candidate routes from that list's filtered members.
This is the strongest anchor for the cessation reading and the paper
had not cited it. §4.1 now does, and carries the three readings of
the §3.2.5.1 b) apposition explicitly: unrestricted-normative
(conflicts with the cessation license), descriptive (false of every
cessation-conforming implementation), computed-list-scoped (mandates
nothing, keys 2-4 vacuous by permission). No reading makes the gloss
accurate and the license innocuous at once; nothing arbitrates; the
flip is measured. "Contradiction" as a label for this instance is
retired in favor of that arbitration-proof statement - which is the
stronger claim, since it survives whichever way a standards body
would resolve it.

**"Cessation makes singleton ION conformant" and "keys 2-4 vacuous
under a singleton" - confirmed, and already the artifacts' own
position** (§4.1 "satisfies the second clause literally"; reading 4
of the quantifier exhaustion; §A.4). These two findings restate the
finding under attack. The review's counterexample (equal arrival,
different termination, discovery order decides) is the measured
content of ION's 1054 key-3 deviations.

**"Figure 3-4 omits reverse contacts, so the acyclicity note
overclaims 'any bidirectional link'" - refuted in substance,
adopted as a pre-emption.** Worked against the spec's own figure 3-2
plan: rule c)'s relevance recursion admits the reverse contact
whenever it admits the forward (both qualification conditions are
discharged by the forward contact itself), so the figure contradicts
the rule as written - evidence for the erratum, not against it.
Figures referenced from the §3.2.1 NOTE are informative; the
shall-items a)-d) are the construction. And the 2-cycle survives
every defensible pruning: contact 2 lies on a §1.4-valid route
(1, 2, 7, 9), so even "keep only contacts on valid routes to D"
retains it. The erratum now carries all three replies as an
anticipated-objection section.

Verdict on review 1: the erratum needed a pre-emption paragraph, not
rework. The paper's §4.1 headline wording ("mandated complete") was
the legitimate target and is fixed.

## Review 2: the closure-claim attack

**"Volume is not inert under leg-sourced traffic at relays" -
accepted, run rather than argued, and the reviewer's direction
confirmed.** Verified first: the replay's traffic was endpoint query
pairs only (evl.py replay_plan), the witness is leg-sourced by
construction, and the structural washout mechanism (tuple-equivalent
fallbacks) is source-relative - it does not extend to bundles
originated at interior nodes, which are natural traffic in mesh
deployments, not adversarial. evl.py grew --traffic relay (every node
sources toward the endpoint destinations) and the full corpus was
rerun at both contention levels: 82 of 1000 plans diverge at
contention 8.0 (all 82 persist under depth-4 adjudication), 40 at
2.0 (36 persist, 4 dissolve as cap artifacts), every divergence an
entry split (the two
ledgers enqueue to different neighbors), residue carried by ~84% of
plans either way. The volume channel is permitted with
traffic-shape-indexed firing, not permitted-but-inert; the paper's
§7 verdict and abstract now say so, and the channel is stated as the
fifth deferred point (§3.2.8.1.4 a) 4) "arbitrarily" plus §3.2.8.1.2
charging the arbitrarily-stored object). This was the review's
strongest finding and the program's instruments were one traffic
flag away from it.

**"Plan horizon / Tmax clipping is an unlisted fifth DoF" - refuted
as an implementation freedom.** The 86400 clip is a property of the
plan: every contact in it ends at the generator's horizon, and both
implementations receive identical end times. Operational horizon
choices vary the input, and the claim quantifies over (plan,
dispatch) pairs; §3.2.3.2 deletes only past contacts, and no clause
licenses dropping future ones. What the review correctly exposed is
that the paper never stated the quantification; §1 now does, and
§6.2 marks the clip as plan-side where the residue witnesses use it.

**"Excluded-nodes list + custody refusal is a second state channel" -
refuted as amplification, confirmed obliquely via the probe option.**
The §7 induction covers excluded lists exactly as it covers queues:
§3.2.5.2 populates them from action history (prior hop, refusal
events), never from the stored route object, so they propagate
divergence but cannot originate it once selections agree; the review's
chain presupposes the divergence it claims to add. §7 now states the
excluded-list case alongside queues. What the review's neighborhood
does contain, found during verification: §2.4.4 makes probe
forwarding optional ("may ... occasionally"), and §3.2.5.2 b) keys
the exclusion filter on the would-serve-as-probe predicate - so under
custody-bearing traffic, identical refusal histories admit different
excluded lists and different forwards in two conformant
implementations. A genuine deferred point in the selection path, of
the same species as the four, unexercisable on custody-free corpora.
Now flagged in §8.

**"Procedural enumeration freedom (visited list, Yen vs best-first,
contact order) is a fifth DoF the differential never varied" -
accepted in substance; absorbed as the interior of the candidate-list
freedom.** The program's own numbers prove the point: under the
completeness reading the deployed visited pruning costs 210 key-3 + 1
key-4 dispatches of 4093, so two implementations that both "fix the
four" but differ on visited practice differ behaviorally; under the
cessation reading §3.2.6.10 pins generation order by arrival cost
only, so equal-arrival singleton identity - entry node included - is
unpinned tie behavior. "Fix the four" is honest only as "pin the list
contents"; §4.1 now says so. Contact-ingestion order is the same
freedom expressed through frontier and closing order, already
measured (the 49-case frontier-order emergence; the closing-caused
survivors).

**"Numeric collation and precision" - accepted as a flagged boundary,
refuted as a measured fifth.** Both implementations compute exactly
on these corpora (rationals; integer seconds), so the measured
footprint is zero; Delta-8 was a harness defect with a measured field
footprint (106 to 1), not a standard freedom. The real textual gaps -
no arithmetic tolerance anywhere, key 4 undefined for dtn-scheme
endpoints - are now in §8.

Verdict on review 2: the spine sentence needed its frame stated and
the candidate-list freedom needed its interior named; both done. Of
the five proposed fifths, one (traffic shape for the volume channel)
was decided by running the experiment and came out the reviewer's
way, one (probe option) is real and custody-scoped, and three
(horizon, excluded amplification, precision-on-these-corpora) do not
survive contact with the quantification or the induction.

## Actions

- Erratum: anticipated-objection section (rule-c) reverse-admission
  lemma, figure status, pruning survival).
- Paper: abstract and §1 state the audited frame; §4 intro says
  "silent, ambiguous, or self-contradictory"; §4.1 retitled
  ("described as complete"), carries §2.3.2.2, the three readings,
  and the interior (visited price, generation ties); §6.2 marks the
  horizon clip plan-side; §7 induction covers the excluded list; §8
  adds the probe option and arithmetic representation; §9 scopes
  "tried and failed to break" to the instrumented axes.
- Degrees-of-freedom note: candidate-list instance relabeled from
  contradiction to measured clause divergence; §2.3.2.2 scoping noted.
- evl.py: --traffic relay mode; full-corpus runs at contention 8.0
  and 2.0 in out_evl_relay/ (82 and 40 of 1000 plans diverged at
  depth 3; 82 and 36 persist at depth 4; all entry splits);
  evl_adjudicate.py re-replays diverged plans at the deeper cap.
- Paper §7 rewritten from permitted-but-inert to
  traffic-shape-indexed firing, with the relay rows and the
  pinned-tie fix; abstract and §1 follow.
