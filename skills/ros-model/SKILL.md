---
name: ros-model
description: Generate and validate RosTooling model files (.ros2 AmentPackage, .rossystem system composition, .ros message specs) for the Fraunhofer IPA ROS 2 Xtext toolchain. Use when asked to model a ROS 2 package, node, its publishers/subscribers/services/actions/parameters, or to wire nodes into a system with connections.
argument-hint: "[ros2 package path or system name]"
---

# RosTooling model generation

Emit files for an **indentation-sensitive Xtext DSL**. It looks like YAML. It is not YAML.
Indentation is lexed into mandatory `BEGIN`/`END` tokens; a wrong indent is a parse error, not a
style nit.

`$ARGUMENTS` is the target: a path to a ROS 2 package (introspect it, emit one `.ros2` per node) or
a bare system name (emit a `.rossystem`). If empty, ask which of the two the user wants before
emitting anything.

## When to use

- Authoring or fixing `.ros2`, `.rossystem`, or `.ros` files.
- Converting a ROS 2 package / launch file / node introspection dump into RosTooling models.
- Reviewing an existing model against the grammar and validators.

## When not to use

- Writing actual ROS 2 C++/Python code, launch files, or `package.xml` — those are the *input*.
- Anything URDF. **Never inline URDF, XML, or a robot description into a model file.** A robot
  description reaches a model only as a `type: String` parameter whose value is a quoted path or an
  empty string `""`.
- `.ros1` files. Out of scope.

## Decision tree: which file

| You need to express | File | Root rule |
|---|---|---|
| Message / service / action **type definitions** | `.ros` | `Package_Impl` — has `msgs:` / `srvs:` / `actions:` |
| A **package + its nodes' interfaces** (pubs, subs, services, actions, params) | `.ros2` | `AmentPackage` — has `fromGitRepo:` / `artifacts:` / `dependencies:` |
| **Composition**: which nodes run together, and what connects to what | `.rossystem` | `RosSystem` — has `nodes:` / `connections:` |

**The rule people get wrong:** `.ros2` uses `AmentPackage`, which has **no `msgs:` / `srvs:` /
`actions:` block**. `Ros2.xtext` opens with `@Override Package returns Package: AmentPackage;`, so
`AmentPackage` is the entry rule and `Package_Impl` is unreachable. Those three keywords *do* appear
in the parser's token table — that is a decoy, not permission. Message specs live in `.ros` files
only. Zero of 253 corpus `.ros2` files contain a `msgs:` block.

A `.ros2` file's `type:` values are **references** into `.ros` specs; the `.ros2` never defines them.

**A package that both defines and consumes its own types needs both files.** The table above reads
as if the three tasks were disjoint; they are not. Whenever any `type:` reference's package prefix
equals the `.ros2`'s own package name — `turtlesim` publishing `'turtlesim/msg/Color'` and serving
`'turtlesim/srv/Spawn'` — a companion `.ros` in the same model project is **required**, or
`CheckMsgsRefPublisher` warns on every such interface. Emit it without being asked.

### Output layout

Mirror the layout both corpora use, because `from:` cross-references resolve through the Xtext
workspace and not through relative paths:

```
<project>/
  msgs/<package>.ros            type definitions
  rosnodes/<package>.ros2       one file per package, named after the DECLARED package name
  <system>.rossystem            beside rosnodes/, not inside it
```

Name each `.ros2` after the package name it declares on line 1, not after the node. (76 of 253
corpus files violate this; do not copy them — but always *read* the package name from the model, per
rule 10.) Whether cross-file linking is directory-scoped or workspace-scoped is **unverified** —
`RosSystemScopeProvider` is an empty class, so stock Xtext scoping applies, and this cannot be
confirmed without a running language server.

---

## Hard rules, ranked by how often an LLM breaks them

### 1. Quoting discipline (the #1 failure)

`EString returns ecore::EString: STRING | ID;` — Basics.xtext:391.
`ID` admits `[a-zA-Z_][a-zA-Z0-9_]*` only. So **any name containing `.`, `/`, `::`, `-`, a space,
or that is empty MUST be double- or single-quoted**, or it is a parse error.

Emit quotes as follows:

