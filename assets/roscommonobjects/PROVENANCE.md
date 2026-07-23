# Provenance -- assets/roscommonobjects/

Vendored `.ros` message/service/action type-specification catalog for the RosTooling toolchain.

- **Source**: `de.fraunhofer.ipa.ros.communication.objects` (Fraunhofer IPA)
- **Upstream remote**: `https://github.com/ipa320/RosCommonObjects.git`
- **Pinned commit**: `dadf8d13e6506ad41ca035d0eaef4d08ba556315` (2024-04-24 17:17:08 +0200)
- **Synced**: 2026-07-23, from a local checkout at
  `material/code/RosCommonObjects/de.fraunhofer.ipa.ros.communication.objects`
- **License**: **unconfirmed**. No `LICENSE` file is present in the local checkout or this
  vendored copy. The upstream repo belongs to the same Fraunhofer IPA / `ipa320` organization
  that publishes RosTooling itself under Apache-2.0, but that is not a confirmed license grant
  for this specific repository -- verify before treating this content as cleared for
  redistribution beyond internal/research use.

## Structure

Two directories, vendored **verbatim, unmerged**:

- `basic_msgs/` -- an older, smaller bundle (15 packages across 15 files, one of which,
  `common_msgs.ros`, bundles 9 packages together: `actionlib_msgs`, `diagnostic_msgs`,
  `geometry_msgs`, `nav_msgs`, `sensor_msgs`, `shape_msgs`, `stereo_msgs`, `trajectory_msgs`,
  `visualization_msgs`).
- `nav2_msgs/` -- a larger, more complete bundle (49 files, one package per file), despite the
  directory's name covering far more than just the `nav2_msgs` package -- it includes the actual
  `nav2_msgs.ros` (with `NavigateToPose`/`ComputePathToPose`/`FollowPath`), plus `sensor_msgs`,
  `nav_msgs`, `control_msgs`, `lifecycle_msgs`, `tf2_msgs`, `std_srvs`, and 40+ others.

**These two directories overlap on several package names with genuinely differing content**
(confirmed for `turtlesim`, `control_msgs`, `tf2_msgs`, `builtin_interfaces`, `map_msgs`,
`controller_manager_msgs`, `realsense2_camera_msgs`, `theora_image_transport`, `aruco_msgs`).
`assets/type_index.json` (built by `scripts/build_type_index.py`) resolves this by preferring
`nav2_msgs/`'s definition whenever a package/type exists in both, falling back to `basic_msgs/`
only for what's genuinely absent from `nav2_msgs/` (confirmed cases: `geometry_msgs` -- only
available bundled inside `basic_msgs/common_msgs.ros` -- plus `moveit_msgs`, `gazebo_msgs`, and
`std_msgs` via `ros_core.ros`). The winning source file for every indexed type is recorded in
the index, not decided silently.

Skipped from vendoring: `BasicSpecs/` (Components/Systems templates) -- confirmed to be
fictitious-placeholder scaffolds (`my_awesome_pkg`, `awesome_node`) demonstrating DSL syntax, not
real catalog content.

## Re-syncing

Run `scripts/sync_catalogue.sh` to re-copy from the local `material/code` checkout, diff against
this vendored copy, and update the date above (and the commit SHA, if the upstream repo's `.git`
is readable at sync time).
