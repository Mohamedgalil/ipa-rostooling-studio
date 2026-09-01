# rostooling-modeler

A Claude Code plugin that lets an AI agent generate and check **RosTooling** model files — `.ros2`
(an `AmentPackage`: one ROS 2 package, its artifacts, nodes and interfaces), `.rossystem` (a system
composition wiring node instances together) and `.ros` (message / service / action type
definitions) — for the Fraunhofer IPA ROS 2 modelling toolchain.

Work item **E1**, CoreSense x Humanoid.

The problem it solves: these are **indentation-sensitive Xtext DSLs that look like YAML and are
not**. Indentation is lexed into mandatory `BEGIN`/`END` tokens, `EString` positions must be quoted
while `RosNames` positions must never be, and several constructs corrupt the model *silently*
rather than failing loudly (`value: True` under `type: Boolean` parses as a string; `value: 10`
under `type: Double` parses as an integer). An agent reasoning from YAML or general ROS intuition
gets these wrong every time. The plugin replaces intuition with a transcribed grammar subset, a
validator rule table and an enforced emission profile.

---

## Prerequisites — read this first

| Requirement | Needed for | Status on this machine |
|---|---|---|
| **Python 3.8+** | linter, round-trip harness | ✅ 3.12.6 |
| PyYAML | structural checks (linter degrades gracefully without it) | ✅ 6.0.3 |
| **Java 21 (Temurin LTS)** | LSP validation of `.ros` / `.ros2` / `.rossystem` | ✅ Temurin 21.0.11 |

### ✅ There is a working oracle — use it

`tests/oracle/ask_oracle.py` drives the real RosTooling language servers over stdio and reports
their diagnostics. All 25 cases<!--@count:oracle_cases--> currently behave as documented; the
rejections are negative controls that confirm the hard exclusions, plus three that settled the
`from:` reference form. The per-case verdicts live with the runs that produced them, in
[`tests/oracle/RESULTS.md`](tests/oracle/RESULTS.md).

```bash
py tests/oracle/ask_oracle.py --all
```

Two things worth knowing:

- **The shipped `ros2` JAR validates `.ros` files too.** It registers `RosIdeSetup` and
  `BasicsIdeSetup` alongside `Ros2IdeSetup`, so message specs get real diagnostics, not just
  packages.
- **`.rossystem` has no *shipped* server, but one has been built from source** at
  `build/rossystem-ls/`, and `ask_oracle.py` selects it per case by file extension. Ten case
  directories now carry a `.rossystem` and have been through it — the 52 corpus systems still
  have not.

One limit that no JDK lifts:

- **The oracle is stale.** The shipped `ros2` JAR was built **2024-08-01**; RosTooling HEAD added
  `lease_duration` / `liveliness` / `lifespan` / `deadline` on 2025-10-16, *after* that build, so
  the JAR cannot even lex them. The project deliberately **pins the emission profile to the
  JAR-accepted subset** and never emits those four fields. Cost of the exclusion is zero — 0 of 253
  corpus `.ros2` files use any of them — and because the JAR's token set is a strict subset of
  HEAD's, output valid under the pinned profile is also valid at HEAD.

---

## Installing

The plugin is self-hosting: its repo is also a Claude Code marketplace
(`.claude-plugin/marketplace.json`), so `/plugin install` works directly.

**Persistent install** (survives across sessions):

```bash
# add this repo as a marketplace (local path, git URL, or GitHub owner/repo all work)
claude plugin marketplace add C:/Users/mae/Downloads/adm-mae/CoreSense/rostooling-plugin
claude plugin install rostooling-modeler@rostooling-modeler-marketplace
```

**Single-session dev load** (no marketplace, no install):

```bash
claude --plugin-dir C:/Users/mae/Downloads/adm-mae/CoreSense/rostooling-plugin
```

Validate the manifest at any time:

```bash
claude plugin validate C:/Users/mae/Downloads/adm-mae/CoreSense/rostooling-plugin
```

### Two environment variables you must set

The plugin bundles its own language-server JAR (`build/ros2-ls/target/…-ls.jar`, referenced via
`${CLAUDE_PLUGIN_ROOT}` so it travels with the plugin) but it cannot bundle a JDK or a Python
interpreter. Both `.lsp.json` and `hooks/hooks.json` read an env var with a POSIX default, so on a
machine where the default resolves correctly you need to set nothing. On **this** machine both
defaults are wrong, so set both:

