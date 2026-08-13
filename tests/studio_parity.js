#!/usr/bin/env node
"use strict";
/* studio_parity.js -- proves the editor's live .rossystem preview is BYTE-IDENTICAL to what
 * the Python emitter writes.
 *
 * ros_studio.py's emit_rossystem()/_exposure_labels() and the editor's genSystem()/
 * exposureLabels() are two implementations of one emission profile. The editor shows the
 * author what Commit will produce; if the two drift, the page lies about the model -- and
 * nothing else in the suite would notice, because both sides stay internally consistent and
 * both keep linting clean.
 *
 * The functions are pulled OUT OF THE RENDERED PAGE by name, not out of the template source
 * and not out of a copy kept here: a copy would go stale exactly when it matters, and the
 * thing that ships to the author is the rendered page.
 *
 *   node tests/studio_parity.js                          # whole pipeline, every examples/*.rossystem
 *   node tests/studio_parity.js FIXTURE.rossystem ...    # whole pipeline, chosen fixtures
 *   node tests/studio_parity.js --project P --html H --expect E    # diff only (pre-built inputs)
 *
 * Exit 0 iff every fixture matches. Pipeline mode drives ros_studio.py through
 * $ROSMODEL_PYTHON (falling back to `python`) into a temp dir; nothing is written into the
 * repo. studio_roundtrip.py runs the diff-only mode, reusing the files it already built.
 */

var fs = require("fs");
var os = require("os");
var path = require("path");
var cp = require("child_process");

var HERE = __dirname;
var ROOT = path.dirname(HERE);
var STUDIO = path.join(ROOT, "scripts", "ros_studio.py");

// The shipped pure functions genSystem() transitively needs, plus ifaceConnected, which the
// page uses to decide the "expose" checkbox is forced on -- the same rule _exposure_labels()
// applies when it walks the connections, so it is cross-checked here too.
//
// The second group is genRos2()'s closure. The .ros2 side is checked because `qos:` and
// `fromGitRepo:` are editable ONLY in this page and appear ONLY in that file: the author's
// single chance to see them before Commit is that preview, so it has to be the emitter's
// bytes and not an approximation of them.
var WANTED = ["qd", "qs2", "nodeById", "ifaceById", "ifaceConnected", "exposureLabels",
  "genSystem",
  "handPkgNodes", "companionPkgs", "typeComment", "pyFloat", "pyRepr", "fmtParamValue",
  "genQos", "genRos2"];


// ---------------------------------------------------------------------------------------
// extracting a function body out of the rendered page
// ---------------------------------------------------------------------------------------

function extractScript(html) {
  var open = html.indexOf("<script>");
  var close = html.lastIndexOf("<\/script>");
  if (open < 0 || close < 0 || close < open)
    throw new Error("rendered page has no <script> block");
  return html.slice(open + "<script>".length, close);
}

function skipString(src, i) {
  var quote = src[i];
  i++;
  while (i < src.length) {
    var ch = src[i];
    if (ch === "\\") { i += 2; continue; }
    if (quote === "`" && ch === "$" && src[i + 1] === "{")
      throw new Error("template-literal interpolation is not supported by this extractor");
    if (ch === quote) return i + 1;
    i++;
  }
  throw new Error("unterminated string literal");
}

function skipRegex(src, i) {
  i++;                                        // past the opening /
  var inClass = false;
  while (i < src.length) {
    var ch = src[i];
    if (ch === "\\") { i += 2; continue; }
    if (ch === "[") inClass = true;
    else if (ch === "]") inClass = false;
    else if (ch === "/" && !inClass) return i + 1;
    else if (ch === "\n") throw new Error("unterminated regex literal");
    i++;
  }
  throw new Error("unterminated regex literal");
}

// A `/` starts a regex unless the previous significant token could END an expression. The
// shipped functions carry both (/\\/g in qd, "assets/rosmodelscatalog/" in genSystem), so
// brace counting has to know the difference or it walks off the end of the function.
function regexAllowed(prev) { return !/[A-Za-z0-9_$)\].]/.test(prev); }

