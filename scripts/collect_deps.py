#!/usr/bin/env python3
"""
collect_deps.py -- resolve a model's type:/from:/arrow references against the vendored
catalogues (assets/type_index.json, assets/node_index.json) and copy the winning
catalogue files into an oracle case directory, replacing the manual "figure out which
_deps files to hand-copy" step.

WHY THIS EXISTS: tests/oracle/cases/_deps/ is a hand-carried, confirmed-stale snapshot
(see assets/roscommonobjects/PROVENANCE.md) that someone has to remember to update by
hand. rosmodel_lint.py's RM083/RM087 already compute exactly which catalogue files a
model needs -- this script just runs the linter and acts on that.

Usage:
    python collect_deps.py <model-file> [<model-file> ...] <case-dir>
        Lints each model file with the catalogue enabled, then copies every catalogue
        file its RM083/RM087 findings named into <case-dir> (creating it if needed).
        This is a TRANSITIVE closure, not just the models' own direct references: a
        copied catalogue file (e.g. lifecycle_msgs.ros) can itself reference further
        catalogue types in its own field bodies (e.g. builtin_interfaces/msg/Time) that
        none of the given model files ever named directly -- those get pulled in too,
        recursively, until nothing new is found.
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rosmodel_lint import Linter  # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
TYPE_CATALOG_ROOT = os.path.join(PLUGIN_ROOT, "assets", "roscommonobjects")
NODE_CATALOG_ROOT = os.path.join(PLUGIN_ROOT, "assets", "rosmodelscatalog")


def collect(model_paths, case_dir):
    """Fixpoint closure, not just a direct-reference lookup: a copied catalogue file (e.g.
    lifecycle_msgs.ros) can itself reference further catalogue types in its own message
    field bodies (e.g. builtin_interfaces/msg/Time) that none of the ORIGINAL model_paths
    ever named directly. Re-lint every newly-copied catalogue file the same way the
    original models were linted, and keep going until nothing new is found."""
    type_files, node_files = set(), set()
    processed = set()
    worklist = list(model_paths)

    while worklist:
        path = worklist.pop()
        if path in processed:
            continue
        processed.add(path)

        linter = Linter(path, use_catalogue=True)
        linter.run()

        for rel in linter.needed_type_files:
            if rel not in type_files:
                type_files.add(rel)
                worklist.append(os.path.join(TYPE_CATALOG_ROOT, rel))
        for rel in linter.needed_node_files:
            if rel not in node_files:
                node_files.add(rel)
                worklist.append(os.path.join(NODE_CATALOG_ROOT, rel))

    os.makedirs(case_dir, exist_ok=True)
    copied = []

    for rel in sorted(type_files):
        src = os.path.join(TYPE_CATALOG_ROOT, rel)
        dst = os.path.join(case_dir, os.path.basename(rel))
        shutil.copyfile(src, dst)
        copied.append(("type", rel, dst))

    for rel in sorted(node_files):
        src = os.path.join(NODE_CATALOG_ROOT, rel)
        dst = os.path.join(case_dir, os.path.basename(rel))
        if os.path.exists(dst) and os.path.basename(rel) in {os.path.basename(t) for t in type_files}:
            # A .ros2 catalogue file and a .ros type file happening to share a basename
            # is not possible (different extensions), but guard anyway rather than silently
            # overwrite.
            print("WARNING: basename collision copying %s -> %s, skipped" % (rel, dst),
                  file=sys.stderr)
            continue
        shutil.copyfile(src, dst)
        copied.append(("node", rel, dst))

    return copied


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2:
        print(__doc__)
        return 1

    *model_paths, case_dir = argv
    missing = [p for p in model_paths if not os.path.isfile(p)]
    if missing:
        print("Model file(s) not found: %s" % ", ".join(missing), file=sys.stderr)
        return 1

    copied = collect(model_paths, case_dir)
    if not copied:
        print("No catalogue files needed (nothing resolved, or catalogue indexes missing).")
        return 0

    for kind, rel, dst in copied:
        print("%-5s %-55s -> %s" % (kind, rel, dst))
    print("Copied %d file(s) into %s" % (len(copied), case_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
