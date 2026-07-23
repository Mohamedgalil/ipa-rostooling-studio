#!/usr/bin/env python3
"""
build_type_index.py -- index every message/service/action type declared in
assets/roscommonobjects/ into assets/type_index.json, plus a human-browsable
references/type-catalogue.md.

WHY THIS EXISTS: rosmodel_lint.py's RM076/RM077 only check that a quoted `type:`
reference is SHAPED like "pkg/msg/Type" -- it has never had any notion of whether that
package/type actually exists. An agent generating a model has no way to tell a real
reference from a plausible-but-invented one until the real oracle rejects it. This
script builds the lookup table that closes that gap (consumed by rosmodel_lint.py's
RM081-083 and by collect_deps.py).

assets/roscommonobjects/ vendors two overlapping bundles -- nav2_msgs/ (49 files, newer,
larger) and basic_msgs/ (15 files, older, some packages bundled together in
common_msgs.ros). Where a package/type exists in both with differing content, nav2_msgs/
wins: it is walked first, and basic_msgs/ only fills in types not already indexed.
Every entry records which file it came from, so the choice is auditable, never silent.

Reuses rosmodel_lint.py's parse_ros_indent (the same indentation-stack parser the
linter's own .ros checks run on) rather than writing a second .ros parser. Mirrors the
package -> block -> spec grouping in Linter.check_ros/check_ros_package_body/
check_ros_specs, but extracts facts instead of emitting diagnostics.

Usage:
    python build_type_index.py
        Writes assets/type_index.json and references/type-catalogue.md next to the
        vendored catalog, using paths relative to this script's own directory.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rosmodel_lint import parse_ros_indent  # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
CATALOG_ROOT = os.path.join(PLUGIN_ROOT, "assets", "roscommonobjects")
INDEX_PATH = os.path.join(PLUGIN_ROOT, "assets", "type_index.json")
CATALOGUE_MD_PATH = os.path.join(PLUGIN_ROOT, "references", "type-catalogue.md")

# nav2_msgs/ is walked first so its definitions win on overlap; see PROVENANCE.md.
BUNDLE_ORDER = ["nav2_msgs", "basic_msgs"]

SPEC_BLOCK_KIND = {"msgs": "msg", "srvs": "srv", "actions": "action"}


def group_ros_file(nodes):
    """Yield (pkg_name, kind, spec_name) for every spec declared in one parsed .ros file.

    Mirrors Linter.check_ros / check_ros_package_body / check_ros_specs (rosmodel_lint.py)
    at the level of grouping-by-depth, without any of the diagnostic emission -- this
    assumes well-formed input (the vendored catalog), not arbitrary user text.
    """
    pkgs, cur = [], None
    for node in nodes:
        if node["depth"] == 0:
            cur = {"head": node, "body": []}
            pkgs.append(cur)
        elif cur is not None:
            cur["body"].append(node)

    for pkg in pkgs:
        head_text = pkg["head"]["text"]
        if not head_text.endswith(":"):
            continue
        pkg_name = head_text[:-1].strip().strip("\"'")
        if not pkg_name:
            continue

        body = pkg["body"]
        if not body:
            continue
        base = min(n["depth"] for n in body)
        for i, node in enumerate(body):
            if node["depth"] != base:
                continue
            key = node["text"].split(":", 1)[0].strip()
            if key not in SPEC_BLOCK_KIND:
                continue
            kind = SPEC_BLOCK_KIND[key]

            block_depth = node["depth"]
            inner = []
            for later in body[i + 1:]:
                if later["depth"] <= block_depth:
                    break
                inner.append(later)
            if not inner:
                continue
            spec_depth = min(n["depth"] for n in inner)
            for spec_node in inner:
                if spec_node["depth"] != spec_depth:
                    continue
                spec_name = spec_node["text"].rstrip(":").strip()
                if " " in spec_name.strip("\"'"):
                    continue  # not a spec name line (e.g. a stray field) -- skip rather than guess
                spec_name = spec_name.strip("\"'")
                if spec_name:
                    yield pkg_name, kind, spec_name


def main():
    index = {}
    per_package = {}  # pkg_name -> {"file": ..., "specs": {kind: [names]}}

    for bundle in BUNDLE_ORDER:
        bundle_dir = os.path.join(CATALOG_ROOT, bundle)
        if not os.path.isdir(bundle_dir):
            continue
        for fname in sorted(os.listdir(bundle_dir)):
            if not fname.endswith(".ros"):
                continue
            fpath = os.path.join(bundle_dir, fname)
            with open(fpath, encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
            nodes = parse_ros_indent(lines)
            rel_file = "%s/%s" % (bundle, fname)

            for pkg_name, kind, spec_name in group_ros_file(nodes):
                key = "%s/%s/%s" % (pkg_name, kind, spec_name)
                if key not in index:
                    index[key] = {"kind": kind, "file": rel_file}

                pkg_entry = per_package.setdefault(pkg_name, {"file": rel_file, "specs": {}})
                # Keep using the FIRST file seen for this package (bundle-priority order)
                # for the catalogue table, even if some individual types under it fell
                # back to a different bundle above.
                pkg_entry["specs"].setdefault(kind, [])
                if spec_name not in pkg_entry["specs"][kind]:
                    pkg_entry["specs"][kind].append(spec_name)

    payload = {
        "_meta": {
            "generated_by": "scripts/build_type_index.py",
            "source": "assets/roscommonobjects/",
            "package_count": len(per_package),
            "type_count": len(index),
        },
        "types": index,
    }
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")

    lines = [
        "# Type catalogue (generated -- do not hand-edit)",
        "",
        "Generated by `scripts/build_type_index.py` from `assets/roscommonobjects/`. "
        "%d packages, %d types. Regenerate after `scripts/sync_catalogue.sh`, never edit "
        "this file directly." % (len(per_package), len(index)),
        "",
        "| Package | Source file | msgs | srvs | actions |",
        "|---|---|---|---|---|",
    ]
    for pkg_name in sorted(per_package):
        entry = per_package[pkg_name]
        msgs = ", ".join(sorted(entry["specs"].get("msg", [])))
        srvs = ", ".join(sorted(entry["specs"].get("srv", [])))
        actions = ", ".join(sorted(entry["specs"].get("action", [])))
        lines.append("| `%s` | `%s` | %s | %s | %s |"
                      % (pkg_name, entry["file"], msgs or "-", srvs or "-", actions or "-"))

    os.makedirs(os.path.dirname(CATALOGUE_MD_PATH), exist_ok=True)
    with open(CATALOGUE_MD_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    print("Indexed %d packages, %d types -> %s" % (len(per_package), len(index), INDEX_PATH))
    print("Wrote catalogue table -> %s" % CATALOGUE_MD_PATH)


if __name__ == "__main__":
    main()