| Position | Quote | Why |
|---|---|---|
| `.ros2` interface name, parameter name, `type:` **message ref** | `'single'`, always — even when bare would parse | removes a per-name decision |
| `.ros2` parameter `value:` string, `fromGitRepo:` | `"double"` | it is data, not a reference |
| every quoted token in `.rossystem` (`from:`, arrow target, interface label, param ref, `fromFile:`) | `"double"`, always | Corpus B is 100% double there |
| `.ros2` package name (col 0), artifact name, `node:` name | **NEVER quoted** | `RosNames` has no `STRING` alternative |
| parameter **type keywords** (`Boolean`, `String`, `Double`, `Integer`, `Array[String]`) | **NEVER quoted** | they are grammar keywords; quoting one is a parse error |

```
RosNames returns ecore::EString:
    ROS_CONVENTION_A | ID | 'node'          # Basics.xtext:394-396 — no STRING branch
```

Corpus: 253/253 package names bare, 267/267 `node:` names bare, 0 quoted.

### 2. Lowercase package names — the only naming ERROR

`checkNameConventionsPackage` calls `error(...)`, not `warning(...)`. Any uppercase character in a
`.ros2` root package name is an **ERROR**, and the loop does not short-circuit, so `MyPkg` yields
two errors.

- Package name (`.ros2` line 1): `[a-z0-9_]` **only**. MUST.
- Node and artifact names: lowercase preferred, but uppercase is only a WARNING — **do not mangle an
  upstream name to satisfy it.** `gazebo_sensor_B1_controller` is a real, correct artifact name.
- Parameter names: uppercase warns only if the remainder of the name contains no `.`. So `Foo.bar`
  is clean; `foo.Bar` warns.

This produces a deliberate asymmetry inside one file — lowercase package, original-case artifact:

```
gazebo_sensor_b1_controller:
  artifacts:
    gazebo_sensor_B1_controller:
      node: gazebo_sensor_B1_controller
```

### 2a. Package, artifact and node are three distinct names — all three matter for launch generation

Confirmed directly by the plugin maintainer (review of `examples/turtlebot3_navigation.rossystem`,
2026-08-13), matching the same three-tier shape already established by rule 4b/`RosQNP.xtend`:

```yaml
planner_server:            # the ROS 2 package name
  artifacts:
    planner_server:         # the executable to run
      node: planner_server  # the name given to the node, visible to rosgraph
```

These are frequently the same string (as above), but they answer different questions and are
**not interchangeable placeholders for each other** — never collapse them because they happen to
match in a given package. Getting the wrong one into the wrong DSL position is exactly what rules
4b, 6, and the RM014/RM056/RM062 lint checks exist to catch: `rossdl_cmake` (the actual launch-file
generator this composition feeds) derives the node's runtime class from `from:`'s **node** segment
and keys its remapping table on the **artifact**'s bare name, so confusing package ↔ artifact ↔
node produces a `.rossystem` that lints and validates clean but generates a broken launch file —
a defect this plugin cannot detect on its own, since it never runs `rossdl_cmake` itself.

### 3. Indentation

Spaces only, **exactly 2 per level**, LF endings, one trailing newline, no tabs, no trailing
whitespace, no blank lines inside an indented block. The corpus is inconsistent (26/51 `.rossystem`
files contain tabs) — **do not imitate it.** Emit the normalised form.

### 4. Connection direction and type identity (`.rossystem`)

`from` is **always** the server/publisher side. Only three pairings are legal:

| `from` | `to` |
|---|---|
| `pub->` | `sub->` |
| `ss->` | `sc->` |
| `as->` | `ac->` |

`MatchPortMsgs` additionally compares with Xtend `!==` — **object identity**, not name equality.
Both endpoints must resolve to the *same* spec object, so emit byte-identical `type:` strings on
both ends.

Use only the `RosSystemConnection` form, `- [from_label , to_label]`, referencing interface **labels
declared in the same file**. The `RosConnection` alternative triggers a `ClassCastException` in
three separate validator methods.

**Never synthesise a `connections:` block that the source did not declare.** When transcribing an
existing system that has no `connections:`, emit none — even when pub/sub pairs look obvious.
`MatchPortMsgs` requires *object identity* on the type, which cannot be confirmed without resolving
every referenced `.ros2`, so an invented connection is an unverifiable claim that may hard-error.
Instead, list the candidate label pairs in your response and let the caller decide. (`MT.rossystem`
has 32 nodes and several obvious pairings — such as `relay`/`controller_server` on
`kmriiwa/base/command/cmd_vel` — and declares zero connections. Leave it that way.)

