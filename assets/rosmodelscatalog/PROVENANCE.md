# Provenance -- assets/rosmodelscatalog/

Vendored `.ros2` node/package models and `.rossystem` system compositions for standard,
commonly-used ROS 2 packages (Fraunhofer IPA's RosModelsCatalog).

- **Source**: `RosModelsCatalog` (Fraunhofer IPA)
- **Upstream remote**: unconfirmed. The local checkout's `.git/` has a real remote pack and
  `origin/HEAD` ref, but `git remote -v` / `git log` both fail with a Windows
  "detected dubious ownership" error (repo owned by a different local account than the one
  running these tools). Not bypassed -- `git config --global --add safe.directory` was
  deliberately not run. Re-run `git -C <path> remote -v` / `git log -1` yourself once ownership
  is resolved to fill this in.
- **Synced**: 2026-07-23, from a local checkout at `material/code/RosModelsCatalog`
- **License**: **unconfirmed**. No `LICENSE` file is present in the local checkout or this
  vendored copy.

## Structure

Straight copy of 9 subdirectories (56 files, `.ros2` node models + `.rossystem` compositions),
covering: `arms/` (UR), `cameras/`, `common/` (robot_state_publisher, tf2_ros, etc.),
`controllers/`, `lidar/`, `manipulation/`, `navigation/` (the Nav2 stack: `amcl`, `bt_navigator`,
`planner_server`, `controller_server`, costmaps, lifecycle managers, `waypoint_follower`, etc.),
`perception/`, and `robots/turtlebot3/` (a complete, real `turtlebot3_navigation2.rossystem` plus
base-platform and simulation compositions).

`assets/node_index.json` (built by `scripts/build_node_index.py`) indexes every `pkg.node` pair
declared across the vendored `.ros2` files, with each node's interfaces. `.rossystem` files found
here are recorded separately (under `_systems` in the index) as retrieval references, not indexed
for resolution -- they're compositions, not definitions.

**TurtleBot 2 / Kobuki is not represented anywhere in this catalog** -- only TurtleBot 3 is.
Any model referencing a Kobuki-specific package remains unresolvable against this catalog by
design, not oversight.

Skipped from vendoring: `.project`, `representations.aird`, `tools/haros_call.sh` -- Eclipse/tool
metadata, not model content.

## Re-syncing

Run `scripts/sync_catalogue.sh` to re-copy from the local `material/code` checkout and diff
against this vendored copy. The commit-SHA gap above can only be closed once the ownership issue
is resolved outside of this tooling.
