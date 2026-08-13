#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""studio_roundtrip.py -- regression harness for /ros-studio's seed -> generate round-trip,
and for the JS/Python parity of the editor's preview.

The defect this exists to catch: `init` used to discard the .rossystem exposure LABEL
("odom_pub") and keep only the interface NAME it arrow-points at ("odom"), then re-link
connections by stripping a _<kind> suffix off the label. Any label not spelled <name>_<kind>
failed to re-link and its connection was dropped -- silently, with `generate` still reporting
"0 error(s)". On the TurtleBot 3 example that lost 7 of 10 connections and 14 of 21 exposures.

So the assertion here is not "it runs" or "it lints clean" -- a truncated model does both. It
is that the set of NODES, EXPOSURES and CONNECTIONS survives the trip unchanged.

Four checks per fixture:
  ROUND-TRIP   seed -> generate preserves every node, exposure, namespace and connection.
  ORPHAN-GATE  an arrow target the backing artifact does not declare BLOCKS generation.
  FIELDS       the optional members no example happens to use -- `namespace:` on a node,
               `fromGitRepo:` on a package, a `qos:` block on an interface -- are PLANTED into
               a copy of the fixture and must come back out. `namespace:` was dropped exactly
               this way (ros_plot read it, ros_studio never seeded or emitted it), and a fact
               set can only protect a field some fixture actually carries, so this check
               manufactures the carrier instead of waiting for one.
  PARITY       tests/studio_parity.js: the editor's genSystem()/genRos2() -- pulled out of the
               RENDERED page, not out of the template -- emit the same bytes as
               emit_rossystem()/emit_ros2(). The editor is a live preview of those emitters; if
               the two drift, the page lies about the model and every other check here still
               passes. Needs `node`; SKIPs without it (the other checks still run and gate).

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
PARITY_JS = os.path.join(_HERE, "studio_parity.js")

EXPOSURE_RE = re.compile(
    r'^\s+-\s+"?([\w.-]+)"?:\s*(pub|sub|ss|sc|as|ac)->\s*"?([\w:.-]+)"?\s*$')
CONNECTION_RE = re.compile(r'^\s+-\s+\[\s*"?([\w.-]+)"?\s*,\s*"?([\w.-]+)"?\s*\]\s*$')
NODE_RE = re.compile(r'^\s{4}"?([\w.-]+)"?:\s*$')
NAMESPACE_RE = re.compile(r'^\s+namespace:\s*"?([^"]*?)"?\s*$')
FROMFILE_RE = re.compile(r'^\s{2}fromFile:\s*"?([^"]*?)"?\s*$')
FROMGIT_RE = re.compile(r'^\s{2}fromGitRepo:\s*"?([^"]*?)"?\s*$')
ROS2_QOS_RE = re.compile(r'^\s+(profile|history|depth|reliability|durability|lease_duration'
                         r'|liveliness|lifespan|deadline):\s*(.+?)\s*$')


def facts(path):
    """The fact sets a round-trip must preserve. Comments are stripped: the emission profile
    does not promise to carry them, and SKILL.md rule 12 already requires reporting that.
    Everything else is content and must survive.

    `namespaces` is keyed by the owning node so a namespace cannot silently migrate between
    nodes and still look preserved; `fromFile` is a one-element set so an absent one compares
    equal to an absent one."""
    exposures, connections, nodes = set(), set(), set()
    namespaces, from_file = set(), set()
    current = None
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
            m = NAMESPACE_RE.match(line)
            if m:
                namespaces.add((current, m.group(1)))
                continue
            m = FROMFILE_RE.match(line)
            if m:
                from_file.add(m.group(1))
                continue
            m = NODE_RE.match(line)
            if m:
                current = m.group(1)
                nodes.add(current)
    return {"nodes": nodes, "exposures": exposures, "connections": connections,
            "namespaces": namespaces, "fromFile": from_file}


FACT_KEYS = ("nodes", "exposures", "connections", "namespaces", "fromFile")


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
    for key in FACT_KEYS:
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


# The three optional members no fixture happens to carry. Values are chosen to be legal:
# "1000" ns is inside the ~2.147 s Integer.parseInt ceiling RM035 describes, and `infinite` is
# a bare grammar keyword rather than an EString (quoting it is an RM035 error).
GIT_URL = "https://example.invalid/%s.git"
PLANTED_QOS = ['reliability: reliable', 'durability: volatile', 'liveliness: automatic',
               'deadline: "1000"', 'lifespan: infinite']
