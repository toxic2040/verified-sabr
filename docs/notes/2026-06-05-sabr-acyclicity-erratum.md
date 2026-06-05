# SABR erratum: the contact graph is declared acyclic and its own construction rule is not

CCSDS 734.3-B-1 (July 2019), §3.2.1, defines the contact graph for
node D at node X as "a conceptual directed acyclic graph that shall
comprise" a root vertex, a terminal vertex, one vertex per relevant
contact, and:

> d) an edge between two vertices wherever one vertex corresponds to a
> contact signifying transmission 'to' some node (the origin of the
> edge) and the other vertex corresponds to a contact signifying
> transmission 'from' that same node (the termination of the edge).

Rule d) is purely topological: it places an edge from contact C1 to
contact C2 whenever C1's receiving node equals C2's sending node, with
no condition on the contacts' time windows. Consequently, for any pair
of contacts C1 = (A -> B) and C2 = (B -> A) - any bidirectional link,
at any times - rule d) produces both the edge C1 -> C2 (via node B)
and the edge C2 -> C1 (via node A): a directed 2-cycle. The graph the
section constructs is therefore cyclic on every contact plan
containing a single two-way link, which is every operational network.
The declaration and the construction rule contradict each other; no
implementation, corpus, or interpretive choice is involved.

Witness, from any plan in this repository's corpora (two lines of a
generated cislunar plan; any real schedule works identically):

    a contact +0 +19968 1 2 2187500
    a contact +0 +21226 2 1 2187500

Contact (1->2) has receiving node 2 = sending node of (2->1), giving
edge (1->2) -> (2->1); contact (2->1) has receiving node 1 = sending
node of (1->2), giving the reverse edge. A 2-cycle, from the rule as
written. (Rule c) admits both vertices whenever it admits one; the
objection below works this out.)

Anticipated objection: figure 3-4 omits the reverse contacts (vertices
2, 4, 6, 8, 10 of the figure 3-2 plan), so a context-aware reader might
take rule c) to exclude them and the graph to be acyclic as intended.
Three replies, in increasing strength:

- Rule c)'s relevance condition is recursive, and it admits the
  reverse whenever it admits the forward. On the spec's own plan:
  contact 2 (B->A) signifies transmission "indirectly to node D"
  because its receiving node A is the sending node of contact 1, which
  is itself indirectly-to-D via contact 3 (B->D); and contact 2 is
  indirectly from X = A because its sending node B receives contact 1,
  which is directly from A. Both conditions are discharged by the
  forward contact itself, so this is general: a forward vertex forces
  its reverse in. The figure contradicts the rule, not the erratum.
- The figure is reached only from the §3.2.1 NOTE ("See figures 3-1,
  3-2, 3-3, and 3-4 for an illustration"), and notes are informative
  in CCSDS books; the normative construction is items a)-d). A figure
  that drops vertices the rule admits is evidence the editors intended
  something narrower than they wrote - which is what an erratum
  reports.
- The cycle survives every pruning the text could be read to imply.
  Contact 2 lies on a §1.4-valid route from A to D - the sequence
  (1, 2, 7, 9) chains A->B->A->B->D and each contact ends no earlier
  than its predecessor begins - so even "keep only contacts on valid
  routes to D" retains vertex 2, and with it edges (1)->(2) and
  (2)->(1). Removing the 2-cycles takes a clause that deletes reverse
  contacts or guards edges temporally, and no such clause exists;
  supplying one is exactly the proposed fix.

Why it matters beyond hygiene: §3.2.6.10 computes routes as "the
shortest path from X to D" through this graph, with Yen's algorithm
suggested in the NOTE. Path-ness (no repeated vertex) is what makes
that computation terminate and what silently restricts generated
routes to no-contact-reuse sequences - a restriction the §1.4 route
definition does not impose (it permits reuse; its only temporal
condition is that contact i+1 end no earlier than contact i begins).
So the acyclicity error is not isolated: the generation procedure
leans on a graph property the construction does not deliver, and the
route class it generates is narrower than the route class the
definitions admit. The §3.2.8.1 NOTE's discussion of routing loops at
the forwarding layer concedes the behavioral consequence.

Minimal fixes, either sufficient:

- add the temporal guard to rule d) that the prose elsewhere assumes -
  an edge from C1 to C2 only where C2's end time is later than C1's
  start time (or a stricter feasibility condition matching §3.2.4.1.1)
  - which removes the 2-cycles that motivate calling the graph
  acyclic in the first place, on plans without time-overlapping
  mutual windows; or
- delete "acyclic" and state that route computation operates on paths
  of the (cyclic) contact graph, making the loopless restriction
  explicit where §3.2.6.10 relies on it.

Either change would also reconcile §3.2.6.10's generation class with
§1.4's route definition, or at least make the divergence a stated
choice rather than an artifact of an inconsistent graph definition.

Status: standalone erratum, extracted from the conformance audit notes
(2026-06-05-sabr-degrees-of-freedom.md) because it depends on nothing
in them - only the standard's text and any contact plan with one
bidirectional link.
