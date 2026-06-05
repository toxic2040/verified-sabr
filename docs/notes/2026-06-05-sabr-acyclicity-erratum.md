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
written.

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
