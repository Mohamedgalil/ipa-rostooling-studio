#!/usr/bin/env python3
"""
ask_oracle.py — feed model files to the REAL RosTooling language server and report what it says.

Everything else in this plugin validates against our own reimplementation of RosTooling's rules.
This script asks the actual toolchain. It is the only component here that does.

Usage:
    py ask_oracle.py <case-dir> [<case-dir> ...]
    py ask_oracle.py --all            # every directory under cases/

Each case directory is opened as its own LSP workspace root so cases cannot interfere
(two files declaring the same package would otherwise cross-contaminate).

Requires Java 19+. Temurin 21 lives outside PATH on this machine, so JAVA is pinned below.
"""

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parent.parent
CODE = PLUGIN.parent / "material" / "code"

JAVA = Path(
    os.environ.get(
        "ROSMODEL_JAVA",
        r"C:\Users\mae\AppData\Local\Programs\Eclipse Adoptium\jdk-21.0.11.10-hotspot\bin\java.exe",
    )
)
# ── language server jars ──────────────────────────────────────────────────────
#
# CURRENT (default). Built from ipa-esa/RosTooling @ esa/main (3.1.0-SNAPSHOT), commit
# 5b7d897. Serves .ros, .ros2 and .rossystem from one process — its ISetup registry lists
# Basics/Ros/Ros2/RosSystem plus the xbase setups. See rostooling-plugin/build/README.md.
#
# This replaced the two jars below as the oracle because the shipped 2024 jar predates the
# Oct-2025 grammar: it cannot parse the QoS fields lease_duration/liveliness/lifespan/
# deadline, which made those look like emission-profile violations when they are valid.
JAR_CURRENT = PLUGIN / "build" / "ros2-ls" / "target" / \
    "de.fraunhofer.ipa.rostooling.ls-3.1.0-SNAPSHOT-ls.jar"

# LEGACY, kept selectable for A/B comparison and as a fallback. Read-only reference clone.
JAR_LEGACY_ROS2 = CODE / "vscode-RosTooling" / "resources" / \
    "de.fraunhofer.ipa.ros2.xtext.ide-3.0.0-SNAPSHOT-ls.jar"

# LEGACY rossystem server: the 2024 fat jar with only rossystem recompiled on top, so its
# ros/ros2 grammar is equally stale. Superseded by JAR_CURRENT.
JAR_LEGACY_ROSSYSTEM = PLUGIN / "build" / "rossystem-ls" / "target" / \
    "de.fraunhofer.ipa.rossystem.xtext.ide-3.0.0-SNAPSHOT-ls.jar"

# ROSMODEL_ORACLE selects which server to use:
#   current (default) | legacy   — 'legacy' restores the pre-rebuild behaviour exactly
#                                  (old ros2 jar for .ros/.ros2, old rossystem jar for
#                                  .rossystem), for A/B-ing a diagnostic.
# ROSMODEL_JAR overrides with an explicit path and wins over ROSMODEL_ORACLE.
ORACLE_MODE = os.environ.get("ROSMODEL_ORACLE", "current").strip().lower()
JAR_OVERRIDE = os.environ.get("ROSMODEL_JAR", "").strip()

LAUNCHER = "org.eclipse.xtext.ide.server.ServerLauncher"

# Model files we feed the server, in the order we open them. Order matters: a .rossystem
# resolves `from:` and arrow targets into .ros/.ros2, so those must be loaded first.
# NOTE: .ros1 is deliberately absent — no Ros1IdeSetup is registered in any of these jars,
# so .ros1 files cannot be served. See build/README.md.
MODEL_GLOBS = ("*.ros", "*.ros2", "*.rossystem")


def jar_for(files) -> Path:
    """Pick the language server for a case directory."""
    if JAR_OVERRIDE:
        return Path(JAR_OVERRIDE)
    if ORACLE_MODE == "legacy":
        if any(f.suffix == ".rossystem" for f in files):
            return JAR_LEGACY_ROSSYSTEM
        return JAR_LEGACY_ROS2
    # 'current' serves every supported extension from a single jar.
    return JAR_CURRENT

SEVERITY = {1: "ERROR", 2: "WARNING", 3: "INFO", 4: "HINT"}


# ── LSP plumbing ──────────────────────────────────────────────────────────────

class Server:
    def __init__(self, root: Path, jar: Path = None, verbose=False):
        self.root = root
        self.verbose = verbose
        self.jar = jar or JAR_CURRENT
        self.proc = subprocess.Popen(
            [str(JAVA), "-cp", str(self.jar), LAUNCHER],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.inbox = queue.Queue()
        self.stderr_lines = []
        self._next_id = 0
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_stdout(self):
        f = self.proc.stdout
        while True:
            header, length = b"", None
            while True:
                line = f.readline()
                if not line:
                    self.inbox.put(None)
                    return
                if line in (b"\r\n", b"\n"):
                    break
                header += line
                low = line.lower()
                if low.startswith(b"content-length:"):
                    length = int(line.split(b":")[1].strip())
            if length is None:
                continue
            body = b""
            while len(body) < length:
                chunk = f.read(length - len(body))
                if not chunk:
                    self.inbox.put(None)
                    return
                body += chunk
            try:
                self.inbox.put(json.loads(body.decode("utf-8")))
            except Exception as exc:  # malformed frame — surface, don't die
                self.inbox.put({"__parse_error__": str(exc), "raw": body[:400].decode("utf-8", "replace")})

    def _read_stderr(self):
        for line in iter(self.proc.stderr.readline, b""):
            s = line.decode("utf-8", "replace").rstrip()
            self.stderr_lines.append(s)
            if self.verbose:
                print(f"    [stderr] {s}", file=sys.stderr)

    def _send(self, payload):
        raw = json.dumps(payload).encode("utf-8")
        self.proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(raw) + raw)
        self.proc.stdin.flush()

    def request(self, method, params):
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params})
        return self._next_id

    def notify(self, method, params):
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def drain(self, seconds, until_uri=None):
        """Collect messages for `seconds`. Stop early once diagnostics for until_uri arrive."""
        msgs, deadline = [], time.time() + seconds
        while time.time() < deadline:
            try:
                m = self.inbox.get(timeout=0.2)
            except queue.Empty:
                continue
            if m is None:
                break
            msgs.append(m)
            if until_uri and m.get("method") == "textDocument/publishDiagnostics":
                if m.get("params", {}).get("uri", "").lower() == until_uri.lower():
                    deadline = min(deadline, time.time() + 1.0)  # brief grace for follow-ups
        return msgs

    def close(self):
        try:
            self.request("shutdown", {})
            time.sleep(0.3)
            self.notify("exit", {})
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def uri_of(p: Path) -> str:
    return p.resolve().as_uri()


