#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""oracle_gate.py -- what `generate` does when the real language server CANNOT run.

The oracle is ON by default (scripts/ros_studio.py, cmd_generate) because rosmodel_lint's RM
rules are a deliberate approximation of the Xtext validator and cannot catch everything it
would. That makes "the oracle could not run" a state every user can reach -- no JDK, an old
JDK, an unbuilt jar -- and the defect this file pins is that the state used to be QUIET:

  * --oracle was opt-in, so a default `generate` never consulted the real server and said
    nothing about not having done so. A clean run printed "0 error(s)" and exited 0.
  * run_oracle() never checked the subprocess return code, and decided the verdict with
    `"ACCEPTED" in out and "REJECTED" not in out` over stdout+stderr -- a text search over a
    stream that also carries diagnostic messages.
  * ask_oracle.py exits 0 even when every case failed to run, because NO_INITIALIZE_RESPONSE
    and MISSING_JAR are per-case statuses. A server that never answered was indistinguishable
    from a model with nothing wrong with it.

None of that needs a working jar to test -- it needs a BROKEN one, which is reproducible
anywhere by pointing ROSMODEL_JAVA at a path that does not exist. That is what this does, so
the failure path is covered on machines that could never run the oracle at all (including the
Linux sandbox this was written on, which has only Java 11 for a jar built with Java 21).

  python3 tests/oracle_gate.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STUDIO = os.path.join(ROOT, "scripts", "ros_studio.py")
ASK = os.path.join(HERE, "oracle", "ask_oracle.py")
FIXTURE = os.path.join(HERE, "fixtures", "params", "param_probe.rossystem")
NO_JAVA = os.path.join(os.sep, "does", "not", "exist", "java")


