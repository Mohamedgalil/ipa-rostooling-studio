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
  the parts that a name alone cannot (`formatVersion: 2`):

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
- **`render project.json`** — emit the editor HTML (`ros-studio.html` next to the project by
  default; `--out PATH` to override). The three autocomplete datasets (message/service/action
  types, package names, node catalogue) are embedded so autocomplete works offline. Prints the
  HTML path. **Does not auto-open** — opening is opt-in via `--open`, and only when the user
  asked for it.
- **`generate project.json`** — deterministically emit `.ros2` / `.rossystem` / companion `.ros`
  into `generated/` (or `--outdir DIR`), then run `rosmodel_lint` over the result and report
  diagnostics **verbatim**. With `--oracle`, it stages catalogue dependencies (`collect_deps`)
  and asks the **real** language server (`tests/oracle/ask_oracle.py`, needs Java). On a
  generation/lint ERROR it re-renders the editor with the diagnostics injected onto the
  offending nodes, next to the project as `<project>.error.html`, and exits non-zero.

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
