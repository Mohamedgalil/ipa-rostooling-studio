---
description: Author RosTooling models in an interactive self-contained editor, then deterministically generate .ros2/.rossystem/.ros and validate them against the real language server, via scripts/ros_studio.py.
argument-hint: "init [file.rossystem | dir ...] | render project.json [--open] | generate project.json [--oracle | --no-oracle] | diff project.json"
allowed-tools: Bash, Read, Glob
---

## What this command does

`/ros-studio` is the authoring counterpart to `/ros-plot`. Where `/ros-plot` only *reads*
`.rossystem` models, `/ros-studio` lets you *build* them: a self-contained vanilla-JS editor
(draggable nodes, kind-coloured ports, an inspector, connection drawing, a node catalogue,
offline autocomplete, and a zoomable canvas with find and auto-layout) authors an in-memory
project; a Python companion then generates the real files and validates them. It supersedes `/ros-plot` for authoring, but `/ros-plot` remains the
lightweight read-only path — the editor also embeds those four read-only abstraction levels
(System │ Interfaces │ Full │ Deps) behind a View ⇄ Edit toggle.

The page has no network access (it opens as a local `file://`), and every file the companion
writes is generated deterministically from `rosmodel_lint`'s own grammar vocabulary, so the
emitter and the checker can never disagree.

## How to run it

Shell out to the script, passing the user's arguments straight through, using the same Python
env-var convention as `hooks/hooks.json`, `.lsp.json` and `/ros-plot`:

```bash
"${ROSMODEL_PYTHON:-python3}" "${CLAUDE_PLUGIN_ROOT}/scripts/ros_studio.py" $ARGUMENTS
```

The subcommands form the authoring loop:

