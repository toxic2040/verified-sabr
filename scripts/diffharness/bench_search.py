#!/usr/bin/env python3
"""Wall-clock cost of the compiled sabrsearch binary vs contact-plan size.

Builds integer-field ionrc slices from a generated plan's contacts.json
(start = floor, end = ceil, rate = floor, owlt = round-half-up integer light
seconds — the generator's quantization) and times one sabrsearch process per
(n, query). Queries follow the repo's Lunanet test guards: surface->ground,
station->surface, and an unreachable endpoint (the no-route case exhausts the
search space, so it is the worst case, not a filler). Node names resolve to
ionrc numbers via the same sorted-name rule the generator uses.

Usage:
  bench_search.py --plan-dir <dir with contacts.json>
                  [--sizes 50,100,200,300,418] [--timeout 120] [--t0 0]
"""

import argparse
import json
import math
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BIN = Path(__file__).resolve().parents[2] / ".lake" / "build" / "bin" / "sabrsearch"

QUERY_PAIRS = [
    ("SHACKLETON", "CANBERRA"),
    ("GATEWAY", "SHACKLETON"),
    ("SHACKLETON", "NOSUCHNODE"),
]


def load_contacts(plan_dir):
    contacts = json.loads((plan_dir / "contacts.json").read_text())
    names = sorted({c["from_node"] for c in contacts}
                   | {c["to_node"] for c in contacts})
    nmap = {name: i + 1 for i, name in enumerate(names)}
    rows = []
    for c in sorted(contacts,
                    key=lambda c: (c["start_s"], c["from_node"], c["to_node"])):
        start = int(math.floor(float(c["start_s"])))
        stop = int(math.ceil(float(c["start_s"]) + float(c["duration_s"])))
        rate = int(math.floor(float(c["rate_Bps"])))
        owlt = int(math.floor(float(c["latency_s"]) + 0.5))
        a, b = nmap[c["from_node"]], nmap[c["to_node"]]
        rows.append((f"a contact +{start} +{stop} {a} {b} {rate}",
                     f"a range +{start} +{stop} {a} {b} {owlt}"))
    return rows, nmap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-dir", required=True)
    ap.add_argument("--sizes", default="50,100,200,300,418")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--t0", default="0")
    args = ap.parse_args()

    plan_dir = Path(args.plan_dir)
    rows, nmap = load_contacts(plan_dir)
    n_total = len(rows)
    sizes = sorted({min(int(s), n_total) for s in args.sizes.split(",")})

    print(f"plan: {plan_dir}  contacts: {n_total}  binary: {BIN}")
    if not BIN.exists():
        sys.exit("sabrsearch binary missing; run: lake build sabrsearch")

    print(f"{'n':>5} {'src->dst':<24} {'seconds':>9}  result")
    for n in sizes:
        body = "\n".join(line for pair in rows[:n] for line in pair) + "\n"
        with tempfile.TemporaryDirectory() as td:
            plan_path = Path(td) / "slice.ionrc"
            plan_path.write_text(body)
            for src, dst in QUERY_PAIRS:
                q = f"{nmap.get(src, src)} {nmap.get(dst, '999')} {args.t0}\n"
                q_path = Path(td) / "q.txt"
                q_path.write_text(q)
                t0 = time.monotonic()
                try:
                    out = subprocess.run(
                        [str(BIN), str(plan_path), str(q_path)],
                        capture_output=True, text=True, timeout=args.timeout)
                    dt = time.monotonic() - t0
                    tail = out.stdout.strip().split(" ", 4)[-1][:40] if out.stdout else "(no output)"
                    print(f"{n:>5} {src + '->' + dst:<24} {dt:>9.3f}  {tail}")
                except subprocess.TimeoutExpired:
                    print(f"{n:>5} {src + '->' + dst:<24} {'>' + str(args.timeout):>9}  TIMEOUT")


if __name__ == "__main__":
    main()