function sliceFunction(src, name) {
  var decl = new RegExp("function\\s+" + name + "\\s*\\(");
  var m = decl.exec(src);
  if (!m)
    throw new Error("the rendered page declares no `function " + name + "(` -- either it was "
      + "renamed or inlined; the parity check cannot test a function it cannot find");
  var open = src.indexOf("{", m.index + m[0].length);
  if (open < 0) throw new Error("no body for function " + name);
  var depth = 0, i = open, prev = "";
  while (i < src.length) {
    var ch = src[i], nx = src[i + 1];
    if (ch === "/" && nx === "/") { while (i < src.length && src[i] !== "\n") i++; continue; }
    if (ch === "/" && nx === "*") {
      i = src.indexOf("*/", i + 2);
      if (i < 0) throw new Error("unterminated block comment");
      i += 2; continue;
    }
    if (ch === '"' || ch === "'" || ch === "`") { i = skipString(src, i); prev = "0"; continue; }
    if (ch === "/" && regexAllowed(prev)) { i = skipRegex(src, i); prev = "0"; continue; }
    if (ch === "{") depth++;
    else if (ch === "}") { depth--; if (depth === 0) return src.slice(m.index, i + 1); }
    if (!/\s/.test(ch)) prev = ch;
    i++;
  }
  throw new Error("unbalanced braces in function " + name);
}

// The payload ros_studio.render_editor() substitutes for /*__DATA__*/null, on one line.
// genSystem() sorts the exposures with KINDS (= DATA.kindOrder, the emitter's ARROW_KINDS),
// so the sandbox has to hand the shipped functions the shipped constants rather than a
// hand-copied kind order that could itself drift.
function extractData(script) {
  var m = /^var DATA = (.*);$/m.exec(script);
  if (!m) throw new Error("rendered page has no `var DATA = ...;` payload");
  return JSON.parse(m[1]);
}

// Re-animate the extracted functions over the project the Python emitter saw. genSystem is
// pure apart from one DOM read (the topbar system-name input), which the page keeps in sync
// with project.system.name; any OTHER DOM touch means the function stopped being pure and
// the sandbox says so instead of silently faking it.
function loadShipped(html, project) {
  var script = extractScript(html);
  var parts = WANTED.map(function (n) { return sliceFunction(script, n); });
  var sysname = (project.system && project.system.name) || "system";
  var body =
    "var DATA = __data;\n" +
    "var KINDS = DATA.kindOrder;\n" +
    "var BLOCK = DATA.blocks;\n" +
    "var TYPEFILES = DATA.typeFiles || {};\n" +
    "var SEGBLOCK = DATA.typeSegBlocks || {};\n" +
    "var QOS = DATA.qos;\n" +
    "var QOS_DUR = {}; (QOS.durations||[]).forEach(function(k){QOS_DUR[k]=1;});\n" +
    "var project = __project;\n" +
    "project.packages = project.packages || {};\n" +   // the page normalises this on load
    "var document = { getElementById: function(id){\n" +
    "  if(id === 'sysname') return { value: __sysname };\n" +
    "  throw new Error('parity sandbox: unexpected document.getElementById(' + id + ')');\n" +
    "} };\n" +
    parts.join("\n") + "\n" +
    "return { " + WANTED.map(function (n) { return n + ": " + n; }).join(", ") + " };\n";
  return new Function("__project", "__sysname", "__data", body)(
    project, sysname, extractData(script));
}


// ---------------------------------------------------------------------------------------
// the comparison
// ---------------------------------------------------------------------------------------

function firstDiff(expected, actual) {
  var a = expected.split("\n"), b = actual.split("\n");
  for (var i = 0; i < Math.max(a.length, b.length); i++) {
    if (a[i] !== b[i]) {
      return "line " + (i + 1) + ":\n      python: " + JSON.stringify(a[i])
        + "\n      editor: " + JSON.stringify(b[i]);
    }
  }
  return null;
}

