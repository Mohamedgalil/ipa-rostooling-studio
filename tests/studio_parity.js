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
//
// The third group is the comment layer. Comments are the only model content the author writes
// as free text, so a drift here is invisible in every other check: the preview would keep
// showing the author's words while `generate` wrote a file without them, or at a different
// indent, or with the RM088/RM089 provenance overwritten.
// The fourth group is the .ros companion. Message FIELDS are authored ONLY in this page --
// nothing else in the pipeline invents one -- and a spec whose body silently comes out empty
// is legal (RM080 INFO), so a drift there produces a file that lints clean, generates clean
// and has lost the author's content. That is the exact defect shape STATUS.md sec 8 defect 2
// records, which is why the preview is held to the emitter's bytes rather than eyeballed.
// The fifth group is the "changed since the seed" tab. Its whole point is to tell an edit
// from a reformat, so a projectFacts() that disagrees with project_facts() would report edits
// the author never made -- or, far worse, stay silent about one they did. Nothing else in the
// suite compares the two: both sides are internally consistent and both keep linting clean,
// exactly as with genSystem().
var WANTED = ["qd", "qs2", "nodeById", "ifaceById", "ifaceConnected", "exposureLabels",
  "genSystem",
  "handPkgNodes", "localTypePkgs", "companionTypes", "companionPkgs", "typeAutoNote",
  "pyFloat", "pyRepr", "fmtParamValue", "genQos", "genRos2", "genRos",
  "cmtClean", "cmtList", "cmtOf", "cmtBlock", "noteSuffix",
  "factStr", "unquoteEmitted", "paramFact", "qosFact", "ifaceFactKey", "projectFacts",
  "isFactObj", "factSummary", "diffWalk", "diffFacts", "diffShow", "padTo", "formatDiff"];


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