1. **`ROSMODEL_JAVA`** — the LSP command is `"${ROSMODEL_JAVA:-java}"`. Bare `java` on `PATH` here is
   1.8 and the JARs need JDK 19+, so the server would start under Java 8 and die. Point it at
   Temurin 21:

   ```
   ROSMODEL_JAVA=C:\Users\mae\AppData\Local\Programs\Eclipse Adoptium\jdk-21.0.11.10-hotspot\bin\java.exe
   ```

2. **`ROSMODEL_PYTHON`** — the hook command is `"${ROSMODEL_PYTHON:-python3}" .../rosmodel_lint.py`.
   Bare `python`/`python3` here is the Microsoft Store stub, which prints a "not found" notice and
   exits non-zero — the hook would then silently never lint. Point it at the real interpreter:

   ```
   ROSMODEL_PYTHON=C:\Users\mae\AppData\Local\Programs\Python\Python312\python.exe
   ```

On Linux/macOS the defaults (`java`, `python3`) are usually correct, provided `java -version`
reports 19+.

---

## Component layout

```
.claude-plugin/plugin.json      manifest
.lsp.json                       ros2 + ros language servers (auto-discovered at plugin root)
hooks/hooks.json                PostToolUse linter for .ros2 and .rossystem (auto-discovered)
commands/update-ros-catalog.md  slash command: refresh popular-ROS-packages reference (cheap agent)
commands/ros-plot.md            slash command: render .rossystem models as one interactive HTML file (read-only)
commands/ros-studio.md          slash command: interactive AUTHORING editor + deterministic generate/validate
agents/ros-modeler.md           subagent, preloads the ros-model skill
skills/ros-model/
  SKILL.md                      entry point: decision tree, hard rules, self-check
  references/ros2-syntax.md     .ros2 + .ros grammar, verbatim productions
  references/rossystem-syntax.md .rossystem grammar + RosSystemValidator behaviour
  references/worked-examples.md  3 full transformations, failure catalogue, source-defect policy
scripts/rosmodel_lint.py        static linter, 81 rules (.ros / .ros2 / .rossystem)
scripts/ros_plot.py             /ros-plot backend: .rossystem -> self-contained interactive HTML (read-only)
scripts/ros_studio.py           /ros-studio backend: init (seed) / render (editor HTML) / generate (+ lint, oracle)
scripts/_studio_common.py       shared HTML/CSS/JS primitives + emit vocabulary (imported by both ros_plot and ros_studio)
scripts/_studio_editor.py       the /ros-studio editor page as one raw-string template
scripts/README.md               rule reference + deviations + test evidence
tests/roundtrip.py              semantic round-trip harness
tests/studio_roundtrip.py       /ros-studio seed -> generate: round-trip, orphan gate, JS/Python parity
tests/studio_parity.js          the editor's .rossystem preview vs the Python emitter, byte for byte
tests/fixtures/manifest.md      fixture inventory
tests/regenerated/              adversarial regeneration outputs (4 corpus targets)
tests/oracle/ask_oracle.py      drives the REAL language servers; 25 cases
tests/oracle/RESULTS.md         what the toolchain actually said
tests/docs_check.py             holds the PROSE to the code: cited paths, rule ids, marked counts
emission-profile.md             NORMATIVE formatting profile, 37 numbered rules
docs/grammar-subset.md          what the pinned JAR can lex; the HEAD-vs-JAR token diff
research/validator-rules.md     transcription of both *Validator.xtend files, with severities
```

`plugin.json` deliberately declares no component path fields — `.lsp.json` at the root,
`hooks/hooks.json`, `agents/` and `skills/` are all discovered by default, and adding explicit
paths would only create a second place to keep in sync.

### Document precedence

When these disagree, resolve in this order:

1. **The grammar itself** — `RosTooling/plugins/.../{Basics,Ros,Ros2,RosSystem}.xtext` and the two
   `*Validator.xtend` files, in the read-only reference clone. Always the authority.
2. `docs/grammar-subset.md` — what the *pinned* oracle can lex, which is narrower than the grammar.
3. `research/validator-rules.md` — semantic constraints and their real severities.
4. `emission-profile.md` — normative style.
5. `skills/ros-model/**` — the operational restatement of all of the above.