NS_VALUE = "/robot%d"


def _plant_namespaces(text):
    """Give every node its own namespace, in the grammar's slot: RosSystem.xtext:60-75 puts
    `namespace:` immediately after `from:`."""
    out, count = [], 0
    for line in text.splitlines():
        out.append(line)
        m = re.match(r"^(\s+)from:\s", re.sub(r"\s+#.*$", "", line.rstrip()))
        if m:
            count += 1
            out.append('%snamespace: "%s"' % (m.group(1), NS_VALUE % count))
    return "\n".join(out) + "\n", count


def _plant_ros2(text, package):
    """fromGitRepo on the package (AMENT_PACKAGE_KEYS puts it before artifacts:) and a qos:
    block on the first interface -- matched on a `type:` whose value is a pkg/seg/Name
    reference, so a parameter's `type: Double` is never mistaken for one."""
    out, planted = [], False
    for line in text.splitlines():
        out.append(line)
        m = re.match(r"^(\s+)type:\s+['\"]?\w+/", line)
        if m and not planted:
            planted = True
            for q in PLANTED_QOS:
                out.append(m.group(1) + "  " + q)
            out.insert(len(out) - len(PLANTED_QOS), m.group(1) + "qos:")
    for i, line in enumerate(out):
        if line.strip() and not line.startswith((" ", "\t", "#")):
            out.insert(i + 1, '  fromGitRepo: "%s"' % (GIT_URL % package))
            break
    return "\n".join(out) + "\n", planted


def check_fields(src, work):
    """Plant namespace / fromGitRepo / qos into a copy of the fixture and require them back.
    Returns (True|False|None, [lines]); None means SKIP."""
    src_dir = os.path.dirname(os.path.abspath(src))
    ros2 = []
    for sub in ("", "rosnodes", "nodes"):
        d = os.path.join(src_dir, sub)
        if os.path.isdir(d):
            ros2 += [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".ros2")]
    if not ros2:
        return None, ["skipped: no sibling .ros2 to carry fromGitRepo/qos"]

    planted_pkgs = {}
    for f in ros2:
        pkg = os.path.splitext(os.path.basename(f))[0]
        text, had_qos = _plant_ros2(open(f, encoding="utf-8").read(), pkg)
        open(os.path.join(work, os.path.basename(f)), "w", encoding="utf-8").write(text)
        planted_pkgs[pkg] = had_qos

    text, n_ns = _plant_namespaces(open(src, encoding="utf-8").read())
    if not n_ns:
        return None, ["skipped: the fixture has no node to carry a namespace"]
    staged = os.path.join(work, os.path.basename(src))
    open(staged, "w", encoding="utf-8").write(text)

    proj = os.path.join(work, "fields.json")
    code, out = run(["init", staged, "--out", proj])
    if code != 0:
        return False, ["init failed on the planted fixture (exit %d):\n%s" % (code, out)]
    outdir = os.path.join(work, "fields-generated")
    code, out = run(["generate", proj, "--outdir", outdir])
    if code != 0:
        return False, ["generate failed on the planted fixture (exit %d):\n%s" % (code, out)]

    fails = []
    gen_sys = [f for f in os.listdir(outdir) if f.endswith(".rossystem")]
    if not gen_sys:
        return False, ["generate wrote no .rossystem"]
    before, after = facts(staged), facts(os.path.join(outdir, gen_sys[0]))
    for key in ("namespaces", "fromFile"):
        missing = sorted(before[key] - after[key])
        added = sorted(after[key] - before[key])
        if missing:
            fails.append("%s: %d of %d LOST -- %s"
                         % (key, len(missing), len(before[key]), missing))
        if added:
            fails.append("%s: %d INVENTED -- %s" % (key, len(added), added))

    gen_ros2 = [f for f in os.listdir(outdir) if f.endswith(".ros2")]
    if not gen_ros2:
        fails.append("generate wrote no .ros2, so fromGitRepo/qos could not be checked")
    for f in gen_ros2:
        pkg = os.path.splitext(f)[0]
        body = open(os.path.join(outdir, f), encoding="utf-8").read()
        want_git = 'fromGitRepo: "%s"' % (GIT_URL % pkg)
        if pkg in planted_pkgs and want_git not in body:
            fails.append("%s.ros2: fromGitRepo LOST (expected %s)" % (pkg, want_git))
        if planted_pkgs.get(pkg):
            for q in PLANTED_QOS:
                if not re.search(r"^\s+%s$" % re.escape(q), body, re.M):
                    fails.append("%s.ros2: qos '%s' LOST" % (pkg, q))
    return not fails, fails


