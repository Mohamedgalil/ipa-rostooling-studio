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
// The sixth group is the in-page LOADER. It re-seeds a project from raw .rossystem/.ros2/.ros
// text, which is a second implementation of ros_studio.seed_from_rossystem -- the exact shape
// that has silently truncated this project's models three times. The SEED cases below hold it
// to the Python seeder's own output, fact for fact, on every checked-in fixture.
var WANTED = ["splitLines", "indentOf", "splitComment", "cleanNote", "unq", "cmtSet",
  "parseRos2", "parseRos", "parseRossystem", "mergeParams", "seedFromFiles",
  "qd", "qs2", "nodeById", "ifaceById", "ifaceConnected", "exposureLabels",
  "subState", "genSystem", "generatedFiles",
  "handPkgNodes", "foldArtifacts", "localTypePkgs", "companionTypes", "companionPkgs",
  "typeAutoNote",
  "pyFloat", "pyRepr", "fmtParamValue", "inferPtype", "artParamDecl", "sysParamFact",
  "genQos", "genRos2", "genRos",
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
    // the loader resolves catalogue-backed nodes against the same two embedded datasets the
    // page uses, so the sandbox has to hand it the real ones rather than empty stand-ins --
    // otherwise a seed of a catalogue-backed fixture would "match" only because both sides
    // resolved nothing.
    "var CATALOGUE = DATA.catalogue || {};\n" +
    "var CATTYPES = DATA.catalogueTypes || {};\n" +
    "var SYSTEMS = DATA.systems || {};\n" +
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

// Seed the SAME source files in the page's own loader and compare the resulting fact tree with
// the one ros_studio.py produced from them. Facts, not bytes: ids and canvas coordinates are
// allowed to differ (they are per-run), everything the model MEANS is not.
// Every comment either project carries, keyed by the element it annotates rather than by
// position, so the two can be compared without depending on ids or ordering.
function commentIndex(project) {
  var out = {};
  function take(where, obj) {
    var c = obj && obj.comments;
    if (!c) return;
    Object.keys(c).forEach(function (slot) {
      var v = c[slot];
      if (v == null || v === "" || (Array.isArray(v) && !v.length)) return;
      out[where + "|" + slot] = Array.isArray(v) ? v.join(" ⏎ ") : String(v);
    });
  }
  take("system", project);
  take("system", (project.system || {}));
  (project.subSystems || []).forEach(function (s) { take("subSystems/" + s.ref, s); });
  (project.nodes || []).forEach(function (n) {
    take("node/" + n.label, n);
    (n.ifaces || []).forEach(function (f) {
      take("node/" + n.label + "/iface/" + f.kind + " " + f.name, f);
    });
    (n.params || []).forEach(function (p) {
      take("node/" + n.label + "/param/" + p.name, p);
    });
  });
  // a connection is identified by the labels of its endpoints, which is what a reader sees
  (project.connections || []).forEach(function (c) {
    function endp(e) {
      var n = (project.nodes || []).filter(function (x) { return x.id === e.n; })[0];
      var f = n && (n.ifaces || []).filter(function (x) { return x.id === e.i; })[0];
      return f ? (f.label || f.name) : "?";
    }
    take("conn/" + endp(c.from) + "->" + endp(c.to), c);
  });
  Object.keys(project.packages || {}).forEach(function (p) {
    take("package/" + p, project.packages[p]);
  });
  return out;
}

function compareComments(pyProject, jsProject) {
  var want = commentIndex(pyProject), got = commentIndex(jsProject), problems = [];
  Object.keys(want).sort().forEach(function (k) {
    if (!(k in got)) problems.push("in-page seed LOST the comment at " + k + ": " + JSON.stringify(want[k]));
    else if (got[k] !== want[k])
      problems.push("in-page seed changed the comment at " + k + ": python "
        + JSON.stringify(want[k]) + " vs loader " + JSON.stringify(got[k]));
  });
  Object.keys(got).sort().forEach(function (k) {
    if (!(k in want)) problems.push("in-page seed INVENTED a comment at " + k + ": " + JSON.stringify(got[k]));
  });
  return problems.slice(0, 6);
}

function compareSeed(fixture, projectPath, htmlPath) {
  var project = JSON.parse(fs.readFileSync(projectPath, "utf8"));
  var html = fs.readFileSync(htmlPath, "utf8");
  var fns = loadShipped(html, project);
  // The same file set `init` opens: the fixture's own directory plus one level of
  // subdirectories (ros_studio.SEED_GLOBS covers rosnodes/, nodes/ and */). A user selecting
  // "the model and its artifacts" in the file dialog picks exactly these; handing the loader
  // less would test it against an easier problem than the one it is compared to.
  var dir = path.dirname(fixture);
  var files = [];
  function collect(d, prefix) {
    fs.readdirSync(d).forEach(function (f) {
      var full = path.join(d, f);
      if (fs.statSync(full).isDirectory()) {
        if (!prefix) collect(full, f + "/");
        return;
      }
      if (!/\.(rossystem|ros2|ros)$/.test(f)) return;
      files.push({ name: f, text: fs.readFileSync(full, "utf8") });
    });
  }
  collect(dir, "");
  files.sort(function (a, b) { return a.name < b.name ? -1 : (a.name > b.name ? 1 : 0); });
  // the fixture itself must be the FIRST .rossystem, since that is the one Python seeded
  files.sort(function (a, b) {
    var af = a.name === path.basename(fixture) ? 0 : 1;
    var bf = b.name === path.basename(fixture) ? 0 : 1;
    return af - bf || (a.name < b.name ? -1 : 1);
  });

  var res = fns.seedFromFiles(files);
  if (res.error) return ["the in-page loader refused the fixture: " + res.error];

  var problems = [];
  var want = fns.projectFacts(project);
  var got = fns.projectFacts(res.project);
  // projectFacts() is a MODEL fact tree and carries no comments -- by design, so the seed-diff
  // tab can tell an edit from a reformat. A loader that dropped every comment would therefore
  // pass the comparison below and lose the author's words on the next Commit, which is the
  // defect 1b837a2 exists to prevent. Compare them separately.
  var cmtProblems = compareComments(project, res.project);
  if (cmtProblems.length) return cmtProblems;

  var NL = String.fromCharCode(10);
  var wantJ = JSON.stringify(want, null, 1).split(NL);
  var gotJ = JSON.stringify(got, null, 1).split(NL);
  for (var i = 0; i < Math.max(wantJ.length, gotJ.length); i++) {
    if (wantJ[i] !== gotJ[i]) {
      problems.push("in-page seed differs from `init` at fact line " + (i + 1) + ":" + NL
        + "      python: " + JSON.stringify(wantJ[i] || "(end)") + NL
        + "      loader: " + JSON.stringify(gotJ[i] || "(end)"));
      break;
    }
  }
  return problems;
}

// Every subsystem VIEW state must emit identical bytes. The state lives in project.view and
// nothing in the emitter reads it -- but "nothing reads it" is exactly the kind of claim that
// stops being true one refactor later, and a view that quietly changed the model would be
// invisible: both the preview and the file would agree, and both would lint clean. So the
// property is asserted rather than argued.
//
// It matters more than it looks: a collapsed subsystem HIDES its member nodes from the canvas,
// and `emit_rossystem` deliberately skips those same nodes for an unrelated reason (RM090). Two
// independent reasons to skip the same nodes is precisely where a "while I am here" edit lands.
function compareViewStates(projectPath, htmlPath, expectPath) {
  var project = JSON.parse(fs.readFileSync(projectPath, "utf8"));
  var html = fs.readFileSync(htmlPath, "utf8");
  var expected = fs.readFileSync(expectPath, "utf8");
  var refs = (project.subSystems || []).map(function (s) { return s.ref; });
  var problems = [];

  // project["view"] stopped being "the subsystem states" and became THE WHOLE VISUALIZATION --
  // subsystem and package box positions, the abstraction level, edit/view mode, the kind filter,
  // auto sides, the camera. Every one of those is a new key on a structure the emitter is
  // handed, and the invariant they all have to satisfy is the same one the states below satisfy:
  // no view can change an emitted byte.
  //
  // This runs for EVERY fixture, not just the ones with a subSystems: block, because these keys
  // exist regardless of whether anything is collapsible -- the early return below used to skip
  // the whole check for a plain project, which is most of them.
  //
  // Populated with deliberately NON-default values: a level that is not the default 3, view mode
  // rather than edit, a filter hiding two kinds (the one that hides content), autoSides on, a
  // camera nowhere near the origin, and positions for boxes that may not even exist here. If any
  // of it reached the emitter -- or the fact tree behind `diff` -- this fails.
  var fullView = {
    subPos: { "some_ref": { x: 917, y: 431 }, "another": { x: 12, y: 88 } },
    pkgPos: { "some_pkg": { x: 640, y: 205 } },
    level: 1, mode: "view", autoSides: true,
    hiddenKinds: ["pub", "sc", "param"],
    camera: { k: 2.5, tx: -1180, ty: 640 }
  };
  [["populated view keys", fullView],
   ["view keys on top of framed subsystems",
    (function () {
      var v = JSON.parse(JSON.stringify(fullView));
      v.subsystems = {};
      refs.forEach(function (r) { v.subsystems[r] = "framed"; });
      return v;
    })()]].forEach(function (st) {
    var copy = JSON.parse(JSON.stringify(project));
    copy.view = st[1];
    var fns = loadShipped(html, copy);
    if (fns.genSystem() !== expected) {
      var d = firstDiff(expected, fns.genSystem());
      problems.push(st[0] + " CHANGED the emitted .rossystem at " + (d || "(trailing bytes)")
        + " -- the whole visualization lives under project.view and none of it may reach a byte");
    }
    var f = fns.projectFacts();
    if ("view" in f) problems.push(st[0] + ": projectFacts() carries `view` -- the arrangement "
      + "must stay out of the fact tree, or saving a layout reports as a model change");
    Object.keys(fullView).forEach(function (k) {
      if (k in f) problems.push(st[0] + ": projectFacts() carries view key `" + k + "`");
    });
  });

  // ---- provenance is not content ----------------------------------------------------------
  // `n.srcSystem` -- which source .rossystem a node was merged or imported from -- is a NEW node
  // key, and a node key is a far more dangerous place to add something than project.view: the
  // emitter walks nodes, and both fact trees describe them. It is excluded by construction
  // (emit_rossystem/emit_ros2 write named keys, project_facts builds from an allow-list), which
  // is exactly the kind of "nothing reads it" claim that stops being true one refactor later.
  //
  // Stamped on EVERY node here, including catalogue- and subsystem-backed ones, with a value
  // that would be unmistakable in the output if it ever leaked.
  var provenance = JSON.parse(JSON.stringify(project));
  provenance.nodes.forEach(function (n, i) { n.srcSystem = "ORIGIN_LEAK_" + i; });
  var pfns = loadShipped(html, provenance);
  if (pfns.genSystem() !== expected) {
    var dp = firstDiff(expected, pfns.genSystem());
    problems.push("n.srcSystem CHANGED the emitted .rossystem at " + (dp || "(trailing bytes)")
      + " -- provenance is a fact about where a node came from, never content");
  }
  if (JSON.stringify(pfns.projectFacts()).indexOf("ORIGIN_LEAK_") !== -1)
    problems.push("n.srcSystem reached projectFacts() -- re-seeding a merged project would then "
      + "report every node as changed");

  // ...and the SAME claim on the Python side, which is a separate implementation and therefore a
  // separate opportunity to read a view key. `diff` reduces both sides to project_facts(); if a
  // saved arrangement leaked in there, `diff` would report "you changed the model" for a project
  // whose only change was that someone dragged a box. project_facts() excludes `view` by
  // building from an allow-list rather than by deleting keys, so this is a regression pin on
  // that construction, not a restatement of it.
  var vp = projectPath.replace(/\.json$/, "") + ".viewkeys.json";
  var withView = JSON.parse(JSON.stringify(project));
  withView.view = fullView;
  withView.nodes.forEach(function (n, i) { n.srcSystem = "ORIGIN_LEAK_" + i; });
  fs.writeFileSync(vp, JSON.stringify(withView, null, 2));
  try {
    var factsPlain = canonical(JSON.parse(runStudio(["--facts", projectPath])));
    var factsView = canonical(JSON.parse(runStudio(["--facts", vp])));
    if (factsPlain !== factsView)
      problems.push("project_facts() CHANGED when project.view was populated and every node was "
        + "given a srcSystem -- the Python fact tree is reading the arrangement or the "
        + "provenance, so `diff` would report a drag, or a merge, as a model edit");
  } finally {
    try { fs.unlinkSync(vp); } catch (e) { }
  }

  if (!refs.length) return problems;            // nothing to collapse; not a failure

  var states = [
    ["all collapsed", "collapsed"],
    ["all framed", "framed"],
    ["absent (older project.json)", null]
  ];
  states.forEach(function (st) {
    var copy = JSON.parse(JSON.stringify(project));
    if (st[1] === null) {
      delete copy.view;
    } else {
      copy.view = { subsystems: {} };
      refs.forEach(function (r) { copy.view.subsystems[r] = st[1]; });
    }
    var fns = loadShipped(html, copy);
    var got = fns.genSystem();
    if (got !== expected) {
      var d = firstDiff(expected, got);
      problems.push("subsystem view state " + st[0] + " CHANGED the emitted .rossystem at "
        + (d || "(trailing bytes)") + " -- a view must never reach an emitted byte");
    }
    var f = fns.projectFacts();
    if (JSON.stringify(f.subSystems) !== JSON.stringify(
          (project.subSystems || []).map(function (x) { return String(x.ref); }))) {
      problems.push("subsystem view state " + st[0] + " changed projectFacts().subSystems");
    }
    if ("view" in f) problems.push("projectFacts() carries `view` -- presentation state must "
      + "stay out of the fact tree, or the seed diff reports a collapse as a model change");
  });
  return problems;
}

// A few invariants of the SHIPPED PAGE that no byte comparison can see, because they are about
// state the page keeps at runtime rather than about what it emits. Each one here is a bug that
// actually shipped, not a hypothetical.
function checkPageInvariants(htmlPath) {
  var html = fs.readFileSync(htmlPath, "utf8");
  var script = extractScript(html);
  var problems = [];

  // `document.body.className = "..."` wipes EVERY other class on <body>. The responsive layer
  // keeps `narrow`, `tiny` and `drawer-l`/`drawer-r` there, so one such assignment in the mode
  // switch meant that tapping View or Edit on a phone destroyed the layout mid-session and
  // dropped the page back into the desktop three-column form. Reported from a real phone.
  if (/document\.body\.className\s*=/.test(script))
    problems.push("the page assigns document.body.className wholesale, which wipes the "
      + "responsive (`narrow`/`tiny`) and drawer classes -- use classList.toggle");

  // ---- the guided tutorial's progress is the READER's, not the model's -------------------
  // Which step of the walkthrough you are on, and whether you finished it, is a fact about the
  // person reading -- not about the system being authored. It lives under its own localStorage
  // key and never enters `project` at all, which is a stronger guarantee than a project.view
  // slot would be: a view key is only excluded because both fact trees are built from an
  // allow-list and someone remembered not to add it, whereas a key that is never written onto
  // the project cannot leak into an emitted byte, into `diff`, or into a project.json handed to
  // a colleague, by any route.
  //
  // That is cheap to state and cheap to break with one "while I am here" edit, so it is pinned
  // both ways: the key has to still be there, and nothing may start writing the state onto the
  // project instead.
  if (!/rosStudio\.tour/.test(script))
    problems.push("the tutorial's own localStorage key is gone -- its progress has to live "
      + "outside `project`, or a saved project starts carrying who read what");
  if (/project\s*(?:\.\s*view\s*)?(?:\.\s*tour\b|\[\s*["']tour["']\s*\])/.test(script))
    problems.push("tutorial state is being written onto `project` -- progress through the "
      + "walkthrough belongs to the reader, and a project.view slot would then have to be kept "
      + "out of both fact trees by hand, forever");

  // The stylesheet and the code must not judge "is this narrow?" independently. They did once,
  // via @media (max-width:...) on one side and matchMedia on the other, and disagreed on a real
  // phone: the toolbar buttons appeared while the panels stayed in column flow.
  var css = /<style>([\s\S]*?)<\/style>/.exec(html);
  var bare = css ? css[1].replace(/\/\*[\s\S]*?\*\//g, "") : "";
  if (/@media[^{]*max-width/.test(bare))
    problems.push("the stylesheet still keys layout off a max-width media query; the "
      + "responsive layer is driven by the body.narrow class so that CSS and JS cannot "
      + "disagree about the same question");
  if (!/body\.narrow/.test(bare))
    problems.push("no body.narrow rules in the shipped page -- the small-screen layout is gone");
  if (!/orientationchange/.test(script))
    problems.push("nothing re-measures on orientationchange, so rotating a phone leaves the "
      + "layout on the previous width");
  return problems;
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

  // ---- Save all's manifest ---------------------------------------------------------------
  // "Save all" in the Commit modal downloads generatedFiles() straight out of the page, on the
  // strength of the byte comparisons just above. But those compare CONTENT keyed by package,
  // and Save all also has to get the FILENAMES right -- genSystem() being byte-perfect does not
  // make "<system>.rossystem" the right name to save it under, and a wrong name is a file the
  // user then hands to `generate` as a different model, or one that silently shadows another.
  //
  // So the whole manifest is held against the files `generate` reported writing: same set of
  // names, same bytes under each name. The .rossystem is included by name here for the first
  // time -- expectPath is found by extension elsewhere, which would not have caught renaming it.
  //
  // Against what generate WROTE, not against readdir(outdir): a project-local `subSystems:`
  // target is STAGED into that directory unchanged, and staging is copying someone else's file
  // off a disk this page cannot reach. Save all does not produce those and does not pretend to
  // -- the Commit modal says so in as many words. Reading the directory instead made every
  // subsystem fixture fail on exactly that difference, which is a real limitation to document
  // rather than a bug to fix in the page.
  var manifest = fns.generatedFiles();
  var manifestNames = manifest.map(function (f) { return f[0]; }).sort();
  var emitted = ["rossystem", "ros2", "ros"].reduce(function (acc, ext) {
    return acc.concat((known[ext] || []).map(function (b) { return b + "." + ext; }));
  }, []).sort();
  if (emitted.length && manifestNames.join(",") !== emitted.join(","))
    problems.push("Save all would write [" + manifestNames.join(", ") + "] but generate emitted ["
      + emitted.join(", ") + "] -- the one-click save and the companion disagree about the file set");
  manifest.forEach(function (f) {
    var p = path.join(outdir, f[0]);
    if (!fs.existsSync(p)) return;                       // already reported above
    var want = fs.readFileSync(p, "utf8");
    if (f[1] !== want) {
      var dm = firstDiff(want, f[1]);
      problems.push("Save all's " + f[0] + " differs from what generate wrote at "
        + (dm || "(trailing bytes)"));
    }
  });

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
  // --no-oracle: these cases test the EMITTER against the Python emitter, byte for byte.
  // Real-server validation is a different question, it is slow (a JVM start and an LSP
  // handshake per call), and now that `generate` runs it by DEFAULT, leaving it on here
  // would put minutes of language-server time into a parity run on any machine that has a
  // JDK -- and would fail these cases on a server verdict they are not about.
  var out = runStudio(["generate", proj, "--outdir", gen, "--no-oracle"]);
  return { project: proj, html: html, expect: generated(gen, fixture), fixture: fixture,
           wrote: { ros2: wroteExt(out, "ros2"), ros: wroteExt(out, "ros"),
                    rossystem: wroteExt(out, "rossystem") } };
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
  // --no-oracle: these cases test the EMITTER against the Python emitter, byte for byte.
  // Real-server validation is a different question, it is slow (a JVM start and an LSP
  // handshake per call), and now that `generate` runs it by DEFAULT, leaving it on here
  // would put minutes of language-server time into a parity run on any machine that has a
  // JDK -- and would fail these cases on a server verdict they are not about.
  var out = runStudio(["generate", proj, "--outdir", gen, "--no-oracle"]);
  return { project: proj, html: base.html, expect: generated(gen, base.fixture),
           wrote: { ros2: wroteExt(out, "ros2"), ros: wroteExt(out, "ros"),
                    rossystem: wroteExt(out, "rossystem") } };
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
      cases.push({ name: path.basename(f) + " [in-page seed]", seed: f, paths: base });
      cases.push({ name: path.basename(f) + " [subsystem views]", views: true, paths: base });
      if (!k) cases.push({ name: "shipped page invariants", page: true, paths: base });
    });
  }

  var failures = 0;
  try {
    cases.forEach(function (c) {
      var problems;
      try {
        problems = c.seed
          ? compareSeed(c.seed, c.paths.project, c.paths.html)
          : (c.page
            ? checkPageInvariants(c.paths.html)
            : (c.views
              ? compareViewStates(c.paths.project, c.paths.html, c.paths.expect)
              : compare(c.paths.project, c.paths.html, c.paths.expect, c.paths.wrote)));
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