// A page-scope `var NAME = ...;` on ONE line, taken verbatim out of the rendered page. The
// fact tree's section list and its sentinel live in such a declaration rather than in a
// function, and hand-copying them here would put the drift back in the place this harness
// exists to remove.
function sliceVar(src, name) {
  var m = new RegExp("^[ \\t]*var " + name + "\\s*=.*;[ \\t]*$", "m").exec(src);
  if (!m)
    throw new Error("the rendered page declares no one-line `var " + name + " = ...;`");
  return m[0].trim();
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
    "var ROS = DATA.ros || {blocks:[],bodies:{},scalars:[],arrays:[],nameKeywords:[]};\n" +
    "var ROSSEG = {}; Object.keys(SEGBLOCK).forEach(function(s){ROSSEG[SEGBLOCK[s]]=s;});\n" +
    "var QOS = DATA.qos;\n" +
    "var QOS_DUR = {}; (QOS.durations||[]).forEach(function(k){QOS_DUR[k]=1;});\n" +
    sliceVar(script, "FACT_SECTIONS") + "\n" +
    sliceVar(script, "FACT_MISSING") + "\n" +
    sliceVar(script, "DIFF_OP_MARK") + "\n" +
    "var project = __project;\n" +
    "project.packages = project.packages || {};\n" +   // the page normalises these on load
    "project.types = project.types || {};\n" +
    "var document = { getElementById: function(id){\n" +
    "  if(id === 'sysname') return { value: __sysname };\n" +
    "  throw new Error('parity sandbox: unexpected document.getElementById(' + id + ')');\n" +
    "} };\n" +
    parts.join("\n") + "\n" +
    "return { __DATA: DATA, "
      + WANTED.map(function (n) { return n + ": " + n; }).join(", ") + " };\n";
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

// Key order is an artefact of how each side happens to build the tree, never of the model, so
// both are re-serialised with keys sorted before they are compared.
function canonical(v) {
  if (v === null || typeof v !== "object") return JSON.stringify(v);
  if (v instanceof Array) return "[" + v.map(canonical).join(",") + "]";
  return "{" + Object.keys(v).sort().map(function (k) {
    return JSON.stringify(k) + ":" + canonical(v[k]);
  }).join(",") + "}";
}

// Name the first fact PATH the two trees disagree about; "python: ... / editor: ..." on a
// 200-line JSON blob is not a report anyone can act on.
function firstFactDiff(a, b) {
  var hit = null;
  (function walk(path, x, y) {
    if (hit) return;
    if (canonical(x) === canonical(y)) return;
    if (x && y && typeof x === "object" && typeof y === "object"
        && !(x instanceof Array) && !(y instanceof Array)) {
      var keys = {};
      Object.keys(x).forEach(function (k) { keys[k] = 1; });
      Object.keys(y).forEach(function (k) { keys[k] = 1; });
      Object.keys(keys).sort().forEach(function (k) {
        walk(path ? path + "." + k : k, x[k], y[k]);
      });
      if (hit) return;
    }
    hit = (path || "(root)") + "\n      python: " + canonical(x)
      + "\n      editor: " + canonical(y);
  })("", a, b);
  return hit || "(no leaf differs — the trees stringify differently)";
}

// `generate` also STAGES files it did not write -- a project-local subSystems: target and that
// target's own .ros2 -- so the output directory listing is no longer the set of files THIS
// project produces, and comparing the editor's preview set against it would fail on a file the
// editor is right not to preview. Take the set from generate's own report instead.
function wroteExt(stdout, ext) {
  var out = [], re = new RegExp("^wrote\\s+(.*\\." + ext + ")$");
  String(stdout).split("\n").forEach(function (line) {
    var m = re.exec(line.trim());
    if (m) out.push(path.basename(m[1]).replace(new RegExp("\\." + ext + "$"), ""));
  });
  return out.sort();
}

function compare(projectPath, htmlPath, expectPath, knownWrote) {
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
  var known = knownWrote || {};

  // Same check for the companion .ros. Its file set comes from companionTypes(), a different
  // rule from handPkgNodes() -- a package with no node at all can own one, which is how a type
  // the author invented gets written -- so it is compared separately rather than reused.
  function byExt(ext, want, gen) {
    var wrote = known[ext] || fs.readdirSync(outdir)
      .filter(function (f) { return f.slice(-ext.length - 1) === "." + ext; })
      .map(function (f) { return f.slice(0, -ext.length - 1); }).sort();
    var previews = want().slice().sort();
    if (wrote.join(",") !== previews.join(","))
      problems.push("the ." + ext + " file set differs: python wrote [" + wrote.join(", ")
        + "], the editor previews [" + previews.join(", ") + "]");
    wrote.forEach(function (pkg) {
      if (previews.indexOf(pkg) < 0) return;            // already reported above
      var expected = fs.readFileSync(path.join(outdir, pkg + "." + ext), "utf8");
      var got = gen(pkg);
      if (got !== expected) {
        var dd = firstDiff(expected, got);
        problems.push("gen" + (ext === "ros2" ? "Ros2" : "Ros") + "(" + pkg + ") differs from "
          + "the Python emitter at " + (dd || "(trailing bytes)"));
      }
    });
  }
  byExt("ros2", function () { return fns.handPkgNodes().order; }, fns.genRos2);
  byExt("ros", function () { return Object.keys(fns.companionTypes()); }, fns.genRos);

  // ---- the "changed since the seed" tab -------------------------------------------------
  // Three things are held here. (1) The editor's projectFacts() must equal the companion's
  // project_facts(). (2) The rendered text of the diff must match too, because the two are
  // read side by side -- the tab in the browser and `ros_studio.py diff` in the terminal --
  // and a column that lines up differently is a different report. (3) project_facts() must
  // agree with the files `generate` actually WRITES; `diff` computes both and says so when it
  // does not, and that note is a failure here rather than a line nobody reads.
  var pyFacts = JSON.parse(runStudio(["--facts", projectPath]));
  var jsFacts = fns.projectFacts();
  var pf = canonical(pyFacts), jf = canonical(jsFacts);
  if (pf !== jf)
    problems.push("projectFacts() differs from project_facts() at " + firstFactDiff(pyFacts, jsFacts));

  if (fns.__DATA && fns.__DATA.seedFacts) {
    // stdout on Windows arrives CRLF-terminated; the tab renders \n, and the line ENDING is
    // the console's, not the report's.
    var pyText = runStudio(["--preview-diff", projectPath])
      .replace(/\r\n/g, "\n").replace(/\n$/, "");
    var jsText = fns.formatDiff(fns.diffFacts(fns.__DATA.seedFacts, jsFacts));
    if (pyText !== jsText) {
      var dt = firstDiff(pyText, jsText);
      problems.push("the editor's seed diff differs from format_diff() at "
        + (dt || "(trailing bytes)"));
    }
    var report = JSON.parse(runStudio(["diff", projectPath, "--json"]));
    (report.notes || []).forEach(function (n) {
      if (/^project_facts\(\)/.test(n))
        problems.push("project_facts() does not describe what generate wrote: " + n);
    });
  }

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

function generated(gen, fixture) {
  var sys = fs.readdirSync(gen).filter(function (f) { return /\.rossystem$/.test(f); }).sort();
  if (!sys.length) throw new Error("generate wrote no .rossystem");
  // `generate` copies a project-local subSystems: target into the output dir UNCHANGED, so gen
  // can hold more than one .rossystem and readdir order decided which one counted as "what
  // Python wrote". Comparing the editor's preview of THIS project against a staged dependency
  // reports a diff on line 1 of a file neither side is wrong about. Prefer the fixture's name.
  var want = fixture ? path.basename(fixture) : null;
  if (want && sys.indexOf(want) !== -1) return path.join(gen, want);
  return path.join(gen, sys[0]);
}

function buildInputs(fixture, work) {
  var proj = path.join(work, "p.json");
  var html = path.join(work, "e.html");
  var gen = path.join(work, "gen");
  runStudio(["init", fixture, "--out", proj]);
  runStudio(["render", proj, "--out", html]);
  var out = runStudio(["generate", proj, "--outdir", gen]);
  return { project: proj, html: html, expect: generated(gen, fixture), fixture: fixture,
           wrote: { ros2: wroteExt(out, "ros2"), ros: wroteExt(out, "ros") } };
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
  var out = runStudio(["generate", proj, "--outdir", gen]);
  return { project: proj, html: base.html, expect: generated(gen, base.fixture),
           wrote: { ros2: wroteExt(out, "ros2"), ros: wroteExt(out, "ros") } };
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
    // The caller already resolved which .rossystem is THIS project's (its outdir can also hold
    // a staged subSystems: dependency), so carry that name into the permuted regeneration --
    // otherwise generated() falls back to readdir order and compares against the dependency.
    opts.fixture = opts.expect;
    var perm = permutedCase(opts, work);
    // the caller built the primary outdir, so its "wrote" report is not ours to read. The
    // permuted run produces the same package set (only iface ARRAYS were reversed), so its
    // report is the authority for both -- and it excludes the staged files either way.
    opts.wrote = perm.wrote;
    cases.push({ name: path.basename(opts.expect), paths: opts });
    cases.push({ name: path.basename(opts.expect) + " [ifaces permuted]", paths: perm });
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
        problems = compare(c.paths.project, c.paths.html, c.paths.expect, c.paths.wrote);
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
