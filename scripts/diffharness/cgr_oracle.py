#!/usr/bin/env python3
"""cgrfetch wrapper: simulate a CGR dispatch on the running ION node.

cgrfetch(1) traces a CGR computation from the LOCAL node to DEST-NODE at a
requested dispatch offset and emits JSON describing the routes considered and
chosen. Payload size 0 keeps radiation latency at zero; the expiration offset
is raised far beyond any query horizon so deadline filtering (out of the v1
model) cannot bind.

JSON schema, pinned from an observed ION 4.1.4 run (raw sample kept with the
smoke results):

  constants: {DEFAULT:0, IDENTIFIED:1, CONSIDERED:2, SELECTED:3}
  params:    {localNode, destNode, dispatchTime, expirationTime, bundleSize,
              minLatency}                            -- unix-second times
  routes[]:  {flag, fromTime, deliveryTime, maxCapacity, payloadClass,
              ignoreReason, graph}

Route hop sequences are not in the JSON as structured data; they are encoded
in the embedded graphviz SVG, where the route's edges are stroked #ec1c24.
The hops are recovered by decoding the SVG and chaining the red directed
edges from the local node.
"""

import base64
import json
import re
import subprocess
from pathlib import Path

EXPIRATION_OFFSET = 172800  # 2 days; queries stay far inside it

FLAG_CONSIDERED = 2
FLAG_SELECTED = 3

_EDGE_RE = re.compile(
    r'<g id="edge\d+" class="edge">.*?<title>(\d+)&#45;&gt;(\d+)</title>'
    r'.*?stroke="(#[0-9a-f]{6})"', re.S)
ROUTE_STROKE = "#ec1c24"


class SchemaDrift(RuntimeError):
    pass


def _hops_from_svg(graph_data_uri, local_node):
    """Ordered (from, to) hops: red-stroked edges chained from local_node."""
    b64 = graph_data_uri.split("base64,", 1)[1]
    svg = base64.b64decode(b64).decode("utf-8", errors="replace")
    red = [(int(a), int(b)) for a, b, color in _EDGE_RE.findall(svg)
           if color == ROUTE_STROKE and a != b]
    hops, node = [], int(local_node)
    pool = list(red)
    while pool:
        nxt = [e for e in pool if e[0] == node]
        if not nxt:
            break
        hop = nxt[0]
        hops.append(hop)
        pool.remove(hop)
        node = hop[1]
    return hops


def fetch_routes(dest_node, t0_plan_rel, ion, out_dir):
    """Run cgrfetch toward `dest_node` at plan-relative time `t0_plan_rel`.

    Returns {"dispatch_rel": int, "routes": [...], "raw_path": str} with all
    times as exact integer plan-relative seconds via the node's integer unix
    anchor (see ion_node.py). The caller queries the Lean side at the
    MEASURED dispatch_rel, making both sides' dispatch instants identical by
    construction. Each route carries: arrival_rel, fromtime_rel, flag,
    ignore_reason, hops [(from, to)].
    """
    offset = ion.offset_for(t0_plan_rel)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"cgrfetch_{dest_node}_{int(t0_plan_rel)}.json"
    cmd = ["cgrfetch", "-t", str(offset), "-e", str(EXPIRATION_OFFSET),
           "-q", "-o", str(raw_path), "-d", ion.any_outduct(),
           str(dest_node)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0 or not raw_path.exists():
        raise RuntimeError(
            f"cgrfetch failed rc={proc.returncode}: {proc.stderr[:500]}")
    doc = json.loads(raw_path.read_text())

    try:
        params = doc["params"]
        dispatch_rel = ion.to_rel(params["dispatchTime"])
        local = params["localNode"]
        routes = []
        for r in doc.get("routes", []):
            routes.append({
                "arrival_rel": ion.to_rel(r["deliveryTime"]),
                "fromtime_rel": ion.to_rel(r["fromTime"]),
                "flag": int(r["flag"]),
                "ignore_reason": r.get("ignoreReason", ""),
                "hops": _hops_from_svg(r["graph"], local),
            })
    except (KeyError, TypeError, IndexError) as e:
        raise SchemaDrift(
            f"cgrfetch JSON schema drift ({e}); raw sample: {raw_path}") from e
    return {"dispatch_rel": dispatch_rel, "routes": routes,
            "raw_path": str(raw_path)}