### 4b. `from:` is `package.NODE`; arrow targets are `artifact::interface`

Inside a single `.rossystem`, references into a `.ros2` use **two different naming schemes**. Get
this backwards and the reference silently fails to link.

| Position | Form | Level skipped |
|---|---|---|
| `from:` | `"<package>.<node>"` | the **artifact** |
| `pub->` `sub->` `ss->` `sc->` `as->` `ac->` target | `"<artifact>::<interface>"` | the **package** |
| node-level parameter target | `"<artifact>::<parameter>"` | the **package** |

Not a convention — it is what `RosQNP.xtend` computes. For a `Node` it returns
`pkg.name + "." + node_name` from `obj.eContainer.eContainer as Package`; for a `Publisher` (and the
other five kinds, and `Parameter`) it returns `art.name + "::" + interface.name` from
`obj.eContainer.eContainer as Artifact`. Same expression, different class, opposite level.

Worked example — `MANI01_UR/pick_and_place.ros2` is the one corpus file where all three names
differ:

```
moveit2_scripts:                                 package
  artifacts:
    pick_and_place:                              artifact
      node: simple_pick_and_place_applictation   node
      publishers:
        attached_collision_object: ...           interface
```

```
from:  "moveit2_scripts.simple_pick_and_place_applictation"   ✅ package.NODE
from:  "moveit2_scripts.pick_and_place"                       ❌ package.artifact — does not link
arrow: "pick_and_place::attached_collision_object"            ✅ ARTIFACT::interface
arrow: "simple_pick_and_place_applictation::attached_..."     ❌ node::interface
```

Almost every corpus file has `artifact == node`, so it never notices. **When they differ, say which
one you used in your response.** Detail: `references/rossystem-syntax.md` §3.

### 5. `fromFile:` — always emit it, always with a `/`

`fromFileHelper` dereferences `system.fromFile` **twice with no null guard**, and the field defaults
to `null` when omitted. Omitting `fromFile:` is corpus-normal and trips the bug. `fromFile: ""` also
errors. The only input that traverses the method cleanly:

```
fromFile: "my_pkg/launch/bringup.launch.py"
```

**This is the one field where the skill knowingly supplies data the source does not contain**, so
it needs a derivation ladder rather than a guess. 32 of 52 corpus models omit `fromFile:`, so
"no launch file is known" is the *common* case, not the edge case:

1. The caller named a launch file → use it verbatim.
2. `<pkg>/launch/<system>.launch.py` exists on disk (check with `Glob`) → use the real path.
3. Otherwise → `fromFile: "TODO_PACKAGE/launch/TODO.launch.py"`.

The sentinel satisfies the `contains("/")` check while staying obviously a placeholder. **Never
invent a plausible-looking real path** — a fabricated `"cs4mt_bringup/launch/manufacturing_tb.launch.py"`
is indistinguishable from a verified one and silently converts a known-unknown into a false fact.

On rungs 2 and 3, report the value to the caller as **SYNTHESISED — not extracted from the source,
supplied only to avoid the `fromFileHelper` NPE**. The linter flags the sentinel as `RM066` (INFO)
so it stays visible.

### 6. Node names: never quoted, restricted charset

`node:` takes `RosNames`, so it can never be quoted and can never contain `.`, `-`, `::`, or a
space. Leading/trailing slashes *are* legal (`ROS_CONVENTION_A: ( ('/' ID) | (ID '/') )*`) and are
attested in the corpus (`/light_controller`, `/cam_ns/cam_frame_controller`) — but prefer a plain
`ID`. See the correction note in `references/ros2-syntax.md`.

### 7. QoS durations — quoted 32-bit ints (moot under the pinned profile)

If `lease_duration:` / `lifespan:` / `deadline:` are ever unpinned, each value must be a **quoted**
digit string parseable by `Integer.parseInt` (max `2147483647` ns ≈ 2.1 s — `"5000000000"` is an
ERROR) or the bare keyword `infinite`. Under the current profile you never emit these fields at all
(§ below), so this rule is documentation for a future oracle rebuild, not something to implement.

### 8. Silent-corruption traps in parameter values