- **`init [FILE.rossystem | DIR ...]`** — build a `project.json`. With a `.rossystem` argument it
  seeds from it: the read-only extractor recovers the system structure, the sibling `.ros2` files
  are opened to recover each interface's type and the artifacts' parameters, and the sibling
  `.ros` files to recover the message **fields**. With no argument it writes a blank project.
  Prints the `project.json` path.

  **Several sources merge into one project.** Pass any number of `.rossystem` files and/or
  directories (a directory contributes every `.rossystem` beneath it) and the whole tree is
  indexed for `.ros2`/`.ros`, so a system whose artifacts live in a sibling directory can be
  seeded at all — `init` used to print *"seeds from the first file only; ignoring N more"*. The
  merge re-issues every id, renames a node label a merged source already used (two `nodes:` keys
  with one name is RM009), de-duplicates packages and type definitions first-wins, and collapses
  a `subSystems:` reference whose target is *itself* being merged onto the real nodes — declaring
  the same node inline and by reference is RM090. The system name comes from the first source
  unless `--name` overrides it; everything the merge cannot carry (a second `fromFile:`, a second
  file header, a conflicting package entry) is **reported**, never silently dropped. Two nodes
  that share one `from: pkg.ARTIFACT` — two instances of a node type, or two merged systems
  reusing one package — emit that artifact **once**, carrying the union of what each exposes;
  emitting it per referring node was a duplicate key (RM009). If they disagree about it (a
  different ROS node name, or one interface typed two ways) `generate` refuses and names both
  sides, because folding would otherwise change one node's interface type silently.
  `tests/studio_roundtrip.py`'s **MULTI-FILE** section pins both hazards against
  `tests/fixtures/multifile/` (same label, two directories) and `tests/fixtures/subsystems/`
  (one system references the other).

  Seeding is **lossless** and `tests/studio_roundtrip.py` holds it to that: every node,
  exposure and connection in the source must reappear in `generate`'s output. Two fields carry
  the parts that a name alone cannot (`formatVersion: 4`):

  - **`label`** — the exposure key written into the `.rossystem` (`"odom_pub"`), which is a
    different slot from the interface `name` the arrow points at (`"odom"`). It is preserved
    verbatim, so a round-trip reproduces the author's names instead of renaming them. Blank on
    a new interface means "derive from the name".
  - **`exposed`** — whether the interface belongs in the `.rossystem` at all. Connectivity is
    *not* the test: a model may declare an interface for documentation and deliberately leave
    it unwired. Both fields are editable per interface in the inspector.

  An exposure whose arrow target the backing artifact does not declare is kept and flagged
  `orphan` rather than dropped; `generate` then refuses before writing anything, so a model
  that cannot resolve is reported instead of quietly truncated.

  **`subSystems:` is resolved, not skipped.** A reused composition's nodes are not in this
  file's `nodes:` block, so a connection endpoint that names one of their interfaces used to
  resolve to nothing and its connection was dropped — 6 of 9 on the TurtleBot 3 example,
  silently, with `generate` still reporting "0 error(s)". `init` now resolves each entry (first
  against `assets/node_index.json`, then against a sibling `<ref>.rossystem`) and materialises
  its nodes into the project with `backing: "sub"`. They are **read-only** everywhere in the
  editor — their labels belong to the referenced file and are the exact strings a `connections:`
  endpoint has to spell — and `emit_rossystem` writes the `subSystems:` block instead of
  re-declaring them under `nodes:`, which would be RM090.

  **Several entries work too, and used to not.** `components+=SubSystem*` is a repetition, so N
  references are N bare lines — the real server accepts that and rejects the `- entry` form
  outright (oracle cases `17-subsystems-multi` / `18-neg-subsystems-dash`). PyYAML reads neither:
  quoted lines refuse to compose, and *unquoted* ones — what the corpus writes — fold into a
  single scalar, so three references were silently read as one subsystem with a three-word name.
  `init` now normalises the block before parsing, so a model reusing two compositions round-trips
  like any other. What lands on disk is unchanged: `generate` still writes bare lines.

  A subsystem's connectable interfaces are exactly what the referenced file's own `interfaces:`
  block declares, never what the `.ros2` behind its `from:` declares (`checkIfInterfaceInSystem`,
  RosSystemValidator.xtend:87-109). Two of its nodes may declare the same label (the catalogued
  turtlebot's `tf`); that ambiguity is the source file's, RM065 reports it, and the studio binds
  the first in sorted node order rather than inventing a distinguishing label that would resolve
  to nothing.

  **Message types carry their fields.** A companion `.ros` used to be generated from type NAMES
  alone, so every locally invented spec came back with an empty body — legal (`RM080` is an INFO;
  `(BEGIN message=MessageDefinition END)?` really is optional) and therefore invisible to the
  linter, but silent data loss whenever the source defined fields (STATUS.md sec 8 defect 2).
  `project.types` now holds `{"<pkg>/<msg|srv|action>/<Name>": {"fields": {<body>: [{type,
  name}]}}}`, seeded from sibling `.ros` files and editable in the **message types (.ros)**
  section of the system panel. A field is exactly two tokens, a type then a name
  (Basics.xtext:201-204); a **constant** is one token in the NAME box with no whitespace around
  `=` (`FAN_OFF=0`); a reference to another spec is its **quoted, fully qualified** name
  (`"my_msgs/msg/Reading"`), including for a type in the same package — there is no short form.
  Specs whose package the vendored catalogue owns are neither seeded nor accepted: redeclaring
  one would put two `Package_Impl` entries with the same name in the output directory (RM009).
- **`render project.json`** — emit the editor HTML (`ros-studio.html` next to the project by
  default; `--out PATH` to override). The three autocomplete datasets (message/service/action
  types, package names, node catalogue) are embedded so autocomplete works offline. Prints the
  HTML path. **Does not auto-open** — opening is opt-in via `--open`, and only when the user
  asked for it.
- **`generate project.json`** — deterministically emit `.ros2` / `.rossystem` / companion `.ros`
  into `generated/` (or `--outdir DIR`), then run `rosmodel_lint` over the result and report
  diagnostics **verbatim**. A project-local `subSystems:` target — a `<ref>.rossystem` next to
  the seeded file rather than in the catalogue — is **staged** into the output directory
  unchanged, together with the `.ros2` files its own nodes reference, and each copy is printed
  as `staged …`. Without them the reference resolves to nothing there: `rosmodel_lint` raises
  RM050 on every endpoint the subsystem provides, and the real language server reports
  "Couldn't resolve reference to Node …" and then a *same-type* error on the connection two
  lines further down. Lint still covers only the files this project wrote; a staged file is
  someone else's model. It then stages catalogue dependencies (`collect_deps`) and asks the
  **real** language server — see **Validation** below. On a generation/lint ERROR it re-renders
  the editor with the diagnostics injected onto the offending nodes, next to the project as
  `<project>.error.html`, and exits non-zero. `--diff` additionally prints the section below.
- **`diff project.json`** — *what changed since the seed*. See below.

## Validation — two checkers, and one of them is the authority

`generate` runs **two** checks, and it matters which is which:

- **`rosmodel_lint`** (the RM rules) is deterministic, fast, offline, and a deliberate
  **approximation** of the real Xtext validator. It cannot cover everything — that is stated
  throughout `STATUS.md` and `scripts/README.md`, and it is the entire reason the oracle exists.
- **the oracle** is the real language server jar (`tests/oracle/ask_oracle.py`). It is the
  authority. It catches what the approximation cannot — an action server declared with a
  *message* type rather than an action type being the standard example.

**The oracle now runs by default.** It used to be opt-in behind `--oracle`, which meant most runs
consulted only the approximation and *said nothing about not having asked the authority*: a clean
run printed `0 error(s)` and exited 0. That is the root cause behind "the validation misses errors
the jar would catch".

| invocation | behaviour |
|---|---|
| `generate P` | asks the real server **if it can run**; if it cannot, says so loudly everywhere and still exits 0 (the files were written, the lint passed) |
| `generate P --oracle` | *requires* the real server — failing to run it is an **error**, exit non-zero |
| `generate P --no-oracle` | deliberate opt-out; RM rules only, and nothing is reported about the oracle |

**A jar that cannot run is never silent.** Whether Java is missing, too old, or the jar was never
built, the reason appears in three places: on stdout, on stderr, and — the part that matters,
since "silent" was the complaint — **inside the Studio's own error surface**, as a
`<project>.notice.html` whose banner the page opens automatically on load. It names the binary it
found, why it is unusable, what that means (the results you *are* seeing are plugin-only and
cannot catch everything), and how to fix it (`ROSMODEL_JAVA`, or build the jar). Never a bare
stack trace, never nothing.

That page is `.notice.html`, **not** `.error.html`: the generation succeeded and the lint was
clean, so a file whose own name says "error" would misreport it — and would overwrite the genuine
error page from a previous failing run. For the same reason the banner carries its own title and
severity now instead of the page hard-coding "Generation failed"; a page that overstates one thing
gets believed less about the next.

**A version check, not just an existence check.** The jar is built with `Build-Jdk-Spec: 21` and
the launcher needs Java 19+, but nothing in the repo ever checked that — the requirement lived
only in prose. An older JVM passed the `exists()` test, started, and died inside the JVM with
`UnsupportedClassVersionError`; what the caller saw was the 45-second initialize wait timing out
as `NO_INITIALIZE_RESPONSE`, a message about the LSP handshake for what is really "your Java is
too old". `ask_oracle.py --preflight` now parses `java -version` and says the true thing. It is
also the single place that knows where java and the jar live — `ros_studio.py` asks it rather than
re-deriving those paths, because two copies would drift the first time either moved.

`ROSMODEL_JAVA` also falls back to whatever `java` is on **PATH** before the hard-coded Adoptium
path it used to default to — which is what `.lsp.json` has always done, and why a machine with a
perfectly good JDK could be told `java not found at C:\Users\mae\...`, a path from someone else's
laptop.

**Three ways the old code turned a broken oracle into a clean verdict**, all fixed, all pinned by
`tests/oracle_gate.py`:

1. `proc.returncode` was never checked, so `ask_oracle.py` could print an `ACCEPTED` line and
   then die and still be read as a pass;
2. the verdict was `"ACCEPTED" in out and "REJECTED" not in out` over stdout **plus stderr** — a
   text search across a stream that also carries diagnostic *messages*, so a model whose own text
   contained either word decided its own verdict;
3. `ask_oracle.py` exits 0 even when every case failed to run, because `NO_INITIALIZE_RESPONSE`
   and `MISSING_JAR` are per-case *statuses* — and a case that never received diagnostics still
   printed `ACCEPTED — 0 error(s)`. A server that never answered was indistinguishable from a
   model with nothing wrong with it.

The verdict now comes from the structured `results.json` records — per-case `status` plus the
actual diagnostics — and a status that is not `OK` is a failure, not a pass. Those results are
written into the **output directory**, never `ask_oracle.py`'s default of `tests/oracle/results.json`,
which is this repo's checked-in 19-case regression record: a `generate --oracle` run used to
overwrite it with its own single case.

**Oracle diagnostics reach the node cards**, not just the console. `oracle_diagnostics()` maps the
records into the same `{"global", "byNode"}` shape the linter's findings already use, so they get
the same warning badge, inspector section and Issues-rail entry. The mapping is honestly bounded,
because a record carries `{file, line, severity, message}` and *no column* (`ask_oracle` discards
`range.start.character`):

- by **file**, the reliable half — `generate` writes `<pkg>.ros2` and `<pkg>.ros`, so the stem *is*
  the package name and maps to that package's nodes with no string guessing;
- by **message**, for `.rossystem` diagnostics, which name a node or interface when they are
  reference errors (`Couldn't resolve reference to Node 'pkg.artifact'`) and name nothing at all
  when they are parser errors (`mismatched input 'msgs:'`). Same substring scan the lint mapper
  uses, with the same limits.

Anything that maps to neither goes into the **banner**, not into `project.diagnostics.global` —
that list is carried into the page but nothing renders it on the companion path, so a diagnostic
left there alone would be invisible, which is the failure this whole feature exists to remove.

`tests/oracle_gate.py` pins the whole failure path, and needs **no working jar** to do it — it
points `ROSMODEL_JAVA` at a path that does not exist, which is reproducible anywhere. The
test suites themselves pass `--no-oracle`: they check the emitter byte for byte, and leaving the
oracle on would put minutes of language-server time into a parity run on any machine with a JDK,
and fail those cases on a server verdict they are not about.

## `diff` — what changed since the seed

`project.json` records `seededFrom` (and `seededFromAll` for a merge), so after editing a
seeded system you can ask what you actually changed. `diff` answers it at the **model** level:

```bash
"${ROSMODEL_PYTHON:-python3}" "${CLAUDE_PLUGIN_ROOT}/scripts/ros_studio.py" diff project.json
```

```
diff -- project.json since turtlebot3_navigation.rossystem

  system
    ~ system.name                                 turtlebot3_navigation -> tb3_edited
  nodes
    ~ nodes.amcl.namespace                        (none) -> /robot1
    - nodes.bt_navigator.parameters.use_sim_time  false
    - nodes.controller_server                     exposures: 3; from=controller_server.controller_server
    + nodes.my_new_node                           exposures: 1; from=my_pkg.my_node
  connections
    - connections                                 odom -> odom_ctrl_sub
  packages
    + packages.my_pkg                             artifacts: 1

  6 change(s): 2 added, 2 changed, 2 removed
```

Marks: `+` added · `-` removed · `~` changed · `%` same items, different order.

**Not a text diff, on purpose.** The emitter fixes key order (`ROSSYSTEM_TOP_KEYS` /
`ROSSYSTEM_NODE_KEYS`), quotes every EString, sorts each node's interfaces by `(kind, name)` and
re-places comments by the policy above — so a round-trip that changed *nothing* still rewrites
most lines. Both sides are instead reduced to the same fact tree and that is compared:

| section | leaves |
|---|---|
| `system` | `name`, `fromFile` |
| `subSystems` | each reference, in order |
| `nodes` | per node: `from`, `namespace`, each `exposures.<label>` (`kind-> artifact::name`), each `parameters.<label>` |
| `connections` | each `fromLabel -> toLabel`, as a multiset plus an order check |
| `packages` | per package: `fromGitRepo`, and per artifact its `node`, each interface's type, each `qos:` block, each parameter's `type = default` |
| `types` | per locally defined spec, the field list of each body |

The **before** side is read from the seed file(s) with the very parsers `init` seeds from; the
**after** side is what `generate` actually writes, emitted to a temp directory and read back the
same way. Nothing is written to the project directory.

Two flags: `--against FILE.rossystem` diffs against a file of your choosing (the only way to use
`diff` on a project created blank), and `--json` emits the change records.

Notes it may print, both worth passing on verbatim:

- a **merged seed** replays `init`'s label uniquifier on the seed side, but a `subSystems:`
  reference the merge collapsed reads as a removal — which is what the emitted file really says;
- `project_facts() and the generated files disagree …` means the editor's live preview of this
  diff and the companion's report will differ. That is a bug in the emitter or the predictor, not
  an edit you made; `tests/studio_parity.js` fails on it.

Inside the editor the same report is the **changed since the seed** tab of the Commit modal,
computed live from the project as you edit (the seed's fact tree travels with the page, so it
works offline). `tests/studio_parity.js` holds the tab's text to `format_diff()`'s bytes and the
editor's `projectFacts()` to the companion's `project_facts()`, exactly as it does for the three
file previews.

Because the diff is model-level it also surfaces losses the round-trip has, rather than papering
over them. That is how the two `parameters:` defects were found and it is worth keeping as the
worked example, because one of them the diff could *not* see: on the TurtleBot 3 example a clean
seed→generate used to report `- nodes.bt_navigator.parameters.use_sim_time`, while `ur_robot`'s
five system-level parameters vanished under a confident "no model-level change since the seed"
— the fact tree had no slot for them either, so the check was blind to exactly the loss it
exists to catch. Both slots are modelled now (see **Parameters** below) and both round-trip; the
lesson kept is that a silent diff is only as trustworthy as the fact tree behind it.

## Parameters — two slots, not one

A parameter lives in **two unrelated grammar rules**, and conflating them is the defect this
repo keeps re-finding under different names (it is the same shape as exposure *label* vs
interface *name*, which has now bitten three times).

| | `.ros2` artifact parameter | `.rossystem` node parameter | `.rossystem` system parameter |
|---|---|---|---|
| rule | `Parameter`, Basics.xtext:41 | `RosParameter`, RosSystem.xtext:78 | `Parameter`, Basics.xtext:41 |
| written as | `name: / type: T / default: D` | `- "label": "artifact::name" / value: V` | `name: / ns? / type: T / default? / value?` |
| means | this artifact **declares** the parameter | this system **exposes** it and **overrides** its value for this instance | a system-wide declaration, a peer of `nodes:` |
| lives in | `<pkg>.ros2` | the node's `parameters:` block | the system's own `parameters:` block |

A node parameter therefore carries **both halves** in the project, exactly as an interface
carries `name` (artifact side) and `label`/`exposed` (system side):

```json
{"name": "use_sim_time", "ptype": "Boolean", "value": false,
 "label": "use_sim_time", "exposed": true, "sysValue": false}
```

`name`/`ptype`/`value` are written to the `.ros2`; `label`/`sysValue` are written to the
`.rossystem`. An exposure whose artifact declares no such parameter is kept and flagged
`orphan`, the same way an undeclared interface exposure is — never silently dropped.

Two traps worth knowing, both of which were live bugs:

- **`default:` is not `value:`.** `default:` belongs to the *ParameterType*
  (`ParameterStringType: 'String' ('default:' ...)?`, Basics.xtext:77-80) — indentation is
  hidden whitespace, so `type: String` / `default: x` is one type expression. `value:` is the
  `Parameter`'s own optional slot. A file may carry both; folding them emits one into the
  other's position.
- **`ns:` is not a string.** It takes a `Namespace`, which is one of three bare KEYWORDS —
  `GlobalNamespace` | `RelativeNamespace` | `PrivateNamespace` (Basics.xtext:13-32). Quoting it
  is `no viable alternative at input '"..."'` from the real server. The rule cannot express an
  actual namespace string at all, which is why RM044 records zero corpus support.

A parameter known only as an exposure has no declared type, but the `.ros2` this project writes
for a hand-backed artifact requires one. The type is **inferred from the override value**
(`false` → `Boolean`, `40` → `Integer`, `0.5` → `Double`, otherwise `String`) rather than
defaulted to `String`, which used to retype every such parameter and turn `value: false` into
`type: String / default: 'false'`.

Both slots are held to the real 3.1.0 language server by `tests/oracle/cases/22-parameters`
(ACCEPTED, 0E/0W) and to a lossless round-trip by `tests/fixtures/params/`.

## Where a node came from — colour, legend, and the System level

A project composed from several sources — `init`'s multi-file merge, or the editor's **Import** —
used to lose the one fact that made it readable: *which system each node came from*. Once merged
they were one undifferentiated pile of cards, and the only surviving trace of the boundary was a
rename in `init`'s diagnostics.

`project.json` now records it per node as **`srcSystem`**, stamped by `seed_from_many`'s pass A
(where the source is still identifiable) and by the in-page importer. An imported `project.json`
that already carries origins of its own keeps them rather than being flattened onto the importing
file's name — the node really did come from that system.

`srcSystem` is **provenance, not view state and not content.** It sits on the node, a peer of
`seededFromAll`, because it is a fact about the model's history rather than a drawing choice. It
cannot reach an emitted byte: `emit_rossystem`/`emit_ros2` write named keys and both fact trees
build from an allow-list, so an extra node key is excluded by construction. `tests/studio_parity.js`
stamps an unmistakable value on **every** node — including catalogue- and subsystem-backed ones —
re-emits, and fails if it appears in the `.rossystem`, in `projectFacts()`, or in the companion's
`project_facts()`. That last one matters most: a leak there would make `diff` report every node of
a merged project as changed.

Three things use it, and **all three are inert unless there is more than one source system** — a
blank or single-source project looks exactly as it did:

- **Colour.** Each source system gets one of eight hues, applied as a card border, a 5px left
  edge and a tinted header. The palette lives beside the interaction-kind one in
  `_studio_common.py` and is defined in all four theme blocks (light, `prefers-color-scheme:
  dark`, and both explicit `data-theme` overrides). It is a **different axis** from the kind
  colours — a node has both — so origin owns the card and kind keeps the ports, and the two never
  compete for the same pixel. Hues are separated in the Okabe-Ito spirit (blue, orange, green,
  purple, magenta, gold, teal, slate), and no adjacent pair relies on red-vs-green. More than
  eight systems wrap; the legend still names each one. The origin colour is written *above*
  `.sel`/`.hasdiag`/`.issue-e` in the stylesheet so selection and diagnostics win the border
  back — where a card came from matters less than "this one is selected" or "the server rejected
  this one" — while the left edge keeps saying it regardless.
- **A legend that filters.** A **Source systems** section in the rail, following the **Show
  kinds** pattern: one row per system with its swatch, its name and its node count, and a
  checkbox that hides that system's nodes. Hiding takes the **edges** with it, exactly as the
  kind filter does — a filter that hid the cards and kept the wires would draw edges into empty
  space. Colour is never the only channel: every row is labelled and counted, so the legend reads
  correctly with no colour vision at all. The section is rebuilt on every render, because Import
  can add a system at any time and a legend that missed it would be worse than none.
- **Containers at the System level.** Level 1 already hid every interface row, so a merged
  project at the level whose *name* promises system-scale grouping was the level that showed it
  least: a heap of bare name cards. Each source system is now one box there, its ports being the
  exposure labels its members declare, wired ones solid and unwired dimmed.

**The containers are the subsystem machinery on a different axis, not a parallel one.**
`groupPorts()` — "one row per exposure label across this set of nodes, with every (node,
interface) pair behind it" — was lifted out of `subPorts()` and is now shared by both, so
`subPorts(ref)` is a one-line call. Keeping a second copy is the shape `STATUS.md` keeps
recording: two implementations of one rule that agree until someone fixes only one. The
invisible-stacked-port trick is carried over for the same reason it exists for subsystems —
`drawEdges()` resolves an endpoint by querying `[data-n][data-i]`, so every pair behind a
collapsed row still needs an element or its edge silently disappears.

