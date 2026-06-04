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
"""

import glob
import os
import subprocess
import time
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