> **Note on paths.** The E1 briefing located the three specs under `spec/`. There is no `spec/`
> directory; they are at `docs/grammar-subset.md`, `research/validator-rules.md` and
> `emission-profile.md` (plugin root). Anything hardcoding the briefing's paths will fail.

---

## Running the linter standalone

```bash
python scripts/rosmodel_lint.py <file>...
python scripts/rosmodel_lint.py --json <file>...
python scripts/rosmodel_lint.py --min-severity ERROR <file>...
python scripts/rosmodel_lint.py --quiet "corpus/**/*.ros2"     # summary line only
```

**On Windows use `py -3`, not `python`** (Store stub, see above). Globs are expanded internally, so
quoted `**` patterns work regardless of shell. Exit status is `1` if any ERROR survives
`--min-severity` filtering, else `0`.

Accepts **`.ros`, `.ros2` and `.rossystem`**. `.ros` support was added 2026-07-21; it does not go
through YAML (PyYAML folds message field lines into a single scalar and loses every field) but
through a dedicated indentation-stack parser.

Full rule reference, deliberate deviations from the specs, and test evidence:
[`scripts/README.md`](scripts/README.md).

## Running the round-trip harness standalone

The harness compares two models **semantically** — it parses both to a canonical fact set and diffs
that. Byte-diffing against corpus originals is meaningless here: 26 of 51 corpus `.rossystem` files
contain literal tabs, and indent widths of 3, 4, 5, 6 and 7 spaces all occur. The corpus is a
*semantic* reference, not a style reference.

```bash
python tests/roundtrip.py compare <original> <regenerated>
python tests/roundtrip.py selftest <fixture>...
python tests/roundtrip.py order <file>...
```

**The subcommand is required** — `roundtrip.py <a> <b>` is an argparse error.

`compare` exits `1` on *any* semantic difference, including deviations the skill deliberately
mandates (an added `fromFile:`, a renamed duplicate node label). **A non-zero exit is not by itself
a failure** — read the diff.

`selftest` runs four checks per fixture: identity, text perturbation (whitespace/quote-style
changes must not alter the fact set), order perturbation (block reordering must not either), and a
negative control (a planted semantic change *must* be detected).

## Running both together

```bash
py -3 scripts/rosmodel_lint.py out/my_pkg.ros2 out/my_system.rossystem
py -3 tests/roundtrip.py compare corpus/my_pkg.ros2 out/my_pkg.ros2
```

## /ros-studio — the authoring editor (supersedes /ros-plot for authoring)

`/ros-plot` **reads** a `.rossystem`; `/ros-studio` **builds** one. The editor is the same kind of
self-contained, no-network HTML page, but interactive: draggable nodes with kind-coloured ports, an
inspector, connection drawing with live legality, a node catalogue, offline autocomplete, and a
View ⇄ Edit toggle that also carries `/ros-plot`'s four read-only abstraction levels (System │
Interfaces │ Full │ Deps). `/ros-plot` is **not** removed — it stays as the lightweight read-only
path. Both share one primitives module (`scripts/_studio_common.py`: the palette + seven kind
colours, the SVG arrowhead marker, the bezier edge, pointer-capture drag, theme toggle, grid layout)
so the viewer and the editor can never drift.

The browser only authors an in-memory project; the Python companion owns generation and validation:

```bash
# seed a project.json from an existing system (interface types from the sibling .ros2, message
# fields from the sibling .ros, comments from the source text)
py scripts/ros_studio.py init path/to/system.rossystem --out project.json
# ...several sources, or a whole tree, merge into ONE project (ids re-issued, colliding node
# labels renamed, a subSystems: ref to a system also being merged collapsed onto it):
py scripts/ros_studio.py init path/to/models/ --out project.json --name combined
# ...or start blank:  py scripts/ros_studio.py init --out project.json

# render the editor (autocomplete data embedded; does NOT auto-open — add --open if you want it)
py scripts/ros_studio.py render project.json --out ros-studio.html

# author in the browser, hit Commit (downloads project.json), then generate + validate:
py scripts/ros_studio.py generate project.json --outdir generated            # emits + rosmodel_lint
py scripts/ros_studio.py generate project.json --outdir generated --oracle    # + real language server
```