def check_parity(work, proj_name="project.json", gen_name="generated"):
    """Hand artefacts an earlier check just built to tests/studio_parity.js, which pulls the
    shipped pure functions out of the RENDERED editor and diffs its .rossystem/.ros2 previews
    against the Python emitter's bytes. Returns (True|False|None, [lines]); None means SKIP.

    Run over the FIELDS artefacts as well as the plain round-trip ones, because a fact set the
    fixture does not carry is a preview the editor is never asked to produce: namespace, qos
    and fromGitRepo would each pass this check vacuously on examples/ alone."""
    node = shutil.which("node")
    if node is None:
        return None, ["skipped: `node` is not on PATH — the editor's JS cannot be run"]
    if not os.path.isfile(PARITY_JS):
        return None, ["skipped: %s is missing" % PARITY_JS]
    proj = os.path.join(work, proj_name)
    outdir = os.path.join(work, gen_name)
    if not os.path.isfile(proj) or not os.path.isdir(outdir):
        return False, ["the round-trip produced nothing to compare against"]
    cand = [f for f in os.listdir(outdir) if f.endswith(".rossystem")]
    if not cand:
        return False, ["no generated .rossystem to compare against"]

    html = os.path.join(work, os.path.splitext(proj_name)[0] + ".editor.html")
    code, out = run(["render", proj, "--out", html])
    if code != 0:
        return False, ["render failed (exit %d):\n%s" % (code, out)]
    proc = subprocess.run([node, PARITY_JS, "--project", proj, "--html", html,
                           "--expect", os.path.join(outdir, cand[0])],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    text = proc.stdout.decode("utf-8", "replace")
    if proc.returncode == 0:
        return True, []
    return False, [line for line in text.splitlines() if line.strip()]


def main(argv):
    targets = argv[1:]
    if not targets:
        ex = os.path.join(PLUGIN_ROOT, "examples")
        targets = sorted(os.path.join(ex, f) for f in os.listdir(ex)
                         if f.endswith(".rossystem"))
    if not targets:
        print("no .rossystem to test")
        return 1

    def verdict(state):
        return "PASS" if state else ("SKIP" if state is None else "FAIL")

    print("%-38s %-12s %-12s %-9s %-12s"
          % ("FIXTURE", "ROUND-TRIP", "ORPHAN-GATE", "FIELDS", "PARITY"))
    print("-" * 87)
    failures = 0
    for src in targets:
        work = tempfile.mkdtemp(prefix="studio-rt-")
        try:
            ok, why = check_roundtrip(src, work)
            gate_dir = os.path.join(work, "gate")
            os.makedirs(gate_dir, exist_ok=True)
            gate_ok, gate_why = check_orphan_gate(src, gate_dir)
            fld_dir = os.path.join(work, "fields")
            os.makedirs(fld_dir, exist_ok=True)
            fld_ok, fld_why = check_fields(src, fld_dir)
            par_ok, par_why = check_parity(work)
            if fld_ok:      # only meaningful once the planted artefacts exist
                f_ok, f_why = check_parity(fld_dir, "fields.json", "fields-generated")
                if f_ok is False:
                    par_ok = False
                    par_why = par_why + ["[planted fields] " + line for line in f_why]
            print("%-38s %-12s %-12s %-9s %-12s" % (
                os.path.basename(src), verdict(ok), verdict(gate_ok), verdict(fld_ok),
                verdict(par_ok)))
            for line in why:
                failures += 1
                print("    round-trip: %s" % line)
            if gate_ok is False:
                for line in gate_why:
                    failures += 1
                    print("    orphan-gate: %s" % line)
            if fld_ok is False:
                for line in fld_why:
                    failures += 1
                    print("    fields: %s" % line)
            elif fld_ok is None:
                for line in fld_why:
                    print("    fields: %s" % line)
            if par_ok is False:
                for line in par_why:
                    failures += 1
                    print("    parity: %s" % line)
            elif par_ok is None:
                for line in par_why:
                    print("    parity: %s" % line)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    print()
    print("%d fixture(s), %d failure(s)" % (len(targets), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
