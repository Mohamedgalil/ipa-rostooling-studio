---
description: Author RosTooling models in an interactive self-contained editor, then deterministically generate .ros2/.rossystem/.ros and validate them against the real language server, via scripts/ros_studio.py.
argument-hint: "init [file.rossystem | dir ...] | render project.json [--open] | generate project.json [--oracle] | diff project.json"
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
  someone else's model. With `--oracle`, it stages catalogue dependencies (`collect_deps`)
  and asks the **real** language server (`tests/oracle/ask_oracle.py`, needs Java). On a
  generation/lint ERROR it re-renders the editor with the diagnostics injected onto the
  offending nodes, next to the project as `<project>.error.html`, and exits non-zero.
  `--diff` additionally prints the section below.
- **`diff project.json`** — *what changed since the seed*. See below.

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

## The commit hand-off

Inside the editor, **Commit** opens a modal that downloads the `project.json` (a Blob via a
`<a download>`, which works on `file://`) with a pre-selected `<textarea>` copy fallback. The
user saves it, returns, and says "done"; you then run `generate` on that file to produce and
validate the real files.

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
