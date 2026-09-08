#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_golden.py -- pin the extractors' output to a committed golden file.

    py tests/extract_golden.py             # check
    py tests/extract_golden.py --update    # rewrite the golden after an INTENDED change

Why this exists
---------------
`scripts/extract_ros2_interfaces.py` and `scripts/extract_rossystem.py` are the deterministic
half of this plugin: everything they emit is supposed to be literal in the source, and an agent
downstream is told not to re-derive it. That makes a silent change in what they emit the most
expensive kind of regression here -- the output still lints clean, the oracle still accepts it,
and the only thing that changed is whether the model is TRUE. Nothing catches that except
comparing against output somebody has read.

So: run both scripts over `tests/fixtures/extract/src/`, a miniature two-package workspace with
a launch file, and diff every byte against `tests/fixtures/extract/golden/`. Any edit to either
script that changes emitted output shows up here as a diff to read and either accept
(`--update`) or fix.

The fixture is not the real robot
---------------------------------
The models this plugin was developed against come from a real driver tree that is not in this
repo and cannot be committed to it, so a golden keyed to that tree would only run on one
machine. The fixture reproduces the SHAPES that mattered there instead: a C++ package with
`generate_parameter_library` parameters and a non-literal topic name, a Python `rclpy` package,
a launch file mixing project-local nodes with one that resolves against the vendored catalogue.
Not covered, and worth knowing: `controllers.yaml` controller-instance resolution, `.msg`
transcription (`--emit-msgs`), and `IncludeLaunchDescription` (which the extractor does not
follow at all).

Two named checks on top of the diff
-----------------------------------
A byte diff tells you SOMETHING changed, not what it means. Two bug classes have actually
shipped here, so they are asserted by name as well -- a failure should say which invariant
broke, not just print a diff:

1. A parameter whose `default_value` is the *string* `"false"` under a declared `bool` must
   render `false`. Python truthiness makes a non-empty string true, so the naive reading emits
   `default: true` -- the exact opposite of the source, and it passes every other check in this
   repo while asserting the opposite of the truth.
2. A topic name built from literals plus one identifier must produce a `# FLAG` carrying the
   candidate names as evidence, and must emit NO declaration for it. Emitting the candidates
   would turn a visible unknown into an invisible one: the realistic failure is a plausible
   subset, not a nonsense name.