def run(args, env_extra=None):
    env = dict(os.environ)
    env.pop("ROSMODEL_JAVA", None)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True, text=True,
                          env=env, timeout=600)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main():
    failures = []

    def check(name, cond, detail=""):
        print("%-4s %s" % ("PASS" if cond else "FAIL", name))
        if not cond:
            failures.append(name + ((" -- " + detail) if detail else ""))

    work = tempfile.mkdtemp(prefix="oracle-gate-")
    try:
        proj = os.path.join(work, "p.json")
        code, out = run([STUDIO, "init", FIXTURE, "--out", proj])
        if code != 0:
            print("could not seed the fixture:\n" + out)
            return 1

        broken = {"ROSMODEL_JAVA": NO_JAVA}

        # ---- 1. the preflight names the problem, and does not merely fail ------------------
        code, out = run([ASK, "--preflight"], broken)
        check("preflight exits non-zero when java is missing", code != 0, "exit %d" % code)
        check("preflight names the path it looked at", NO_JAVA in out, out.strip()[:200])
        check("preflight says how to fix it", "ROSMODEL_JAVA" in out, out.strip()[:200])

        # ---- 2. default generate: degrades LOUDLY, but still succeeds ----------------------
        # The files were written and the lint passed; an absent JDK is not a failed generation.
        # But it must not be silent, and it must not claim to have validated anything.
        code, out = run([STUDIO, "generate", proj, "--outdir", os.path.join(work, "g1")], broken)
        check("default generate still exits 0 when the oracle cannot run", code == 0,
              "exit %d" % code)
        check("default generate says the oracle did NOT run", "NOT RUN" in out, out[-400:])
        check("default generate says lint alone is not enough",
              "cannot catch everything" in out, out[-400:])
        notice = os.path.splitext(proj)[0] + ".notice.html"
        check("a notice page is written for the studio to show", os.path.isfile(notice))
        if os.path.isfile(notice):
            html = open(notice, encoding="utf-8").read()
            check("the notice page carries the reason in its banner",
                  "Real-server validation did NOT run" in html)
            check("the notice page is titled as incomplete, NOT as a failed generation",
                  '"bannerTitle": "Validation incomplete"' in html
                  and '"bannerSev": "warn"' in html)
        # ...and it is NOT written to <project>.error.html, which belongs to a real failure and
        # would otherwise be overwritten by a run that generated perfectly well.
        check("a clean-but-unvalidated run does not write .error.html",
              not os.path.isfile(os.path.splitext(proj)[0] + ".error.html"))

        # ---- 3. --oracle means "I require it": not running it is an ERROR ------------------
        code, out = run([STUDIO, "generate", proj, "--outdir", os.path.join(work, "g2"),
                         "--oracle"], broken)
        check("--oracle exits non-zero when the oracle cannot run", code != 0, "exit %d" % code)
        check("--oracle explains that it was requested and could not run",
              "--oracle was requested" in out, out[-400:])

        # ---- 4. --no-oracle is the deliberate opt-out, and is quiet ------------------------
        # Clear the notice step 2 left behind, or "no notice was written" would be answered by
        # the previous run's file rather than by this one.
        if os.path.isfile(notice):
            os.remove(notice)
        code, out = run([STUDIO, "generate", proj, "--outdir", os.path.join(work, "g3"),
                         "--no-oracle"], broken)
        check("--no-oracle exits 0", code == 0, "exit %d" % code)
        # Matched on the SECTION HEADER, not on the bare word "oracle": the output is full of
        # paths, and this test's own temp directory is called oracle-gate-XXXX, which a naive
        # substring check happily mistakes for the tool talking about the oracle.
        check("--no-oracle prints no oracle section",
              "--- oracle" not in out and "NOT RUN" not in out, out[-300:])
        check("--no-oracle writes no notice page",
              not os.path.isfile(os.path.splitext(proj)[0] + ".notice.html"))

        # ---- 4b. a JVM that starts but never answers is caught, and only ONE case is judged --
        # A stub `java` that reports 21 and then exits passes the preflight and gets as far as
        # actually launching the server, so this exercises the RUNTIME detection rather than the
        # preflight: ask_oracle returns exit 0 with a per-case NO_INITIALIZE_RESPONSE, and the
        # old substring verdict had no way to tell that from a clean model.
        #
        # It also pins an argument-passing bug found by running this: ask_oracle.main() collects
        # case directories as `[a for a in sys.argv[1:] if not a.startswith("-")]`, so passing
        # `--results PATH` as two tokens hands it the PATH as a second case, which it reports as
        # NO_FILES. Hence `--results=PATH`, and hence this assertion on the case COUNT.
        stub = os.path.join(work, "fakejava")
        with open(stub, "w", encoding="utf-8") as handle:
            handle.write('#!/bin/sh\necho \'openjdk version "21.0.11" 2024-04-16\' >&2\n')
        os.chmod(stub, 0o755)
        if os.name != "nt":
            code, out = run([STUDIO, "generate", proj, "--outdir", os.path.join(work, "g5")],
                            {"ROSMODEL_JAVA": stub})
            # The stub exits immediately, so which failure lands is a RACE: ask_oracle either
            # times out waiting for initialize (per-case NO_INITIALIZE_RESPONSE, its own exit 0)
            # or dies writing to the closed pipe (BrokenPipeError, exit 1). Both used to be read
            # as a pass -- the first because a per-case status is not an exit code, the second
            # because the return code was never checked. Asserting on the invariant that covers
            # both, rather than on whichever one wins today.
            check("a server that never answers never yields a clean verdict", code != 0,
                  "exit %d" % code)
            check("and it says specifically what went wrong",
                  ("could not validate" in out) or ("oracle process exited" in out), out[-300:])
            # A crash returns no diagnostics; blaming the MODEL for that would be the same
            # misreport in a new place.
            check("a non-answering server is not reported as REJECTING the model",
                  "rejected this model" not in out, out[-300:])
            # The --results value must not be swept up as a second case directory.
            check("only the real case is judged, not the --results path too",
                  "NO_FILES" not in out
                  and "could not validate 2 case(s)" not in out, out[-300:])

        # ---- 5. the checked-in regression record is never collateral damage ----------------
        # ask_oracle.py defaults its results to tests/oracle/results.json, which is the 19-case
        # verdict record committed to this repo. run_oracle now passes --results into the output
        # directory; without that, every `generate --oracle` would overwrite it with one case.
        results = os.path.join(HERE, "oracle", "results.json")
        if os.path.isfile(results) and os.name != "nt":
            before = open(results, "rb").read()
            # Under the STUB java, not the broken one. With ROSMODEL_JAVA pointing at a path that
            # does not exist the run stops at oracle_preflight() and never reaches run_oracle(),
            # so ask_oracle.py and _results_path() never execute and the file is trivially
            # unchanged -- a check that passes for the wrong reason and pins nothing. The stub
            # passes the preflight, so the results file really is written, into the output
            # directory, which is the property under test.
            _code4, out4 = run([STUDIO, "generate", proj, "--outdir",
                                os.path.join(work, "g4"), "--oracle"],
                               {"ROSMODEL_JAVA": stub})
            check("generate --oracle does not overwrite tests/oracle/results.json",
                  open(results, "rb").read() == before)
            # Subject to the SAME race the block above documents: the stub exits at once, so
            # ask_oracle.py either times out on initialize and writes a results file, or dies
            # writing to the closed pipe and never gets to write one at all. Asserting only the
            # first outcome made this check fail on about three runs in four -- on an unmodified
            # tree, so it read as "your change broke the oracle" to anyone running the suite.
            # The property under test is where the results go, not whether the stub survived
            # long enough to produce any; a run that wrote none still satisfies it, and the
            # check above is what proves the checked-in record was not the file written.
            check("it writes its results into the output directory instead",
                  os.path.isfile(os.path.join(work, "g4", "oracle_results.json"))
                  or "oracle process exited" in out4,
                  out4[-300:])
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print("\n%d check(s) failed" % len(failures))
    for f in failures:
        print("  " + f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