Because Commit is a manual download, the page also holds the session itself: every mutating action
snapshots the project onto a 50-deep undo stack (Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y, with a burst of
keystrokes in one field coalesced into one entry), the project is autosaved to `localStorage` under
the system name, and closing the tab with work not yet committed asks first. A stored autosave is
never applied silently: on load the page names it, shows both it and the seeded project, and makes
you choose. `tests/studio_parity.js` (wired into `tests/studio_roundtrip.py`) keeps the editor's
`.rossystem`, `.ros2` and `.ros` previews byte-identical to the Python emitters by pulling the
shipped functions out of the *rendered* page and diffing. That last one matters because message
FIELDS are authored only in the page: a spec whose body silently comes back empty parses, lints
clean (RM080 is an INFO) and generates clean.

`generate` emits `.ros2` / `.rossystem` / companion `.ros` **deterministically** from the linter's
own grammar vocabulary (block names, arrow pairs, quoting), always runs `rosmodel_lint`, and with
`--oracle` stages catalogue dependencies (`collect_deps`) and asks the real server (`ask_oracle`). On
a lint ERROR it re-renders the editor with the diagnostics injected onto the offending nodes as
`<project>.error.html` and exits non-zero. The three autocomplete datasets come from
`assets/type_index.json` (message/service/action types), `assets/node_index.json` +
`references/popular-ros-packages.md` (package names) and `assets/node_index.json` (the node
catalogue); each is guarded, so a stripped install still runs (autocomplete just narrows).

---

## What the hook can and cannot do

`hooks/hooks.json` runs the linter on every `Write`/`Edit` of a `.ros`, `.ros2` or `.rossystem`
file.

`PostToolUse` fires *after* a tool call succeeds, and the capability table reads
`PostToolUse | No | Shows stderr to Claude; the tool already ran`. **The file is on disk by the time
the linter runs.** Returning `{"decision": "block", "reason": "..."}` does not undo the write — it
blocks further processing and forces a corrective edit. The invariant bought is *"no invalid model
survives the turn"*, not *"no invalid model is ever written"*.

Doing better needs `PreToolUse`, which *can* block — but it would have to lint `tool_input.content`
before the file exists, and for `Edit` it would have to apply the diff itself to know the post-edit
content. That is a real option worth taking later.

`matcher` filters on **tool name only** (`"Write|Edit"`); path narrowing is done by the separate
`if` field, whose syntax embeds the tool name (`Write(...)` / `Edit(...)`), so each tool needs its
own handler. Hence six handlers for three extensions.

**Plugin-shipped agents cannot declare hooks** (`hooks`, `mcpServers` and `permissionMode` are
unsupported there for security reasons), and whether a plugin's own hooks fire inside a subagent
context is not documented either way. **Verify before relying on it.** If they do not fire, the
subagent must call the linter itself, which means adding `Bash` back to its tool list — it is
currently restricted to `Read, Write, Edit, Glob, Grep, Skill`.

## Why `-cp` and not `-jar` in `.lsp.json`

The JAR ships two usable launchers, both confirmed by extracting and reading the class files:

- `de.fraunhofer.ipa.ros2.ide.launch.ServerLauncher` is the manifest `Main-Class` and is
  **socket-based** — its constant pool holds `java/net/InetSocketAddress`, `localhost` and
  `createSocketLauncher`, and a `sipush 5008` gives the port. Its `main(String[])` never reads
  `args`. So `java -jar <jar>` yields a server on `localhost:5008`: not stdio, not configurable.
- `org.eclipse.xtext.ide.server.ServerLauncher` is also present and is the stock Xtext **stdio**
  launcher (`-noValidate`, `-trace`, `-log`, `logStandardStreams` in its constant pool).

Claude Code's LSP transport defaults to `stdio`, and while `transport: "socket"` is documented, no
documented field carries a port. So `.lsp.json` bypasses `Main-Class` and names the stdio launcher
explicitly. **This is unverified** — the stock launcher discovers languages via `ISetup`
service-loader registration on the classpath, and the ros2 setup is bundled, so it *should* work,
but it has not been run. If it fails, `claude --debug` reports why; the fallback is to run the
socket launcher out of band and switch to `transport: "socket"`.

`.ros1` is deliberately not wired — a third JAR ships for it, but it is out of E1 scope.
`.rossystem` is not wired into `.lsp.json` because no server for it *ships*; the locally built one
is reached through `ask_oracle.py` instead.

---

## Status and honesty

See [`STATUS.md`](STATUS.md) for a blunt assessment: what is verified and how, what is built but
unverified and precisely why, what is not done, every open assumption with the person who must
answer it, and the effort reckoning against the 3 PD WBS budget.
