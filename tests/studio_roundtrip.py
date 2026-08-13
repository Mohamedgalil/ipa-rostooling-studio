#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""studio_roundtrip.py -- regression harness for /ros-studio's seed -> generate round-trip.

The defect this exists to catch: `init` used to discard the .rossystem exposure LABEL
("odom_pub") and keep only the interface NAME it arrow-points at ("odom"), then re-link
connections by stripping a _<kind> suffix off the label. Any label not spelled <name>_<kind>
failed to re-link and its connection was dropped -- silently, with `generate` still reporting
"0 error(s)". On the TurtleBot 3 example that lost 7 of 10 connections and 14 of 21 exposures.

So the assertion here is not "it runs" or "it lints clean" -- a truncated model does both. It
is that the set of NODES, EXPOSURES and CONNECTIONS survives the trip unchanged.

    python tests/studio_roundtrip.py [FILE.rossystem ...]

With no argument it runs every .rossystem under examples/. Exit 0 iff every check passes.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(_HERE)
SCRIPTS = os.path.join(PLUGIN_ROOT, "scripts")
STUDIO = os.path.join(SCRIPTS, "ros_studio.py")

EXPOSURE_RE = re.compile(
    r'^\s+-\s+"?([\w.-]+)"?:\s*(pub|sub|ss|sc|as|ac)->\s*"?([\w:.-]+)"?\s*$')
CONNECTION_RE = re.compile(r'^\s+-\s+\[\s*"?([\w.-]+)"?\s*,\s*"?([\w.-]+)"?\s*\]\s*$')
NODE_RE = re.compile(r'^\s{4}"?([\w.-]+)"?:\s*$')


def facts(path):
    """The three fact sets a round-trip must preserve. Comments are stripped: the emission
    profile does not promise to carry them, and SKILL.md rule 12 already requires reporting
    that. Everything else is content and must survive."""
    exposures, connections, nodes = set(), set(), set()
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = re.sub(r"\s+#.*$", "", line.rstrip())
            m = EXPOSURE_RE.match(line)
            if m:
                exposures.add(m.groups())
                continue
            m = CONNECTION_RE.match(line)
            if m:
                connections.add(m.groups())
                continue
            m = NODE_RE.match(line)
            if m:
                nodes.add(m.group(1))
    return {"nodes": nodes, "exposures": exposures, "connections": connections}


def run(args, cwd=None):
    proc = subprocess.run([sys.executable, STUDIO] + args, cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def check_roundtrip(src, work):
    """Seed from `src`, generate, and compare fact sets. Returns (ok, [failure lines])."""
    staged = os.path.join(work, os.path.basename(src))
    shutil.copy(src, staged)
    # the sibling .ros2 files the seeder opens to recover types must travel with it
    src_dir = os.path.dirname(os.path.abspath(src))
    for sub in ("", "rosnodes", "nodes"):
        d = os.path.join(src_dir, sub)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.endswith(".ros2"):
                shutil.copy(os.path.join(d, f), os.path.join(work, f))

    proj = os.path.join(work, "project.json")
    code, out = run(["init", staged, "--out", proj])
    if code != 0:
        return False, ["init failed (exit %d):\n%s" % (code, out)]
    outdir = os.path.join(work, "generated")
    code, out = run(["generate", proj, "--outdir", outdir])
    if code != 0:
        return False, ["generate failed (exit %d):\n%s" % (code, out)]

    gen = os.path.join(outdir, os.path.basename(src))
    if not os.path.isfile(gen):
        cand = [f for f in os.listdir(outdir) if f.endswith(".rossystem")]
        if not cand:
            return False, ["generate wrote no .rossystem"]
        gen = os.path.join(outdir, cand[0])

    before, after = facts(staged), facts(gen)
    failures = []
    for key in ("nodes", "exposures", "connections"):
        missing = sorted(before[key] - after[key])
        added = sorted(after[key] - before[key])
        if missing:
            failures.append("%s: %d of %d LOST -- %s"
                            % (key, len(missing), len(before[key]), missing))
        if added:
            failures.append("%s: %d INVENTED -- %s" % (key, len(added), added))
    return not failures, failures


def check_orphan_gate(src, work):
    """An exposure whose arrow target the backing artifact does not declare must BLOCK
    generation before anything is written -- not be dropped, and not be written out for the
    language server to reject."""
    src_dir = os.path.dirname(os.path.abspath(src))
    ros2 = []
    for sub in ("", "rosnodes", "nodes"):
        d = os.path.join(src_dir, sub)
        if os.path.isdir(d):
            ros2 += [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".ros2")]
    if not ros2:
        return None, ["skipped: no sibling .ros2 to back a node"]
    for f in ros2:
        shutil.copy(f, os.path.join(work, os.path.basename(f)))

    text = open(src, encoding="utf-8").read()
    m = None
    for line in text.splitlines():
        m = EXPOSURE_RE.match(re.sub(r"\s+#.*$", "", line.rstrip()))
        if m:
            break
    if not m:
        return None, ["skipped: no exposure to mutate"]
    indent = " " * 8
    artifact = m.group(3).split("::")[0]
    injected = '%s- "zzz_ghost": %s-> "%s::zzz_no_such_iface"' % (indent, m.group(2), artifact)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if EXPOSURE_RE.match(re.sub(r"\s+#.*$", "", line.rstrip())):
            lines.insert(i + 1, injected)
            break
    staged = os.path.join(work, "orphan.rossystem")
    open(staged, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    proj = os.path.join(work, "orphan.json")
    code, out = run(["init", staged, "--out", proj])
    if code != 0:
        return False, ["init failed on the mutated file (exit %d)" % code]
    outdir = os.path.join(work, "orphan-generated")
    code, out = run(["generate", proj, "--outdir", outdir])
    fails = []
    if code == 0:
        fails.append("generate ACCEPTED an unresolvable arrow target (expected exit 1)")
    if os.path.isdir(outdir) and os.listdir(outdir):
        fails.append("generate wrote files despite the gate: %s" % os.listdir(outdir))
    return not fails, fails


def main(argv):
    targets = argv[1:]
    if not targets:
        ex = os.path.join(PLUGIN_ROOT, "examples")
        targets = sorted(os.path.join(ex, f) for f in os.listdir(ex)
                         if f.endswith(".rossystem"))
    if not targets:
        print("no .rossystem to test")
        return 1

    print("%-38s %-12s %-12s" % ("FIXTURE", "ROUND-TRIP", "ORPHAN-GATE"))
    print("-" * 64)
    failures = 0
    for src in targets:
        work = tempfile.mkdtemp(prefix="studio-rt-")
        try:
            ok, why = check_roundtrip(src, work)
            gate_dir = os.path.join(work, "gate")
            os.makedirs(gate_dir, exist_ok=True)
            gate_ok, gate_why = check_orphan_gate(src, gate_dir)
            print("%-38s %-12s %-12s" % (
                os.path.basename(src),
                "PASS" if ok else "FAIL",
                "PASS" if gate_ok else ("SKIP" if gate_ok is None else "FAIL")))
            for line in why:
                failures += 1
                print("    round-trip: %s" % line)
            if gate_ok is False:
                for line in gate_why:
                    failures += 1
                    print("    orphan-gate: %s" % line)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    print()
    print("%d fixture(s), %d failure(s)" % (len(targets), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
