---
description: Author RosTooling models in an interactive self-contained editor, then deterministically generate .ros2/.rossystem/.ros and validate them against the real language server, via scripts/ros_studio.py.
argument-hint: "init [file.rossystem] | render project.json [--open] | generate project.json [--oracle]"
allowed-tools: Bash, Read, Glob
---

## What this command does

`/ros-studio` is the authoring counterpart to `/ros-plot`. Where `/ros-plot` only *reads*
`.rossystem` models, `/ros-studio` lets you *build* them: a self-contained vanilla-JS editor
(draggable nodes, kind-coloured ports, an inspector, connection drawing, a node catalogue and
offline autocomplete) authors an in-memory project; a Python companion then generates the real
files and validates them. It supersedes `/ros-plot` for authoring, but `/ros-plot` remains the
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

The three subcommands form the authoring loop:

- **`init [FILE.rossystem]`** — build a `project.json`. With a `.rossystem` argument it seeds
  from it: the read-only extractor recovers the system structure and the sibling `.ros2` files
  are opened to recover each interface's type and the artifacts' parameters. With no argument it
  writes a blank project. Prints the `project.json` path.

  Seeding is **lossless** and `tests/studio_roundtrip.py` holds it to that: every node,
  exposure and connection in the source must reappear in `generate`'s output. Two fields carry
  the parts that a name alone cannot (`formatVersion: 3`):

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

  A subsystem's connectable interfaces are exactly what the referenced file's own `interfaces:`
  block declares, never what the `.ros2` behind its `from:` declares (`checkIfInterfaceInSystem`,
  RosSystemValidator.xtend:87-109). Two of its nodes may declare the same label (the catalogued
  turtlebot's `tf`); that ambiguity is the source file's, RM065 reports it, and the studio binds
  the first in sorted node order rather than inventing a distinguishing label that would resolve
  to nothing.
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

## What happens to comments

Round-tripping a model used to **delete every comment in it** — `generate` wrote only its own
`# assets/…` provenance lines. Comments are now captured by `init`, carried in `project.json`
(`formatVersion: 3`), editable in the editor, and re-emitted by `generate`. The policy below is
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
- `#foo` and `#  foo` both come back as `# foo`, and `##` loses one `#`;
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
the project model has no slot for: `processes:`, node-level `parameters:` in a `.rossystem`, the
inside of a `qos:` block, trailing comments on block keys (`nodes:`, `subSystems:`, `interfaces:`,
`qos:`, …), a comment block at end of file with nothing after it, and anything attached to an
element the project does not carry.

Every slot is editable: a **comments** section on the node and on the connection inspector, a
`cmt` chip beside `qos` on each interface and parameter, and the `.rossystem` file header, each
`subSystems:` entry and each package's `.ros2` header in the system panel (deselect everything to
reach it). A `subSystems:` node itself has no comment slots — it is declared in the referenced
file, and its comments live there. The
`.rossystem`/`.ros2` tabs under **Commit** preview the comments exactly as they will be written —
`tests/studio_parity.js` holds that preview to the Python emitter's bytes.

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
