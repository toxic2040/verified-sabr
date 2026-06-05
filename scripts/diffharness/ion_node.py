#!/usr/bin/env python3
"""Throwaway single-node ION 4.1.4 lifecycle for CGR oracle queries.

ION is a host singleton (shared memory and semaphores), so plans are processed
strictly serially — one node up at a time, torn down with killm between plans.
That serialization is a hardware constraint, not a convenience fallback.

Time anchoring: the generator emits relative times (+N). Loading those
verbatim would anchor them to ionadmin's own integer reference instant, which
the harness cannot read exactly — and arrival times depend on the exact
dispatch second, so a +-1 s anchor ambiguity would poison exact comparison.
Instead the node loads the plan with ABSOLUTE timestamps: rel time t maps to
the chosen integer unix `anchor` + t. The whole ION timeline is then known
exactly, dispatch offsets are computed against the same anchor, and the
dispatch instant reported back by cgrfetch converts to an exact integer
plan-relative time.

The node boots as one of the contact plan's own node numbers (cgrfetch
computes routes from the LOCAL node).

Corpus validation (the `validate` subcommand) drives live ION over the
dsn_real_v1 corpus, whose plans carry up to 47 nodes and up to ~140
contacts across many distinct query sources. Each query fixes its own
(src, dst, t0), so the node is rebooted once per distinct source and every
query for that source is dispatched on that boot; ION's host-singleton
constraint keeps the whole sweep serial. The node-number remap in the
plan manifest keeps ids dense (1..N), so the per-neighbor bprc/ipnrc
templating below holds unchanged at this scale — each first hop still
needs its own egress plan and outduct, or cgrfetch rejects the route.

Each live dispatch is graded against the frozen ION-mirror prediction in
out_s5/predictions.jsonl, which is computed in ION's own margin frame
(owlt' = owlt + (125*owlt)//186282). cgrfetch's dispatch instant drifts a
second or two off the requested t0 because cgrfetch re-reads the wall
clock at its own start; the route is invariant across that drift on these
full-window plans, but the arrival shifts with it. The route is therefore
graded against the frozen prediction's hop sequence, and the arrival
against the mirror recomputed at ION's MEASURED dispatch instant — the
same measured-instant discipline compare.py uses for the lean side. A
none verdict is confirmed two-sided against the frozen None.
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

IONRC_HEAD = "1 {node} ''\ns\n"

BPRC_TEMPLATE = """\
1
a scheme ipn 'ipnfw' 'ipnadminep'
a endpoint ipn:{node}.1 q
a endpoint ipn:{node}.2 q
a protocol udp 1400 100
a induct udp 0.0.0.0:4556 udpcli
{outducts}
s
"""


def _ts(unix):
    return datetime.fromtimestamp(int(unix), tz=timezone.utc).strftime(
        "%Y/%m/%d-%H:%M:%S")


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=180,
                          **kw)


def _run_admin(cmd, log_path):
    """Run a daemon-spawning ION admin tool with output to a log FILE.

    Capturing via pipes deadlocks: the `s` command forks long-lived daemons
    (rfxclock, ipnfw, ...) that inherit the pipe write ends, so waiting for
    pipe EOF blocks long after the admin tool itself exits. A file descriptor
    has no EOF-wait, so subprocess.run returns when the tool exits and the
    daemons keep logging harmlessly.
    """
    log_path = Path(log_path)
    with log_path.open("ab") as fh:
        fh.write(f"\n==== {' '.join(map(str, cmd))}\n".encode())
        fh.flush()
        proc = subprocess.run(list(map(str, cmd)), stdout=fh, stderr=fh,
                              timeout=180)
    if proc.returncode != 0:
        tail = log_path.read_text(errors="replace")[-500:]
        raise RuntimeError(f"{cmd[0]} failed rc={proc.returncode}:\n{tail}")


# Daemons our minimal node can start (ionadmin/bpadmin/ipnadmin children).
ION_DAEMONS = ["rfxclock", "bpclm", "bpclock", "bptransit", "ipnfw",
               "ipnadminep", "udpcli", "udpclo", "ionadmin", "bpadmin",
               "ipnadmin", "cgrfetch"]


def purge_ion():
    """Targeted ION cleanup: our daemon set plus user-owned ION IPC.

    ION's stock killm greps a ~330-name process list with one awk spawn per
    name; under parallel build load on this host that exceeds a minute per
    call, which is unusable inside a 1000-plan loop. ION's footprint here is
    exactly: the daemons above, SysV shared-memory segments owned by this
    user, and POSIX named semaphores /dev/shm/sem.ion:*. Assumption recorded:
    this user runs no other SysV-shm software on this host.
    """
    for name in ION_DAEMONS:
        subprocess.run(["pkill", "-x", name], capture_output=True)
    time.sleep(0.2)
    out = _run(["ipcs", "-m"])
    user = os.environ.get("USER", "")
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 6 and parts[2] == user and parts[0].startswith("0x"):
            _run(["ipcrm", "-m", parts[1]])
    for sem in glob.glob("/dev/shm/sem.ion:*"):
        try:
            os.unlink(sem)
        except OSError:
            pass


class IonNode:
    """Context manager: boot ION as `node_num` with `plan_path` loaded at an
    exact integer unix `anchor` (defaults to boot instant minus 2 s, keeping
    +0 contacts alive while everything else lies in the near future)."""

    def __init__(self, node_num, plan_path, workdir, registration=False):
        self.node = int(node_num)
        self.plan_path = Path(plan_path)
        self.workdir = Path(workdir)
        self.registration = registration
        self.anchor = None
        self.node_ids = set()

    def _absolute_plan_lines(self):
        lines = []
        for raw in self.plan_path.read_text().splitlines():
            parts = raw.split()
            if len(parts) == 7 and parts[0] == "a" and parts[1] in (
                    "contact", "range"):
                s = int(parts[2].lstrip("+"))
                e = int(parts[3].lstrip("+"))
                a, b = int(parts[4]), int(parts[5])
                self.node_ids.update((a, b))
                lines.append(
                    f"a {parts[1]} {_ts(self.anchor + s)} "
                    f"{_ts(self.anchor + e)} {a} {b} {parts[6]}")
        if self.registration:
            regs = [f"a contact -1 0 {k} {k} 0"
                    for k in sorted(self.node_ids)]
            lines = regs + lines
        return "\n".join(lines)

    def __enter__(self):
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.anchor = int(time.time()) - 2
        plan_lines = self._absolute_plan_lines()
        ionrc = self.workdir / "node.ionrc"
        bprc = self.workdir / "node.bprc"
        ipnrc = self.workdir / "node.ipnrc"
        ionrc.write_text(IONRC_HEAD.format(node=self.node) + plan_lines + "\n")
        # explicit outducts: ipn plan expressions attach ducts but do not
        # create them, and ION 4.1.4 rejects promiscuous '*' ducts
        outducts = "\n".join(
            f"a outduct udp 127.0.0.1:{4556 + k} udpclo"
            for k in sorted(self.node_ids) if k != self.node)
        bprc.write_text(BPRC_TEMPLATE.format(node=self.node,
                                             outducts=outducts))
        ipnrc.write_text("\n".join(
            f"a plan {k} udp/127.0.0.1:{4556 + k}"
            for k in sorted(self.node_ids) if k != self.node) + "\n")

        purge_ion()
        log = self.workdir / "ion_admin.log"
        for tool, rc in (("ionadmin", ionrc), ("bpadmin", bprc),
                         ("ipnadmin", ipnrc)):
            _run_admin([tool, rc], log)
        return self

    def offset_for(self, t_plan_rel):
        """cgrfetch -t offset that lands the dispatch at anchor + t_plan_rel."""
        return max(0, int(self.anchor + t_plan_rel - time.time()))

    def any_outduct(self, wait_s=15.0):
        """One existing outduct expression for cgrfetch -d.

        ION 4.1.4 rejects the promiscuous 'udp:*' default ("ION no longer
        supports promiscuous ('*') outduct expressions"). The per-neighbor
        plan expressions auto-create concrete udp outducts, but bpclm spawns
        them asynchronously after ipnadmin returns — so discover them with
        cgrfetch's own `-d list`, polling briefly. Transmission never happens
        in a cgrfetch simulation, so which duct is named does not affect the
        computed routes.
        """
        deadline = time.time() + wait_s
        while True:
            out = _run(["cgrfetch", "-d", "list", "0"])
            ducts = [l.strip() for l in (out.stdout + out.stderr).splitlines()
                     if l.strip().startswith("udp:")]
            if ducts:
                return ducts[0]
            if time.time() > deadline:
                raise RuntimeError(
                    f"no udp outducts appeared within {wait_s}s:\n"
                    f"{out.stdout[-300:]}\n{out.stderr[-300:]}")
            time.sleep(0.5)

    def to_rel(self, t_unix):
        """Exact plan-relative seconds for an ION-reported unix time."""
        return int(t_unix) - self.anchor

    def __exit__(self, *exc):
        # official admin stops first (clean daemon shutdown), then the purge
        log = self.workdir / "ion_admin.log"
        for cmd in (["bpadmin", "."], ["ionadmin", "."]):
            try:
                _run_admin(cmd, log)
            except RuntimeError:
                pass  # stop-path best effort; purge_ion follows regardless
        time.sleep(0.5)
        purge_ion()
        return False


# --------------------------------------------------------- corpus validation

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cgr_oracle import fetch_routes  # noqa: E402
from predict import parse_plan, ion_route  # noqa: E402


def load_queries(pdir):
    """dsn_real_v1 queries.jsonl ({src,dst,t0}), or the corpus_v3-family
    pairs.jsonl (query-flagged pairs with a single t0_s each)."""
    qf = pdir / "queries.jsonl"
    if qf.exists():
        return [json.loads(line) for line in open(qf)]
    out = []
    for line in open(pdir / "pairs.jsonl"):
        p = json.loads(line)
        if p.get("query"):
            out.append({"src": p["src"], "dst": p["dst"], "t0": p["t0_s"]})
    return out


def load_predictions(path, plan_id):
    """Frozen ion_pred per (src, dst, t0) for one plan; None if no file."""
    if not path:
        return None
    preds = {}
    for line in open(path):
        rec = json.loads(line)
        if rec.get("plan_id") != plan_id or "error" in rec:
            continue
        for q in rec["queries"]:
            preds[(q["src"], q["dst"], q["t0"])] = q["ion_pred"]
    return preds


def _ion_chosen(routes):
    """ION's pick: SELECTED route, else best CONSIDERED, else none — the same
    rule compare.py applies (flag DEFAULT/IDENTIFIED carry an ignoreReason)."""
    selected = [r for r in routes if r["flag"] == 3]
    if selected:
        return min(selected, key=lambda r: r["arrival_rel"])
    considered = [r for r in routes if r["flag"] == 2]
    if considered:
        return min(considered, key=lambda r: r["arrival_rel"])
    return None


def validate_plan(pdir, predictions, sink, settle_s=1.0):
    """Run every dispatch of one dsn plan on live ION, one boot per distinct
    source, and write one graded JSONL row per dispatch with flush().

    The frozen prediction is graded by ROUTE (dispatch-invariant on these
    full-window plans); the live ARRIVAL is graded against the ION mirror
    recomputed at ION's measured dispatch instant, since cgrfetch's wall-clock
    re-read drifts the dispatch a second or two off t0 (module docstring).
    """
    nm = json.load(open(pdir / "plan_manifest.json"))["node_map"]
    queries = load_queries(pdir)
    contacts, ranges = parse_plan(pdir)
    icontacts = sorted((int(f), int(t), s, e, v)
                       for f, t, s, e, v in contacts)
    iranges = [(int(f), int(t), s, e, v) for f, t, s, e, v in ranges]

    by_src = defaultdict(list)
    for q in queries:
        by_src[q["src"]].append(q)

    tally = {"dispatches": 0, "route_exact": 0, "arrival_match": 0,
             "none_match": 0, "mismatch": 0}
    raw_dir = pdir.name
    for src in sorted(by_src):
        workdir = Path(sink.name).parent / "raw" / pdir.name / src
        with IonNode(nm[src], pdir / "contact_plan.ionrc", workdir) as ion:
            time.sleep(settle_s)  # let bp daemons settle before simulating
            for q in by_src[src]:
                dst, t0 = q["dst"], q["t0"]
                oracle = fetch_routes(nm[dst], t0, ion, workdir)
                drel = oracle["dispatch_rel"]
                chosen = _ion_chosen(oracle["routes"])
                mirror = ion_route(icontacts, iranges, nm[src], nm[dst], drel)
                frozen = (predictions.get((src, dst, t0))
                          if predictions is not None else None)

                row = {"plan_id": pdir.name, "src": src, "dst": dst,
                       "t0": t0, "dispatch_rel": drel,
                       "raw": oracle["raw_path"]}
                tally["dispatches"] += 1
                if chosen is None:
                    row["ion"] = None
                    row["frozen"] = frozen
                    # none confirmed against the frozen None and the mirror
                    ok = (predictions is None or frozen is None) \
                        and mirror is None
                    row["none_match"] = ok
                    if ok:
                        tally["none_match"] += 1
                    else:
                        tally["mismatch"] += 1
                        row["mismatch"] = True
                        row["mirror"] = mirror
                else:
                    live_hops = [[int(f), int(t)] for f, t in chosen["hops"]]
                    row["ion"] = {"arrival_rel": chosen["arrival_rel"],
                                  "hops": live_hops}
                    frozen_hops = ([[f, t] for f, t, _ in frozen["hops"]]
                                   if frozen else None)
                    route_ok = (predictions is None) or \
                        (live_hops == frozen_hops)
                    arr_ok = (mirror is not None
                              and chosen["arrival_rel"] == mirror["arrival"])
                    row["route_exact"] = route_ok
                    row["arrival_match"] = arr_ok
                    if route_ok:
                        tally["route_exact"] += 1
                    if arr_ok:
                        tally["arrival_match"] += 1
                    if not (route_ok and arr_ok):
                        tally["mismatch"] += 1
                        row["mismatch"] = True
                        row["frozen"] = frozen
                        row["mirror"] = mirror
                sink.write(json.dumps(row) + "\n")
                sink.flush()
    return tally


def cmd_validate(args):
    corpus = Path(args.corpus)
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)

    done = set()
    if outp.exists():
        for line in open(outp):
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if "plan_done" in rec:
                done.add(rec["plan_done"])

    plans = [p for p in sorted(corpus.glob(args.glob))
             if p.is_dir() and (p / "contact_plan.ionrc").exists()
             and p.name not in done]
    if args.limit_plans:
        plans = plans[:args.limit_plans]
    print(f"{len(done)} plans done, {len(plans)} to go", flush=True)

    with open(outp, "a") as sink:
        for i, pdir in enumerate(plans):
            t0 = time.time()
            try:
                tally = validate_plan(pdir, load_predictions(
                    args.predictions, pdir.name), sink, args.settle)
                rec = {"plan_done": pdir.name, "tally": tally,
                       "wall_s": round(time.time() - t0, 1)}
            except Exception as e:  # one plan must never kill the batch
                rec = {"plan_done": pdir.name, "error": repr(e),
                       "wall_s": round(time.time() - t0, 1)}
            sink.write(json.dumps(rec) + "\n")
            sink.flush()
            print(f"[{i + 1}/{len(plans)}] {pdir.name} "
                  f"{rec.get('tally', rec.get('error'))} "
                  f"{rec['wall_s']}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="live ION over the dsn_real_v1 corpus")
    v.add_argument("--corpus", required=True)
    v.add_argument("--glob", default="dsn_real_v1_plan_*")
    v.add_argument("--predictions", default=None,
                   help="frozen ION-mirror predictions JSONL to grade against")
    v.add_argument("--out", default="out_s5/ion_live.jsonl")
    v.add_argument("--limit-plans", type=int, default=None)
    v.add_argument("--settle", type=float, default=1.0,
                   help="seconds to let bp daemons settle after each boot")
    v.set_defaults(fn=cmd_validate)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