# ── one case ──────────────────────────────────────────────────────────────────

def run_case(case_dir: Path, verbose=False):
    files = []
    for g in MODEL_GLOBS:                 # glob order == open order (deps before dependents)
        files.extend(sorted(case_dir.glob(g)))
    if not files:
        return {"case": case_dir.name, "status": "NO_FILES", "diagnostics": []}

    jar = jar_for(files)
    if not jar.exists():
        return {"case": case_dir.name, "status": f"MISSING_JAR: {jar}", "diagnostics": []}

    srv = Server(case_dir, jar=jar, verbose=verbose)
    result = {"case": case_dir.name, "jar": jar.name,
              "files": [f.name for f in files], "diagnostics": [], "status": "OK"}

    try:
        srv.request("initialize", {
            "processId": os.getpid(),
            "rootUri": uri_of(case_dir),
            "workspaceFolders": [{"uri": uri_of(case_dir), "name": case_dir.name}],
            "capabilities": {"textDocument": {"publishDiagnostics": {"relatedInformation": True}}},
        })
        init = srv.drain(45)
        if not any("result" in m for m in init if isinstance(m, dict)):
            result["status"] = "NO_INITIALIZE_RESPONSE"
            result["stderr"] = srv.stderr_lines[-25:]
            return result
        srv.notify("initialized", {})
        srv.drain(3)

        for f in files:
            uri = uri_of(f)
            srv.notify("textDocument/didOpen", {
                "textDocument": {
                    "uri": uri,
                    "languageId": f.suffix.lstrip("."),
                    "version": 1,
                    "text": f.read_text(encoding="utf-8"),
                }
            })
            for m in srv.drain(25, until_uri=uri):
                if m.get("method") == "textDocument/publishDiagnostics":
                    p = m["params"]
                    for d in p.get("diagnostics", []):
                        result["diagnostics"].append({
                            "file": Path(p["uri"].replace("file:///", "")).name,
                            "line": d["range"]["start"]["line"] + 1,
                            "severity": SEVERITY.get(d.get("severity", 1), "?"),
                            "message": d.get("message", "").strip(),
                        })
    finally:
        srv.close()

    if srv.stderr_lines:
        result["stderr"] = srv.stderr_lines[-25:]
    return result


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    if not JAVA.exists():
        print(f"FATAL: java not found at {JAVA}\n  set ROSMODEL_JAVA to override", file=sys.stderr)
        return 2
    if JAR_OVERRIDE:
        print(f"oracle ROSMODEL_JAR override -> {JAR_OVERRIDE}", file=sys.stderr)
    elif ORACLE_MODE == "legacy":
        for j in (JAR_LEGACY_ROS2, JAR_LEGACY_ROSSYSTEM):
            if not j.exists():
                print(f"FATAL: legacy jar not found at {j}", file=sys.stderr)
                return 2
        print("oracle mode: LEGACY (stale 2024 grammar — QoS fields will not parse)",
              file=sys.stderr)
    elif not JAR_CURRENT.exists():
        print(f"FATAL: current language server jar not found at {JAR_CURRENT}\n"
              f"  build it per rostooling-plugin/build/README.md, or set "
              f"ROSMODEL_ORACLE=legacy to fall back", file=sys.stderr)
        return 2

    if "--all" in sys.argv or not args:
        dirs = sorted(d for d in (HERE / "cases").iterdir() if d.is_dir())
    else:
        dirs = [Path(a).resolve() for a in args]

    print(f"java   {JAVA}")
    print(f"cases  {len(dirs)}   (jar chosen per case by file extension)\n")

    results = []
    for d in dirs:
        print(f"== {d.name} " + "=" * max(0, 56 - len(d.name)))
        r = run_case(d, verbose=verbose)
        results.append(r)

        if r["status"] != "OK":
            print(f"   STATUS: {r['status']}")
            for line in r.get("stderr", [])[-12:]:
                print(f"   | {line}")
            print()
            continue

        errs = [d_ for d_ in r["diagnostics"] if d_["severity"] == "ERROR"]
        warns = [d_ for d_ in r["diagnostics"] if d_["severity"] == "WARNING"]
        verdict = "REJECTED" if errs else "ACCEPTED"
        print(f"   {verdict}  —  {len(errs)} error(s), {len(warns)} warning(s)   [{r.get('jar','?')}]")
        for d_ in r["diagnostics"][:14]:
            print(f"     {d_['severity']:<8} line {d_['line']:<4} {d_['message'][:100]}")
        if len(r["diagnostics"]) > 14:
            print(f"     ... {len(r['diagnostics']) - 14} more")
        print()

    out = HERE / "results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"full results: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