- Booleans: **lowercase only**. `terminal BOOLEAN: 'true'|'false'`. `True` does not error — it falls
  through the `ParameterValue` alternation into `ParameterString`, so a `type: Boolean` parameter
  silently holds a *string*. No validator catches it. 910 corpus occurrences are latently corrupt.
- Doubles: **must carry a `.` or exponent**. `value: 10` under `type: Double` silently becomes a
  `ParameterInteger`. Emit `10.0`.
- Never emit an empty name `'':`.

### 8b. `.ros` message bodies — emit the FIELDS, not just the type name

A `.ros` spec is not just a list of type names. `MessageDefinition` expands, and dropping the
fields silently destroys the entire content of the file. This is the single largest information
loss this skill has produced: an adversarial test asked for `Pose` and got a bare `message` line,
losing all five of `float32 x`, `y`, `theta`, `linear_velocity`, `angular_velocity`.

**A field is two bare tokens — type, then name — four indent levels deep:**

```
turtlesim:              level 0   package
  msgs:                 level 1   block keyword
    Pose                level 2   spec name — NO trailing ':'
      message           level 3   body keyword
        float32 x       level 4   FIELD  (column 8)
        float32 y
        float32 theta
```

`srvs:` uses `request` / `response` at level 3, `actions:` uses `goal` / `result` / `feedback`.
The spec name at level 2 is the only named element in the language with no trailing `:`.

Two things a `.ros` allows that a `.ros2` does not: the root is `PackageSet`, so **one file may
declare several packages** at column 0; and `MessagePart*` has no line separator, so **several
fields may share a line**. Emit one package per file and one field per line anyway — but never
flag either as an error when reading a source file.

| Form | Write | Not |
|---|---|---|
| scalar | `float32 x` | — |
| array | `float32[] xs` | `float32[3] xs` — **no bounded arrays exist**, it is a lexer error |
| `time` / `duration` / `Header` | `time stamp` | `time[] stamps` — these three have **no array form** |
| ref to any spec, incl. **own package** | `"pkg/msg/Type" field` | `Type field` — bare short names never resolve |
| array of refs | `"pkg/msg/Type"[] fields` | — |
| constant | `uint8 FAN_OFF=0` | `uint8 FAN_OFF = 0` — spaces split the token |

Legal scalar keywords: `bool` `int8` `uint8` `int16` `uint16` `int32` `uint32` `int64` `uint64`
`float32` `float64` `string` `byte` `char` `time` `duration` `Header`. Arrays are the same list
minus `time`/`duration`/`Header`, with `[]` appended. Field names may be grammar keywords
(`string name`, `int32 type`) and are never quoted.

**Emit the fields whenever the input supplies them.** An empty body is grammatically legal — a
bodiless `message`, or a `response` with no fields, is a correct transcription when the source
genuinely has none. But falling back to it because you did not know the syntax is data loss, and
if you ever do emit a bodiless spec you must say so: *"message bodies omitted — field definitions
were not available in the input."*

Full type table, the verbatim productions and a validated end-to-end example:
`references/ros2-syntax.md` §11.

### 8c. Resolve every `type:` and `from:`/arrow reference against the vendored catalogues

Two real catalogues are vendored into this plugin — `assets/roscommonobjects/` (message/
service/action **type** specs, indexed in `assets/type_index.json`) and
`assets/rosmodelscatalog/` (standard package **node** models, indexed in
`assets/node_index.json`). Browsable tables: `references/type-catalogue.md`,
`references/node-catalogue.md`.

**Before emitting any `type:` reference**, resolve it against `assets/type_index.json`. If it
resolves, use the catalogue's exact spelling (package name, kind, and Type all come from a real,
oracle-shaped source, not memory). If it does not resolve, one of two things is true: the package
is genuinely project-local — emit a companion `.ros` defining it — or the reference was invented
and must not be emitted. `rosmodel_lint.py`'s RM081 (WARNING, package not indexed at all — a
project-local package is legitimate) and RM082 (ERROR, package indexed but this type isn't —
this is a real typo, not a plausible gap) enforce this at lint time and suggest the nearest match.