Exit 0 iff every check passes.
"""

import difflib
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)

SRC = os.path.join("tests", "fixtures", "extract", "src")
LAUNCH = os.path.join(SRC, "probe_bringup", "launch", "probe.launch.py")
GOLDEN = os.path.join(ROOT, "tests", "fixtures", "extract", "golden")

# Relative path under the run's output dir -> relative path under golden/.
ARTEFACTS = [
    os.path.join("rosnodes", "probe_bridge.ros2"),
    os.path.join("rosnodes", "probe_pilot.ros2"),
    "probe.rossystem",
]


def run_extractors(out):
    """Both scripts, in the order the skill prescribes. Returns (ok, log)."""
    log = []
    for args in (
        [sys.executable, os.path.join("scripts", "extract_ros2_interfaces.py"), SRC,
         "-o", os.path.join(out, "rosnodes")],
        [sys.executable, os.path.join("scripts", "extract_rossystem.py"), LAUNCH,
         "--models", os.path.join(out, "rosnodes"),
         "-o", os.path.join(out, "probe.rossystem"),
         "--workspace", SRC],
    ):
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
        log.append(r.stdout + r.stderr)
        if r.returncode != 0:
            log.append("EXIT %d from %s" % (r.returncode, args[1]))
            return False, "\n".join(log)
    return True, "\n".join(log)


def normalise(text, out):
    """Strip the two things that legitimately differ between machines and runs.

    The scripts record where they read from and wrote to, by absolute path. That provenance is
    worth having in a real model and worthless in a golden, so it is replaced rather than
    removed -- a golden that dropped the lines could not tell a missing header from a moved one.
    """
    return text.replace(os.path.realpath(out), "<OUT>").replace(out, "<OUT>") \
               .replace(os.path.realpath(ROOT), "<ROOT>").replace(ROOT, "<ROOT>")


def check_golden(out, update, add):
    for rel in ARTEFACTS:
        produced = os.path.join(out, rel)
        expected = os.path.join(GOLDEN, rel)
        if not os.path.exists(produced):
            add("the extractors did not produce %s" % rel)
            continue
        got = normalise(open(produced, encoding="utf-8").read(), out)
        if update:
            os.makedirs(os.path.dirname(expected), exist_ok=True)
            with open(expected, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(got)
            print("  updated  tests/fixtures/extract/golden/%s" % rel.replace(os.sep, "/"))
            continue
        if not os.path.exists(expected):
            add("no golden for %s -- run with --update once you have READ the output" % rel)
            continue
        want = open(expected, encoding="utf-8").read()
        if got == want:
            print("  ok       %s" % rel.replace(os.sep, "/"))
            continue
        diff = "".join(difflib.unified_diff(
            want.splitlines(True), got.splitlines(True),
            fromfile="golden/" + rel.replace(os.sep, "/"), tofile="produced/" + rel.replace(os.sep, "/")))
        add("%s differs from its golden:\n%s" % (rel, diff))


def check_bug_classes(out, add):
    """The two invariants that have actually broken here, asserted by name."""
    path = os.path.join(out, "rosnodes", "probe_bridge.ros2")
    if not os.path.exists(path):
        add("cannot check the bug-class fixtures: %s was not produced" % path)
        return
    lines = open(path, encoding="utf-8").read().splitlines()

    # 1. string "false" under a declared bool renders false, not true.
    got = None
    for i, line in enumerate(lines):
        if line.strip() == "'enable_probe':":
            got = [l.strip() for l in lines[i + 1:i + 3]]
            break
    if got is None:
        add("BOOLEAN DEFAULT: parameter 'enable_probe' is missing from probe_bridge.ros2 "
            "entirely; its source declares it (probe_bridge_parameters.yaml)")
    elif "type: Boolean" not in got:
        add("BOOLEAN DEFAULT: 'enable_probe' is declared `type: bool` in the source but came "
            "out as %r" % got)
    elif "default: false" not in got:
        add("BOOLEAN DEFAULT: 'enable_probe' has default_value \"false\" (the STRING) in "
            "probe_bridge_parameters.yaml and MUST render `default: false`; got %r. A "
            "non-empty string is truthy in Python, so this is the silent inversion -- the "
            "model would assert the opposite of the source and still pass every other check."
            % got)

    # 2. a name built from literals + one identifier is flagged WITH candidates, not declared.
    flagged = [l for l in lines if l.startswith("#") and "CANDIDATES" in l]
    if len(flagged) != 2:
        add("COMPOSED TOPIC NAME: expected 2 flags carrying CANDIDATES (the publisher and the "
            "subscriber built as \"/probe/\" + side), found %d" % len(flagged))
    header = "\n".join(l for l in lines if l.startswith("#"))
    for want in ("/probe/left/state", "/probe/right/state",
                 "/probe/left/cmd", "/probe/right/cmd"):
        if want not in header:
            add("COMPOSED TOPIC NAME: the flag does not carry %s as a candidate. The two "
                "ProbeSide construction sites pass 'left' and 'right' literally, so the "
                "evidence is there to be read." % want)
        declared = "'%s':" % want
        if any(l.strip() == declared for l in lines if not l.startswith("#")):
            add("COMPOSED TOPIC NAME: %s was DECLARED, not flagged. The extractor cannot see "
                "construction sites outside the package, so emitting the visible ones claims a "
                "completeness it has no basis for -- a plausible subset turns a visible "
                "unknown into an invisible one." % want)


def main(argv):
    update = "--update" in argv[1:]
    findings = []

    def add(msg):
        findings.append(msg)

    out = tempfile.mkdtemp(prefix="extract_golden_")
    try:
        ok, log = run_extractors(out)
        if not ok:
            print(log)
            print("\nan extractor failed to run; nothing was compared")
            return 1
        check_golden(out, update, add)
        if not update:
            check_bug_classes(out, add)
    finally:
        shutil.rmtree(out, ignore_errors=True)

    for msg in findings:
        print("  FAIL     %s" % msg)
    if update:
        print("\ngolden updated -- read the diff before committing it")
        return 0
    print("\n%d artefact(s) checked, %d failure(s)" % (len(ARTEFACTS), len(findings)))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
