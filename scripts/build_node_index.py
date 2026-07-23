#!/usr/bin/env python3
"""
build_node_index.py -- index every pkg.node declared in assets/rosmodelscatalog/'s
.ros2 files into assets/node_index.json, plus a human-browsable
references/node-catalogue.md. Also records every .rossystem composition found there
as a retrieval reference (e.g. the real turtlebot3_navigation2.rossystem).

WHY THIS EXISTS: the node-side counterpart to build_type_index.py. An agent authoring
a .rossystem has no way to check that a `from: "pkg.node"` or an arrow/parameter target
`"artifact::interface"` refers to something real versus a plausible-but-invented stock
node -- this is exactly the mistake made when nav2_amcl/nav2_bt_navigator/nav2_planner/
nav2_controller were invented as package names for examples/turtlebot2_navigation.rossystem
(the real catalog names are amcl/bt_navigator/planner_server/controller_server, no `nav2_`
prefix). This index closes that gap (consumed by rosmodel_lint.py's RM084-087 and by
collect_deps.py).

Reuses rosmodel_lint.py's YAML-composition helpers (is_mapping/mapping_items/mapping_keys/
mapping_get/is_scalar), the same ones Linter.check_ros2* uses, rather than writing a second
.ros2 reader.

Usage:
    python build_node_index.py
        Writes assets/node_index.json and references/node-catalogue.md.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rosmodel_lint import (  # noqa: E402
    HAVE_YAML, is_mapping, is_scalar, mapping_items, mapping_keys, mapping_get, yaml,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
CATALOG_ROOT = os.path.join(PLUGIN_ROOT, "assets", "rosmodelscatalog")
INDEX_PATH = os.path.join(PLUGIN_ROOT, "assets", "node_index.json")
CATALOGUE_MD_PATH = os.path.join(PLUGIN_ROOT, "references", "node-catalogue.md")

INTERFACE_BLOCKS = {
    "publishers": "pub", "subscribers": "sub",
    "serviceservers": "ss", "serviceclients": "sc",
    "actionservers": "as", "actionclients": "ac",
}


def compose_yaml(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    try:
        return yaml.compose(text)
    except Exception:
        return None


def extract_ros2_nodes(root):
    """Yield (package_name, artifact_name, node_name, interfaces) for one parsed .ros2 file.

    interfaces is {interface_name: kind} where kind is one of pub/sub/ss/sc/as/ac.
    Mirrors Linter.check_ros2/check_ros2_artifacts/check_ros2_artifact_body's traversal
    without the diagnostics -- assumes well-formed input (the vendored catalog).
    """
    if not is_mapping(root):
        return
    items = mapping_items(root)
    if not items:
        return
    pkg_key, pkg_val = items[0]
    if not is_scalar(pkg_key) or not is_mapping(pkg_val):
        return
    pkg_name = pkg_key.value

    artifacts = mapping_get(pkg_val, "artifacts")
    if not is_mapping(artifacts):
        return

    for art_key, art_val in mapping_items(artifacts):
        if not is_scalar(art_key) or not is_mapping(art_val):
            continue
        artifact_name = art_key.value
        node_val = mapping_get(art_val, "node")
        node_name = node_val.value if is_scalar(node_val) else artifact_name

        interfaces = {}
        for block_key, block_val in mapping_items(art_val):
            if not is_scalar(block_key):
                continue
            kind = INTERFACE_BLOCKS.get(block_key.value)
            if kind is None or not is_mapping(block_val):
                continue
            for iface_key, _iface_val in mapping_items(block_val):
                if is_scalar(iface_key):
                    interfaces[iface_key.value] = kind

        yield pkg_name, artifact_name, node_name, interfaces


def main():
    nodes = {}       # "pkg.node" -> {"file", "artifact", "interfaces"}
    systems = []      # [{"file": ...}] -- .rossystem retrieval references

    for root_dir, _dirs, files in os.walk(CATALOG_ROOT):
        for fname in sorted(files):
            fpath = os.path.join(root_dir, fname)
            rel = os.path.relpath(fpath, CATALOG_ROOT).replace(os.sep, "/")

            if fname.endswith(".rossystem"):
                systems.append({"file": rel})
                continue
            if not fname.endswith(".ros2"):
                continue
            if not HAVE_YAML:
                continue

            root = compose_yaml(fpath)
            if root is None:
                continue

            for pkg_name, artifact_name, node_name, interfaces in extract_ros2_nodes(root):
                key = "%s.%s" % (pkg_name, node_name)
                if key in nodes:
                    continue  # first file wins; collisions are rare and not silently overwritten
                nodes[key] = {"file": rel, "artifact": artifact_name, "interfaces": interfaces}

    payload = {
        "_meta": {
            "generated_by": "scripts/build_node_index.py",
            "source": "assets/rosmodelscatalog/",
            "node_count": len(nodes),
            "system_count": len(systems),
        },
        "nodes": nodes,
        "_systems": sorted(systems, key=lambda s: s["file"]),
    }
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")

    lines = [
        "# Node catalogue (generated -- do not hand-edit)",
        "",
        "Generated by `scripts/build_node_index.py` from `assets/rosmodelscatalog/`. "
        "%d nodes, %d system compositions. Regenerate after `scripts/sync_catalogue.sh`, "
        "never edit this file directly." % (len(nodes), len(systems)),
        "",
        "## Nodes (`from: \"pkg.node\"`)",
        "",
        "| pkg.node | Source file | Artifact | Interfaces (kind: name) |",
        "|---|---|---|---|",
    ]
    for key in sorted(nodes):
        entry = nodes[key]
        ifaces = ", ".join("%s: %s" % (k, n) for n, k in sorted(entry["interfaces"].items()))
        lines.append("| `%s` | `%s` | `%s` | %s |"
                      % (key, entry["file"], entry["artifact"], ifaces or "-"))

    lines += [
        "",
        "## System compositions (`.rossystem`, retrieval references only)",
        "",
    ]
    for sysinfo in sorted(systems, key=lambda s: s["file"]):
        lines.append("- `%s`" % sysinfo["file"])

    os.makedirs(os.path.dirname(CATALOGUE_MD_PATH), exist_ok=True)
    with open(CATALOGUE_MD_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print("Indexed %d nodes, %d systems -> %s" % (len(nodes), len(systems), INDEX_PATH))
    print("Wrote catalogue table -> %s" % CATALOGUE_MD_PATH)


if __name__ == "__main__":
    main()