**Before emitting any `.rossystem` `from:` or arrow/parameter target**, resolve it the same way
against `assets/node_index.json`. This is exactly the mistake that shipped in an earlier
revision of `examples/turtlebot2_navigation.rossystem`: `nav2_amcl.amcl`, `nav2_bt_navigator.
bt_navigator`, `nav2_planner.planner_server` and `nav2_controller.controller_server` were all
invented from general Nav2 knowledge with a plausible `nav2_`-style prefix — the real catalogue
names are `amcl.amcl`, `bt_navigator.bt_navigator`, `planner_server.planner_server`,
`controller_server.controller_server`, no prefix. `rosmodel_lint.py`'s RM084 (WARNING, `from:`
package not indexed — project-local nodes are legitimate), RM085 (ERROR, package indexed but node
name isn't) and RM086 (ERROR, arrow/parameter target resolves to a catalogued node but that
interface name isn't among its real interfaces) enforce this the same way.

**TurtleBot 2 / Kobuki is not in `assets/rosmodelscatalog/` at all** — only TurtleBot 3 is. A
reference to a Kobuki-specific package will always miss the catalogue; that is a known scope
limit of the vendored catalogue, not a defect to fix by guessing a plausible package name for it.

Once a reference resolves, `rosmodel_lint.py` reports which vendored file supplies it (RM083 for
types, RM087 for nodes) — pass the model straight to `scripts/collect_deps.py <file>... <dir>` to
stage exactly those files into an oracle case directory, instead of hand-copying `_deps/` files
and guessing which ones apply.

**Disclose the resolved file inline, on the same line as the reference — not only in a header
comment.** A reader looking at one `"from:"` line should not have to run the linter, open
`assets/node_index.json`, or scroll to a file-level summary comment to find out which real file
backs it. This matters concretely: a `.rossystem` can reference nine nodes where seven resolve to
pre-existing catalogue files nobody in this session wrote, and two resolve to files freshly
authored for this model — from the reference alone those two cases are visually indistinguishable
unless each line says which one it is. Add a trailing comment naming the exact vendored path:

```
"amcl":
  from: "amcl.amcl" # assets/rosmodelscatalog/navigation/amcl.ros2
```

For a project-local node with no catalogue entry, say so instead, e.g. `# project-local, see
rosnodes/turtlebot3_mission_manager.ros2` — the point is that every `from:` line states in-place
whether it points at a real vendored file (and which one) or a companion file this session wrote.
`rosmodel_lint.py`'s RM088 (node `from:`) and RM089 (`type:` refs) check this mechanically: they
fire a WARNING when a reference resolves against the catalogue but the source line's text doesn't
contain the resolved file's name.

### 8d. Reuse a whole catalogued system via `subSystems:` — but only when it actually exposes ports

`from:` names *one node's* real implementation. To reuse a whole pre-built `.rossystem`
composition — not re-derive it node by node — use the system-level `subSystems:` block instead:

```
subSystems:
  "turtlebot"
```

**Not a bracket list.** The grammar production is `components+=SubSystem*`, a repetition, not
`Process.nodes`'s `[...]` form — one bare (quote it anyway, per §8) system name per indented line,
no leading `-`. `subSystems: ["turtlebot"]` is a parse error.

**Before adding a `subSystems:` entry, check what it actually exposes.** A subsystem's
connectable ports are *exactly* what its own `nodes:` block declares under `interfaces:` — **never**
derived from the `.ros2` file its `from:` points at (confirmed directly against
`RosSystemValidator.xtend`'s `checkIfInterfaceInSystem`, which walks one level into a referenced
system's components and reads `rosnode.rosinterfaces` — populated only from that file's own
`interfaces:` blocks). Two real catalogued examples show both outcomes:

- `assets/rosmodelscatalog/robots/turtlebot3/robot/turtlebot.rossystem` declares real
  `interfaces:` on all three of its nodes (`cmd_vel`, `tf`, `odom`, `scan`, `joint_states`,
  `tf_static`) — genuinely reusable. Referencing it exposes those bare labels directly as
  `connections:` endpoints (confirmed against the real oracle — no re-suffixing, no artifact
  prefix, just the subsystem's own label text).
- `assets/rosmodelscatalog/robots/turtlebot3/turtlebot3_navigation2.rossystem` (the Nav2 stack)
  declares **zero** `interfaces:` on any of its 14 nodes. Referencing it via `subSystems:` is
  grammatically valid and resolves, but exposes nothing — none of its nodes can be a
  `connections:` endpoint through it. If a node from a subsystem like this needs external
  wiring, **keep it as an explicit `nodes:` declaration in this file instead**, and say why in a
  comment so a future pass doesn't "simplify" it into a broken `subSystems:` reference. This is
  not a failure to reuse — the reference genuinely offers nothing to reuse.

`assets/node_index.json`'s `_systems` entries (built by `build_node_index.py`) record each
catalogued system's nodes and their declared interfaces, so this is checkable before authoring
anything: an entry with every node's `"interfaces": {}` is the zero-exposure case above.

**Never let one real node be reachable two ways in the same file** — directly under this file's
own `nodes:` **and** through a `subSystems:` entry that also provides it. Two distinct `RosNode`
objects then answer to the same label, which is the concrete shape of "duplicate model
definitions confusing the validator." `rosmodel_lint.py`'s RM090 (ERROR) catches the exact-label
collision; RM092 (WARNING) catches the softer case of the same `from:` reachable under two
different labels. RM091 (WARNING) covers a `subSystems:` entry that doesn't resolve at all, nests
another `subSystems:` block (two levels deep throws `ClassCastException` in the real validator —
keep nesting flat), or resolves but exposes zero interfaces, as above.

### 9. Ordering (grammar-fixed — violating is a parse error)

| Rule | Mandatory order |
|---|---|
| `AmentPackage` | `fromGitRepo:` → `artifacts:` → `dependencies:` |
| `.ros2` interface | `type:` → `ns:` → `qos:` |
| `.ros2` parameter | `type:` → **`default:`** → `ns:` → `value:` → `qos:` |
| `.rossystem` node | `from:` → `namespace:` → `interfaces:` → `parameters:` |
| `.rossystem` **system-level** parameter | `ns:` → `type:` → `default:` → `value:` (no `qos:`) |

`default:` belongs to `ParameterType`, not to `Parameter`, and is legal on **every** scalar type —
not only on `Array[T]`. It has no `BEGIN`/`END` of its own, so it sits as a sibling of `type:`
immediately after it. **`default:` and `value:` are different slots and are never interchangeable**
— preserve whichever the input uses. See `references/ros2-syntax.md` §6.

The two `parameters:` shapes in a `.rossystem` are different rules and are easy to confuse — the
node-level one is a **list** (`- "name": "node::param"` + `value:`), the system-level one is a
**mapping** with a `type:`. See `references/rossystem-syntax.md` §5 and §5b.

Convention (grammar permits any order): node blocks go `publishers` → `subscribers` →
`serviceservers` → `serviceclients` → `actionservers` → `actionclients` → `parameters`; interface
labels unique within a node (`sub_clock` when `clock` is already taken by a publisher).

**Sorting is scoped per file type — it is not a blanket rule:**

| Block | Order |
|---|---|
| `.ros2` interface entries, parameter entries, `artifacts:` | **sort alphabetically** |
| `.rossystem` interface labels within a node | **sort alphabetically**, grouped by kind |
| `.rossystem` `nodes:` | **preserve source order** — it often encodes bring-up sequence |

`rosmodel_lint.py` matches this split: `RM040` fires on unsorted `.ros2` blocks and deliberately
does **not** fire on a `.rossystem` `nodes:` block.

---

## Pinned-oracle exclusion

**Updated 2026-07-21 — this restriction has been lifted.** It previously said *never emit* the four
newer QoS fields, because our only validator was a JAR built 2024-08-01, predating them. We rebuilt
the language server from current source, so `lease_duration:`, `liveliness:`, `lifespan:` and
`deadline:` now parse and validate correctly.

**Prefer the five long-standing fields anyway** — `profile:`, `history:`, `depth:`, `reliability:`,
`durability:`. Emit one of the four newer fields only when the input specifically calls for it.
Two reasons: no corpus model uses them, and anyone consuming your output on an older toolchain
build cannot lex the keyword — it fails as a **syntax error that invalidates the whole publisher**,
not as a warning.

**If you do emit a duration** (`lease_duration:`, `lifespan:`, `deadline:`), the value is in
**nanoseconds** and must fit a signed 32-bit int — max ≈ **2.147 seconds** — or be the literal
`infinite`. `deadline: "5000000000"` (5 s) is a validator ERROR. This is the easiest QoS mistake to
make, because every realistic timeout exceeds the limit.

The complete emittable QoS vocabulary:

```
qos:
  profile:     default_qos | services_qos | sensor_qos | parameter_qos
  history:     keep_last | keep_all
  depth:       <bare integer>
  reliability: best_effort | reliable
  durability:  transient_local | volatile
```

Default to **`reliability:` and `durability:` only** — the only two Corpus B uses. Emit
`profile:` / `history:` / `depth:` solely when the caller supplies a concrete value.

Cost of the exclusion is zero: **0 of 253** corpus `.ros2` files use any of the four fields.
Because the JAR's token set is a strict subset of HEAD's, output valid under this profile is also
valid at HEAD.

Also never emit: `Any`, `ParameterAny`, `Date` (defined but not members of the `ParameterType` /
`ParameterValue` alternations — unreachable), or nested `Struct` **values**.

---

## Self-check before finishing

Run every line against the emitted file:

1. Line 1 package name: lowercase `[a-z0-9_]`, **unquoted**, ends with `:`.
2. No tabs. Every indent is a multiple of 2. LF endings. Exactly one trailing newline.
3. Every `.ros2` interface/parameter name is `'single-quoted'`; every `type:` message ref is
   `'single-quoted'` and contains `/`.
4. Every parameter type keyword is bare. Every string `value:` is `"double-quoted"`.
5. No `msgs:` / `srvs:` / `actions:` in a `.ros2` file.
6. No `lease_duration` / `liveliness` / `lifespan` / `deadline` anywhere.
7. Booleans lowercase; every `.ros2` `Double` value has a `.` or exponent. (In a `.rossystem` the
   declared type is not visible — preserve the source literal instead.)
8. Block order matches §9. `.ros2` entries alphabetical; `.rossystem` `nodes:` in **source order**.
   Any `default:` in the input is still a `default:` in the output, never rewritten to `value:`.
9. `.rossystem` only: `fromFile:` present, quoted, contains `/`. Every connection is
   `- [a , b]` where `a` is a `pub->`/`ss->`/`as->` label and `b` is the matching
   `sub->`/`sc->`/`ac->` label. Both `type:` strings identical. Every label declared in this file.
   Every node in a process's `nodes: [...]` declared in `nodes:`.
10. `from:` in `.rossystem` is `<packageName>.<nodeName>` — **the node, never the artifact** — read
    from the **model contents**, never from the `.ros2` filename (76/253 files have a stem that
    differs from the declared package; `bt_navigator.ros2` declares `nav2_bt_navigator`). In the
    same file the arrow targets are `<artifactName>::<interfaceName>`. Two different schemes; see
    rule 4b.
11. `.ros` only: every spec that has fields in the input **has those fields in the output**, two
    bare tokens per line at indent level 4, spec name at level 2 with no trailing `:`. No bounded
    arrays. Every spec reference — including one into the file's own package — is a quoted
    `"pkg/msg/Type"`. Constants have no spaces around `=`. See §8b.
12. **Report what you dropped or synthesised.** Before finishing, tell the caller about: every
    comment removed from a transcribed source (file, line, text — *DROPPED PROVENANCE*); any
    `fromFile:` from rung 2 or 3 of the ladder (*SYNTHESISED*); any `.ros` message body emitted
    bodiless; any duplicate node label collapsed or renamed; any source defect preserved verbatim.
    Silence about these is the failure mode — none of them is visible to the linter or the harness.
13. Every `type:` reference resolves against `assets/type_index.json`, and every `.rossystem`
    `from:`/arrow/parameter target resolves against `assets/node_index.json` — or is a genuine,
    disclosed project-local reference with its own companion `.ros`/`.ros2`. See §8c.
14. Every resolved `type:`/`from:` reference names its exact vendored source file in a trailing
    comment on the same line (`# assets/rosmodelscatalog/navigation/amcl.ros2`), and every
    project-local one says so and points at its companion file instead. See §8c.
15. Every `subSystems:` entry is the bare-per-line form, never `[...]`. Before emitting one,
    confirmed via `assets/node_index.json`'s `_systems` entries that the target actually declares
    `interfaces:` on the node(s) you need — if it declares none, an explicit `nodes:` entry is the
    correct choice, not a broken `subSystems:` reference. No node is reachable both directly under
    this file's `nodes:` and through a `subSystems:` entry. See §8d.

## Validation

- **Static linter** (always available): `${CLAUDE_PLUGIN_ROOT}/scripts/rosmodel_lint.py`. Checks
  everything above that is decidable in one file.

  ```
  python scripts/rosmodel_lint.py <file>...
  ```

  On Windows under the Bash tool, bare `python` is the Microsoft Store stub and exits non-zero —
  use `py -3` there. Accepts **`.ros`, `.ros2` and `.rossystem`**. (`.ros` support was added
  2026-07-21; older notes saying `.ros` is rejected with `RM000` are stale.) The `.ros` branch does
  not use YAML — it runs its own indentation-stack parser, so it reads message field lines
  correctly and never rejects a file merely for irregular indentation.

  **`RM034` (`profile:` / `history:` / `depth:` used) is expected and correct when the value came
  from the input.** It warns against *inventing* those fields, not against transcribing them.
  Never drop a concrete value that was present in the source in order to get a clean linter run.

  **RM081-092 are the catalogue checks** (§8c, §8d) — RM081/084 (WARNING: reference not indexed
  at all, a project-local package/node is legitimate) and RM082/085/086 (ERROR: the package/node
  *is* indexed but this specific type/node/interface name isn't — a real typo, with a
  suggested nearest match) run automatically whenever `assets/type_index.json` /
  `assets/node_index.json` exist. Pass `--no-catalogue` to suppress them in a workspace whose
  references are heavily project-local. RM083/RM087 name exactly which vendored file a
  resolved reference needs — feed the model straight to `scripts/collect_deps.py <file>...
  <case-dir>` instead of hand-copying `_deps/` files (this also stages any resolved
  `subSystems:` target and follows its own references transitively). RM088/RM089 (WARNING) fire
  when a reference resolves against the catalogue but its source line doesn't name the resolved
  file — add the trailing comment they suggest. RM090 (ERROR)/RM091/RM092 (WARNING) are the
  `subSystems:` reuse checks from §8d: a node reachable both directly and through a subsystem, an
  unresolved/nested/zero-interface subsystem reference, and a same-`from:`-different-label pair.
  RM093 is a separate, non-catalogue grammar check (`--no-catalogue` does not suppress it): ERROR
  on the bracket-list form `subSystems: [...]`, which is never valid (`components+=SubSystem*` is
  a repetition, not a list production — see §8d); WARNING on a multi-entry `- item` block sequence,
  which parses but has not been verified against the real oracle for more than one entry.

- **Round-trip harness**: `tests/roundtrip.py`, which compares two models semantically rather than
  byte-wise (corpus formatting is far too inconsistent for byte-diffing to mean anything).

  ```
  python tests/roundtrip.py compare <original> <regenerated>
  ```

  The `compare` subcommand is **required** — `roundtrip.py <a> <b>` is an argparse error.
  `compare` exits 1 on any semantic difference, including the deviations this skill *mandates*
  (an added `fromFile:`, a renamed duplicate node label). Read the diff; a non-zero exit is not by
  itself a failure.
- **Real oracle — available, use it.** Java 21 is installed and
  `tests/oracle/ask_oracle.py` drives the actual RosTooling language servers over stdio:

  ```
  py tests/oracle/ask_oracle.py <case-dir>      # one directory = one LSP workspace
  py tests/oracle/ask_oracle.py --all           # the whole regression suite
  ```

  Put the file under test in a directory together with every `.ros` it depends on, and read the
  verdict. `ACCEPTED` with 0 errors is the only passing result.

  **The shipped `ros2` JAR registers `RosIdeSetup` and `BasicsIdeSetup` as well as `Ros2IdeSetup`,
  so it validates `.ros` files too** — not just `.ros2`. A `.rossystem` server has now been built
  locally as well (`build/rossystem-ls/`), so all three file types have an oracle.

  **A `.ros2` is only clean when every `type:` it references resolves.** Unresolved references are
  **ERRORs** (they fail in Xtext's linking layer, before the validator runs), not warnings.
  Validating one file in isolation will always show errors — always supply the `.ros` dependencies.

- **The oracle is pinned to a 2024-08-01 build**, so it validates a 2024 language and can say
  nothing about the four HEAD-only QoS fields except that it does not know them. That is exactly
  why they are excluded above.

- **When the linter and the oracle disagree, the oracle wins.** The linter is a reimplementation;
  the oracle is the toolchain. Report a file as validated only if you actually ran it.

Full detail on demand: `references/ros2-syntax.md`, `references/rossystem-syntax.md`,
`references/worked-examples.md`.