That uncovered a **real bug in `portCenter()`**, which this fixes for both groupings: its
fallback looked only for the member's own `.node[data-n=…]` card. At level 1 every port is
hidden, so the width test fails; and a member inside a container is not rendered at all, so the
card lookup fails too. Both misses meant the edge was silently dropped — at the one level whose
whole job is showing how the groups connect. It now falls back to whichever container is standing
in for that node, so the wire lands on the group. Verified in a browser: two cross-system
connections survive the switch from Full to System and re-route onto the boxes.

A node can be *both* "from source system X" and part of a `backing:"sub"` reference. Those are two
different groupings and nesting them is **not attempted**: a `backing:"sub"` node has a null
origin and stays inside the subsystem machinery that already owns it. That is also why wrapping a
selection needs no special handling — wrap mutates the node in place, so its `srcSystem` survives
untouched and simply stops being consulted while it is a sub member.

Container positions live in `project.view.sysPos` and the per-system filter in
`project.view.systemShown`, so both round-trip with the rest of the visualization; dragging a
container is a view change, never an edit, and never enters the undo history. Boxes are first
placed in a row ordered by their members' centroid — centroids of overlapping groups overlap too,
and two boxes stacked on each other is strictly worse than a row that needs one drag — starting
below the floating find control, whose canvas footprint was measured rather than guessed.