function compare(projectPath, htmlPath, expectPath) {
  var project = JSON.parse(fs.readFileSync(projectPath, "utf8"));
  var html = fs.readFileSync(htmlPath, "utf8");
  var expected = fs.readFileSync(expectPath, "utf8");
  var fns = loadShipped(html, project);
  var problems = [];

  var actual = fns.genSystem();
  if (actual !== expected) {
    var d = firstDiff(expected, actual);
    problems.push("genSystem() differs from the Python emitter at " + (d || "(trailing bytes)"));
  }

  // Every .ros2 the companion wrote next to that .rossystem, by package name. The editor
  // decides on its own which packages produce a file (hand-authored + non-empty pkg), so an
  // extra or a missing file is itself a parity failure and is reported as one.
  var outdir = path.dirname(expectPath);
  var wrote = fs.readdirSync(outdir).filter(function (f) { return /\.ros2$/.test(f); })
    .map(function (f) { return f.replace(/\.ros2$/, ""); }).sort();
  var previews = fns.handPkgNodes().order;
  if (wrote.join(",") !== previews.join(","))
    problems.push("the .ros2 file set differs: python wrote [" + wrote.join(", ")
      + "], the editor previews [" + previews.join(", ") + "]");
  wrote.forEach(function (pkg) {
    if (previews.indexOf(pkg) < 0) return;              // already reported above
    var want = fs.readFileSync(path.join(outdir, pkg + ".ros2"), "utf8");
    var got = fns.genRos2(pkg);
    if (got !== want) {
      var dd = firstDiff(want, got);
      problems.push("genRos2(" + pkg + ") differs from the Python emitter at "
        + (dd || "(trailing bytes)"));
    }
  });

  // cross-check the exposure rule itself: every connection endpoint must read as connected
  // AND must have been assigned a label, which is what makes the connections block emittable.
  var labels = fns.exposureLabels();
  (project.connections || []).forEach(function (c) {
    [c.from, c.to].forEach(function (end) {
      var n = fns.nodeById(end.n);
      var f = n && fns.ifaceById(n, end.i);
      if (!n || !f) return;                 // dangling endpoints are studio_roundtrip's business
      if (!fns.ifaceConnected(n, f))
        problems.push("ifaceConnected() says " + n.label + "/" + f.name + " is unwired, but a "
          + "connection names it");
      if (!labels[n.id + "/" + f.id])
        problems.push("exposureLabels() gave no label to connected " + n.label + "/" + f.name);
    });
  });
  return problems;
}


// ---------------------------------------------------------------------------------------
// pipeline mode: build the inputs the same way a user would
// ---------------------------------------------------------------------------------------

function python() {
  return process.env.ROSMODEL_PYTHON || "python";
}

function runStudio(args) {
  var r = cp.spawnSync(python(), [STUDIO].concat(args), { encoding: "utf8" });
  if (r.error) throw new Error("could not run " + python() + ": " + r.error.message);
  if (r.status !== 0)
    throw new Error("ros_studio.py " + args[0] + " failed (exit " + r.status + "):\n"
      + (r.stdout || "") + (r.stderr || ""));
  return r.stdout || "";
}

function generated(gen) {
  var sys = fs.readdirSync(gen).filter(function (f) { return /\.rossystem$/.test(f); });
  if (!sys.length) throw new Error("generate wrote no .rossystem");
  return path.join(gen, sys[0]);
}

function buildInputs(fixture, work) {
  var proj = path.join(work, "p.json");
  var html = path.join(work, "e.html");
  var gen = path.join(work, "gen");
  runStudio(["init", fixture, "--out", proj]);
  runStudio(["render", proj, "--out", html]);
  runStudio(["generate", proj, "--outdir", gen]);
  return { project: proj, html: html, expect: generated(gen) };
}