## Subsystems — one level of abstraction

A `subSystems:` entry names one whole reused composition. The studio used to **flatten** its
nodes onto this file's canvas, marked only by a badge — reusing the catalogued `turtlebot` added
three cards indistinguishable from your own; reusing `turtlebot3_navigation2` would add fourteen.
`/ros-plot` went the other way and resolved every connection into a subsystem to a dashed
`(dangling endpoint)` ghost. Neither showed the thing a reader actually wants: **how the reused
pieces connect, without their internals.**

Three states per subsystem. Toggle from the box itself, the frame's title chip, or the
**subsystems** section of the system inspector.

| state | what you see | when |
|---|---|---|
| **collapsed** (default) | one box; its ports are the labels the referenced file exposes | reading the composition |
| **framed** | the internals, inside a labelled frame | the subsystem is small and its wiring matters |
| **drill-in** (`↗`) | that file alone, read-only, breadcrumb back | the subsystem is too big to frame |

**The collapsed box's ports are the exposed labels**, because that is the DSL's own view: a
`connections:` endpoint is a bare label resolved file-wide, so the label *is* the subsystem's
port. Wired ports are solid, available-but-unwired ones dimmed — the gap that made a reused
system look inert. A label two member nodes both declare (the catalogued turtlebot's `tf`)
collapses to one row badged **⚠2**: that ambiguity is real (RM065), it belongs to the referenced
file, and this is the first view in which it is visible rather than buried in a linter warning.

**Framed layout does not use a new algorithm.** Each framed subsystem's internals are laid out
alone with the existing layered pass; the resulting bounding box is then treated as one oversized
node in a parent pass over the same code, and the internals are translated into place. A
subsystem too complex to fit in a frame still will not fit — that is what drill-in is for.

**No view can change an emitted byte.** The state lives in `project["view"]`, which is excluded
from both fact trees, and `emit_rossystem` skips `backing:"sub"` nodes regardless. That is
asserted rather than argued: `tests/studio_parity.js` emits under *every* state and compares
bytes, because a view that quietly changed the model would be invisible — the preview and the
file would agree, and both would lint clean.

### What a subsystem view can show you today

Nothing in this repo exercises it hard, and that is worth knowing before you read a frame as
empty:

| referenced system | nodes | interfaces | internal connections |
|---|---|---|---|
| `turtlebot` (catalogue) | 3 | 7 | **0** |
| `robot_base` / `sensor_base` / `labelled_base` | 1 | 1–2 | **0** |
| `ur5e_cell_moveit_config` | 0 | 0 | **0** |

Every referenced system in the tree has **zero internal wiring**, and the one large candidate
(`turtlebot3_navigation2`, 14 nodes) declares zero `interfaces:` so it cannot be referenced
usefully at all. An empty frame is usually the source file's truth, not a read failure.
`tests/fixtures/subsysgraph/` exists solely to provide a subsystem that *does* have internal
connections, so the framed layout and drill-in have something real to be tested against.

Drill-in needs the referenced file's own graph, which neither `resolve_subsystem` nor the system
index used to carry. The seeder now embeds it as `subSystems[i].graph` (nodes + connections), and
`build_node_index.py` records `connections` for catalogued systems. Both are presentation data,
excluded from the fact tree. A reference whose file could not be read still resolves and still
draws its box — it simply cannot be opened, and says so.

## Working a large canvas

Nine nodes fit on a fixed grid; dozens do not. The canvas therefore has:

- **Zoom and pan.** Ctrl/⌘+wheel (or a trackpad pinch) zooms *at the pointer*; a plain wheel or
  two-finger scroll pans; dragging empty canvas pans. **Fit**, **100%**, **−**/**+** sit bottom
  left, with `F`, `0`, `-`, `+` as shortcuts. The SVG wire layer is a child of the transformed
  node layer, so edges stay on their ports at every zoom level. The page opens at 100% when the
  system fits and only ever zooms *out* to make it fit.
- **Find** (top left, or `Ctrl+F`). Matches the node label, the `package.node` the file will
  spell, the namespace, and **every interface name and type** — so "which node publishes
  `/odom`" is one query. Matches are outlined and everything else recedes; Enter / Shift+Enter
  step through them and scroll each into view.
- **Auto layout** — a layered (Sugiyama-style) arrangement that follows connection direction:
  sources on the left, sinks on the right, four barycentre sweeps to cut crossings, isolated
  nodes in a trailing column. Feedback edges (a controller subscribing to what it drives) are
  detected and excluded from the *layering* only; they are still drawn. Node sizes are measured
  off the rendered boxes rather than estimated, because a node's height is its interface count.
  Node `x`/`y` live in `project.json`, so a layout is a normal **undoable** edit (`Ctrl+Z`), and
  **Reset layout** still returns to the positions the page was rendered with.

## What happens to comments

Round-tripping a model used to **delete every comment in it** — `generate` wrote only its own
`# assets/…` provenance lines. Comments are now captured by `init`, carried in `project.json`
(`formatVersion: 4`), editable in the editor, and re-emitted by `generate`. The policy below is
exact and `tests/studio_roundtrip.py`'s **COMMENTS** check enforces it against
`tests/fixtures/comments/` and `tests/fixtures/subsystems/`, which between them carry one witness
per position — including the ones the policy deliberately drops, which `init` must *report*.

The rule in one line: **a leading comment block attaches to the next modelled element; a trailing
comment attaches to the element on its own line.**

**Preserved** — the position survives and the text comes back verbatim:

| `.rossystem` | `.ros2` |
|---|---|
| the file header block | the file header block |
| block above a node · trailing on the node key · trailing on `from:` | block above an artifact · trailing on the artifact key |
| block above an exposure · trailing on the exposure | block above an interface · trailing on the interface key · trailing on its `type:` line |
| block above a connection · trailing on the connection | block above a parameter · trailing on the parameter key |
| block above a `subSystems:` entry · trailing on the entry | |
| trailing on `fromFile:` | |

**Normalised** — kept, but not byte-for-byte where it stood:

- indentation follows the *emitted* element, not the source;
- exactly one leading space is stripped and `# ` is always re-emitted, so `#foo` comes back
  as `# foo` — but `#  foo` keeps its second space and `##x` comes back as `# #x`. Nothing is
  ever deleted; extra spaces and extra hashes are content, not formatting (measured
  2026-08-14 — the earlier claim that `#  foo` collapses and `##` loses a hash was wrong);
- a line break typed into a comment field becomes a space (a comment runs to end of line, so a
  break would end it and turn the rest into code);
- a leading block that preceded a **block key** (`nodes:`, `interfaces:`, `artifacts:`, …)
  re-emerges before the **first element inside** that block — the model has no slot for the key
  itself;
- a trailing comment on a `from:` or `type:` line shares the line with the RM088/RM089
  provenance the emitter owes that reference. If your comment already names that file it
  *replaces* the provenance (which is what the TurtleBot 3 example's own comments do); otherwise
  the provenance is kept and your text is appended after ` -- `, so an edit can never silently
  delete a disclosure the linter requires.

**Dropped, and always REPORTED** — `init` prints one line per lost comment, naming the file, the
line and what it annotated, so it can be re-placed by hand (SKILL.md rule 12). This is everything
the project model has no slot for: `processes:`, the
inside of a `qos:` block, trailing comments on block keys (`nodes:`, `subSystems:`, `interfaces:`,
`qos:`, …), a comment block at end of file with nothing after it, and anything attached to an
element the project does not carry.

Every slot is editable: a **comments** section on the node and on the connection inspector, a
`cmt` chip beside `qos` on each interface and parameter, and the `.rossystem` file header, each
`subSystems:` entry and each package's `.ros2` header in the system panel (deselect everything to
reach it). A `subSystems:` node itself has no comment slots — it is declared in the referenced
file, and its comments live there. The
`.rossystem`/`.ros2`/`.ros` tabs under **Commit** preview the generated files exactly as they will
be written — `tests/studio_parity.js` holds all three previews to the Python emitter's bytes, and
the fourth tab, **changed since the seed**, to `diff`'s.

## Starting from a real ROS 2 repository

**From ROS 2 source…** in the rail (beside **Add** / **From catalogue…**) covers the case the
editor previously had no answer for: you have a source repo, not a model.

**It does not run the pipeline, and does not pretend to.** This page is a `file://` document with
no network and no way to spawn a process — it cannot invoke Python, full stop. A button that
looked like it imported a repo and silently did nothing would be worse than no button. So it does
the part it genuinely can: you type the paths you know, and it assembles the **exact,
correctly-ordered, correctly-flagged** commands, with a copy control and a note saying you run
them in a terminal — or paste them to Claude Code and ask it to.

The pipeline is the one `skills/ros-model/SKILL.md` documents under *Converting real source*, and
every flag comes from the two extractors' own argparse. `tests/extract_golden.py` runs steps 1 and
2 exactly this way, which is executable ground truth rather than prose:

1. `extract_ros2_interfaces.py <src> -o <out>/rosnodes --emit-msgs <out>/msgs --json …`
2. `extract_rossystem.py <launch…> --models <out>/rosnodes -o <out>/<system>.rossystem --workspace <src> --json …`
3. `ros_studio.py init <out>/<system>.rossystem --out <out>/project.json`

Four things the panel exists to get right, each of which is a way this goes wrong by hand:

- **Step 1's `-o` and step 2's `--models` must be the same directory.** `ModelIndex` does a flat
  `os.listdir()` of `--models`, and a wrong path **fails silently** — there are simply no local
  models, so every launch node resolves against the vendored catalogue or is skipped with a
  `# FLAG`. Both are derived from one **output directory** field rather than asked for twice, and
  the generated block says so in a comment.
- **The launch file cannot be guessed.** Nothing discovers it, and a real repo usually has
  several. It is a required field, and until you fill it the commands carry a `<FILL-IN>`
  placeholder rendered in red — visually distinct from every real value, and left *unquoted* so
  the shell fails loudly on it rather than silently accepting a plausible-looking path. Several
  launch files are accepted (they are `nargs="+"`); the **first** decides `fromFile:` and the
  default system name, which the field's hint says.
- **Optional flags appear only when you fill them in.** `--system-name` and `--controllers-file`
  are real and documented, but emitting them empty would be inventing a value. `--controllers-file`
  is auto-discovered from the launch arguments when it can be; the hint says to pass it when the
  extractor reports it could not.
- **A non-zero exit mid-pipeline is normal.** Step 2 exits non-zero whenever it flags anything and
  step 1 does on a lint ERROR — *a partial model is a result, not a failure* — so the note tells
  you to read the reports rather than stop. It also names the `${CLAUDE_PLUGIN_ROOT}` trap: the
  variable is set when the plugin is installed and unset inside the repo, where the paths are
  plain `scripts/…`, which is exactly what a "No such file or directory" on step 1 means.

Paths are POSIX-single-quoted when they need it, so a directory with a space survives the copy.
Verified by running the generated commands unmodified against `tests/fixtures/extract/src`: all
three steps exit 0 and produce a `project.json` of 4 nodes and 9 interfaces that `generate`
re-emits cleanly.

## Opening files in the page

The page can now **read** models, not just write them. **Open** in the topbar (or drag files onto
the canvas) accepts:

- **a `project.json`** — loaded exactly as saved. This is the page's own format, so nothing is
  re-derived; it is how you resume a session, or hand a project to someone who has no Python.
- **a `.rossystem` together with its `.ros2` and `.ros` files** — select them all at once (the
  dialog is multi-select) and the page seeds a project from them in the browser, with no
  companion involved. Catalogue-backed nodes and catalogued `subSystems:` references resolve
  against the datasets embedded in the page, so a model reusing `turtlebot` works offline.

`init` remains the **authoritative** seeder: it walks sibling directories, resolves a
project-local `subSystems:` target that was not opened, and reports everything it could not
carry. The in-page loader does the same job on exactly the files it is handed, and says what it
could not do — a subsystem whose file you did not open, a node whose `.ros2` is missing, a
connection whose endpoint therefore cannot be re-linked — in the banner, rather than seeding
less and staying quiet about it.

That makes it a **second implementation of the seeder**, which is the shape that has silently
truncated this project's models three times. It is held to the Python one by
`tests/studio_parity.js`'s **`[in-page seed]`** cases: for every checked-in fixture and for the
TurtleBot 3 example, the loader is handed the same file set `init` reads and its project must
match `init`'s fact-for-fact — nodes, exposures, connections, subSystems, namespaces, parameters,
qos and types — **and comment-for-comment**, since the fact tree deliberately carries no comments
and a loader that dropped them all would otherwise pass. It caught two real losses while being
written (the `.ros2` artifact comments, and every node a catalogued `subSystems:` provides).

Loading replaces the current project, so it asks first when there are unsaved changes, and the
load itself is undoable.

## The saved visualization

`project.json` used to record only *part* of what a reader had arranged: node `x`/`y`, and
`project.view.subsystems`. Everything else was a plain JS variable that died with the tab — the
subsystem box positions (`subPos`), the Deps view's package boxes (`pkgPos`), the abstraction
level, the Edit/View mode, the **Show kinds** filter, **auto sides**, the camera. So a layout
built over ten minutes survived a reload only by accident, and **Auto layout** — which clears
`subPos`/`pkgPos` by design — threw the rest away with no way back.

All of it now lives under `project["view"]` and round-trips:

| key | what it holds |
|---|---|
| `subsystems` | collapsed / framed, per `subSystems:` reference (unchanged) |
| `subPos` · `pkgPos` | where the subsystem and package boxes were dragged to |
| `level` · `mode` | which of System │ Interfaces │ Full │ Deps, and Edit vs View |
| `hiddenKinds` | the **Show kinds** filter, including the `param` pseudo-kind |
| `autoSides` | the port-side toggle |
| `camera` | `k`/`tx`/`ty` — where the reader was standing |

Two lines are drawn deliberately, because "restore everything always" is the wrong answer twice:

- **Layout is undoable; preferences are not.** `Ctrl+Z` after **Auto layout** restores `subPos`
  and `pkgPos` along with the node positions it already restored — that is the complaint this
  fixes. It does *not* rewind the level, mode or filter you happen to be looking through, because
  a view was never an edit (the same line `secOpen` already draws for collapsed sections).
- **The camera is saved but only restored by an explicit load.** A `project.json` carrying one
  opens exactly where it was saved; one carrying none still gets the fit-on-open pass, so a
  freshly seeded project is unaffected.

`autoSides` and `hiddenKinds` remain localStorage preferences *as well*, and the project's value
wins when a project carries one — so a filter follows you between projects, but a saved
arrangement is still the arrangement you saved.

**None of it can reach an emitted byte.** Both fact trees build from an allow-list of model keys
rather than by deleting presentation ones, so a key added here is excluded by construction. That
is asserted rather than argued: `tests/studio_parity.js`'s `compareViewStates()` now emits under a
*populated* view — a non-default level, View mode, a filter hiding two kinds, `autoSides` on, a
camera far from the origin, positions for boxes that may not exist — for **every** fixture rather
than only the ones with a `subSystems:` block, byte-compares the `.rossystem`, and checks that
neither `projectFacts()` nor the companion's `project_facts()` grew any of the keys. A project
with a populated `view` and one without must produce identical `--facts` output, or `diff` would
report dragging a box as a model change.

## The commit hand-off

Inside the editor, **Commit** opens a modal with two ways out.

**Save all files** downloads what `generate` would emit — the `<system>.rossystem`, every
`<pkg>.ros2`, every companion `<pkg>.ros`, and the `project.json` — as one browser download each.
This is the direct path the manual round-trip existed to work around, and it is safe in the
specific sense that matters here: the page is still a `file://` document with no network and no
filesystem API, nothing is overwritten, and the browser's own download UI is the confirmation
step. (A burst of programmatic downloads is what makes a browser stop honouring them, so they are
staggered; Chrome asks once to allow multiple downloads.)

It rests on a property this repo already proves rather than on a new emitter: `tests/studio_parity.js`
holds `genSystem()`/`genRos2()`/`genRos()` to the Python emitter's **bytes** for every fixture, so
the previews are the generated files, not an approximation. That test now also pins the
**manifest** — the filenames and the file *set*, not just the content keyed by package — because
`genSystem()` being byte-perfect does not make `<system>.rossystem` the right name to save it
under, and a wrong name is a file the user hands back to `generate` as a different model.

Two things Save all deliberately does **not** do, and the modal says so:

- it does not lint and it does not ask the language server — `generate` is still the path to the
  **verdict**, and only it can re-render the editor with diagnostics on the offending nodes;
- it cannot produce a staged project-local `subSystems:` target. Staging is copying someone
  else's file off a disk this page cannot read. That is why the parity check compares Save all's
  manifest against the files `generate` reported *writing* rather than against its output
  directory, which also holds what it *staged*.

**project.json only** is the original hand-off, unchanged: a Blob via an `<a download>` (which
works on `file://`) with a pre-selected `<textarea>` copy fallback. The user saves it, returns,
and says "done"; you then run `generate` on that file to produce and validate the real files.

Because that hand-off is manual, the page keeps the session safe on its own:

- **Undo / redo** (topbar buttons, `Ctrl+Z` / `Ctrl+Shift+Z` / `Ctrl+Y`) over a 50-deep stack of
  project snapshots. Deleting a node also deletes every connection touching it, and undo brings
  both back. Typing in one field coalesces into a single entry, and the shortcut is left to the
  browser inside fields the model has never seen (catalogue search, the add-interface form).
- **Autosave** to `localStorage`, debounced and keyed by system name. On load a stored autosave
  is *offered*, never applied: the prompt names it, shows it beside the project the companion
  seeded, and requires a choice. Blocked or full storage degrades to a warning in the topbar.
- **An unsaved-work guard** on tab close, armed only while there are changes since the last
  Commit/download.

If the user reports the page asking to restore something unexpected, that is a previous session's
autosave for the same system name — "Discard and use the seeded project" clears it.

## Reporting back

1. **Report the printed path** (project.json, HTML, or the generated files) verbatim.
2. **Do NOT auto-open** the HTML — `--open` is opt-in only.
3. **Surface diagnostics verbatim.** `rosmodel_lint` findings and any oracle verdict are model
   facts; pass them through as-is. A clean run is `0 error(s)` from the linter and `ACCEPTED`
   from the oracle.

## Non-goals

This command authors and validates; it does not lint-fix existing files (that is
`scripts/rosmodel_lint.py`, run on write by the `PostToolUse` hook) and it never synthesises a
connection the user did not draw.