// A seeded project happens to arrive with each node's interfaces already in the emitter's
// (kind, name) order, so a straight round-trip cannot tell "same order" from "same sort".
// Reversing every iface list breaks that coincidence -- it is what an interface ADDED in the
// editor does to the array -- and re-emits from Python for the same comparison. Same shipped
// page, different project: these functions are pure over `project`.
function permutedCase(base, work) {
  var project = JSON.parse(fs.readFileSync(base.project, "utf8"));
  (project.nodes || []).forEach(function (n) { (n.ifaces || []).reverse(); });
  var proj = path.join(work, "p-permuted.json");
  var gen = path.join(work, "gen-permuted");
  fs.writeFileSync(proj, JSON.stringify(project, null, 2), "utf8");
  runStudio(["generate", proj, "--outdir", gen]);
  return { project: proj, html: base.html, expect: generated(gen) };
}

function main(argv) {
  var opts = {}, fixtures = [];
  for (var i = 0; i < argv.length; i++) {
    var a = argv[i];
    if (a === "--project" || a === "--html" || a === "--expect") opts[a.slice(2)] = argv[++i];
    else if (a === "-h" || a === "--help") {
      console.log("usage: node tests/studio_parity.js [FIXTURE.rossystem ...]");
      console.log("       node tests/studio_parity.js --project P --html H --expect E");
      return 0;
    } else fixtures.push(a);
  }

  var cases = [], work = null;
  if (opts.project || opts.html || opts.expect) {
    if (!(opts.project && opts.html && opts.expect)) {
      console.error("--project, --html and --expect must be given together");
      return 2;
    }
    // diff-only mode still gets the permuted case -- it costs one extra `generate` and it is
    // the half of the comparison a freshly seeded project cannot exercise (see permutedCase).
    work = fs.mkdtempSync(path.join(os.tmpdir(), "studio-parity-"));
    cases.push({ name: path.basename(opts.expect), paths: opts });
    cases.push({
      name: path.basename(opts.expect) + " [ifaces permuted]",
      paths: permutedCase(opts, work)
    });
  } else {
    if (!fixtures.length) {
      var ex = path.join(ROOT, "examples");
      fixtures = fs.readdirSync(ex).filter(function (f) { return /\.rossystem$/.test(f); })
        .sort().map(function (f) { return path.join(ex, f); });
    }
    if (!fixtures.length) { console.error("no .rossystem to test"); return 1; }
    work = fs.mkdtempSync(path.join(os.tmpdir(), "studio-parity-"));
    fixtures.forEach(function (f, k) {
      var d = path.join(work, "f" + k);
      fs.mkdirSync(d);
      var base = buildInputs(f, d);
      cases.push({ name: path.basename(f), paths: base });
      cases.push({ name: path.basename(f) + " [ifaces permuted]", paths: permutedCase(base, d) });
    });
  }

  var failures = 0;
  try {
    cases.forEach(function (c) {
      var problems;
      try {
        problems = compare(c.paths.project, c.paths.html, c.paths.expect);
      } catch (e) {
        problems = ["harness error: " + e.message];
      }
      console.log("%s %s", problems.length ? "FAIL" : "PASS", c.name);
      problems.forEach(function (p) { failures++; console.log("    " + p); });
    });
  } finally {
    if (work) try { fs.rmSync(work, { recursive: true, force: true }); } catch (e) { }
  }
  console.log("%d case(s), %d failure(s)", cases.length, failures);
  return failures ? 1 : 0;
}

// Also usable as a library, so another harness can pull functions out of a rendered page with
// THIS extractor rather than a second, subtly different copy of the brace counter.
if (require.main === module) {
  try {
    process.exit(main(process.argv.slice(2)));
  } catch (e) {
    console.error("studio_parity: " + (e && e.message ? e.message : e));
    process.exit(2);
  }
} else {
  module.exports = { extractScript: extractScript, extractData: extractData,
    sliceFunction: sliceFunction, loadShipped: loadShipped };
}
