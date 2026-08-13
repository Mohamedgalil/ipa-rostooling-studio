#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ros_studio.py -- the Python companion for /ros-studio, an interactive authoring editor for
RosTooling models. The editor itself is a self-contained vanilla-JS page (no network); this
script owns everything the browser cannot: seeding a project from existing files,
DETERMINISTIC file generation, and REAL validation against rosmodel_lint (always) and the
language-server oracle (opt-in).

    ros_studio.py init [FILE.rossystem ...] [--out project.json]
        Build a project.json. With a .rossystem argument, seed from it: reuse ros_plot's
        extractor for the system structure and open the sibling .ros2 files (via
        rosmodel_lint's compose) to recover each interface's type and the artifacts'
        parameters. With no argument, emit a blank project.

    ros_studio.py render project.json [--out ros-studio.html] [--open]
        Emit the self-contained editor HTML, with the three autocomplete datasets
        (message/service/action types, package names, node catalogue) embedded so
        autocomplete works offline.

    ros_studio.py generate project.json [--outdir DIR] [--oracle]
        Deterministically emit .ros2 / .rossystem / companion .ros (reusing rosmodel_lint's
        vocabulary), then run rosmodel_lint over the result. With --oracle, stage catalogue
        dependencies (collect_deps) and run the real language server (ask_oracle). On a
        generation/lint ERROR, re-render the editor with the diagnostics injected onto the
        offending nodes (written next to the project as <project>.error.html).

This SUPERSEDES /ros-plot for authoring; /ros-plot stays as the lightweight read-only path.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import rosmodel_lint as L        # noqa: E402  grammar constants + compose + accessors
import _studio_common as C       # noqa: E402  shared HTML/CSS/JS primitives + emit vocab
import ros_plot                  # noqa: E402  reuse the read-only extractor for seeding

PLUGIN_ROOT = os.path.dirname(_HERE)
ASSETS = os.path.join(PLUGIN_ROOT, "assets")
ARROW_KINDS = L.ARROW_KIND_ORDER            # ["pub","sub","ss","sc","as","ac"]
SRC_SIDE = {"pub": 1, "ss": 1, "as": 1, "sub": 0, "sc": 0, "ac": 0}


# ========================================================================================
# Small emit helpers (quoting mirrors rosmodel_lint's grammar facts)
# ========================================================================================

def _q_double(s):
    """Double-quoted scalar. Backslash escaping (\\\\, \\") is accepted by BOTH the YAML
    composer the linter uses AND the Xtext STRING terminal the language server uses, so a
    label like  say "hi"  round-trips through both."""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _q_single(s):
    """Single-quoted scalar for .ros2 names / type refs. Valid ROS names never contain a
    quote or backslash, but if one slips through, fall back to a double-quoted scalar: YAML's
    '' doubling and Xtext's \\' escaping are mutually incompatible in single quotes, whereas
    double-quoted backslash escaping satisfies both."""
    s = str(s)
    if "'" in s or "\\" in s:
        return _q_double(s)
    return "'" + s + "'"


def _sanitise(text):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(text))


def _fmt_param_value(ptype, value):
    """Typed value emission -- prevents the True/int and Double-without-.0 traps."""
    ptype = (ptype or "String").strip()
    raw = "" if value is None else str(value)
    if ptype == "Boolean":
        return "true" if re.match(r"^\s*(t|1|y|true)", raw, re.I) else "false"
    if ptype == "Integer":
        try:
            return str(int(float(raw))) if raw else "0"
        except ValueError:
            return "0"
    if ptype == "Double":
        try:
            f = float(raw) if raw else 0.0
        except ValueError:
            f = 0.0
        s = repr(f)
        if "." in s:
            return s
        if "e" in s or "E" in s:                 # 1e+20 -> 1.0e+20 (a mantissa is required)
            mant, _, exp = s.partition("e")
            if "." not in mant:
                mant += ".0"
            return mant + "e" + exp
        return s + ".0"
    # String / Base64 and anything else: a quoted literal in .ros2. Prefer single quotes, but
    # a value with an embedded ' or \\ must use the double-quoted+escaped form (see _q_single).
    return _q_single(raw)


# ========================================================================================
# Seeding: parse sibling .ros2 files to recover interface types + parameters
# ========================================================================================

def _compose(path, kind):
    """Drive rosmodel_lint's byte/layout + compose stages for an arbitrary file kind.
    Returns the root YAML node or None."""
    lint = L.Linter(path, use_catalogue=False)
    lint.kind = kind
    try:
        with open(path, "rb") as handle:
            lint.raw = handle.read()
    except (IOError, OSError):
        return None
    lint.check_bytes_and_layout()
    if not L.HAVE_YAML:
        return None
    try:
        ok = lint.compose()
    except Exception:
        return None
    return lint.root if ok else None


def parse_ros2(path):
    """Map a .ros2 AmentPackage to {(package, nodeOrArtifact): artifact_record}. Each record
    carries the full interface set with types and the artifact parameters."""
    root = _compose(path, "ros2")
    out = {}
    pkg_git = {}
    if root is None:
        return out, pkg_git
    for pkg_key, pkg_val in L.mapping_items(root):
        if not (L.is_scalar(pkg_key) and L.is_mapping(pkg_val)):
            continue
        package = pkg_key.value
        git_node = L.mapping_get(pkg_val, "fromGitRepo")
        if L.is_scalar(git_node):
            pkg_git[package] = ros_plot._strip_quotes(git_node.value)
        arts = L.mapping_get(pkg_val, "artifacts")
        if not L.is_mapping(arts):
            continue
        for art_key, art_val in L.mapping_items(arts):
            if not (L.is_scalar(art_key) and L.is_mapping(art_val)):
                continue
            artifact = art_key.value
            node_node = L.mapping_get(art_val, "node")
            node_name = node_node.value if L.is_scalar(node_node) else artifact
            ifaces = []
            for kind in ARROW_KINDS:
                block = L.mapping_get(art_val, C.KIND_TO_BLOCK[kind])
                if not L.is_mapping(block):
                    continue
                for ik, iv in L.mapping_items(block):
                    if not L.is_scalar(ik):
                        continue
                    name = ros_plot._strip_quotes(ik.value)
                    typ = None
                    qos = None
                    if L.is_mapping(iv):
                        tnode = L.mapping_get(iv, "type")
                        if L.is_scalar(tnode):
                            typ = ros_plot._strip_quotes(tnode.value)
                        qnode = L.mapping_get(iv, "qos")
                        if L.is_mapping(qnode):
                            qos = {}
                            for qk, qv in L.mapping_items(qnode):
                                if L.is_scalar(qk) and L.is_scalar(qv):
                                    qos[qk.value] = ros_plot._strip_quotes(qv.value)
                            if not qos:
                                qos = None
                    ifaces.append({"name": name, "kind": kind, "type": typ, "qos": qos})
            params = []
            pnode = L.mapping_get(art_val, "parameters")
            if L.is_mapping(pnode):
                for pk, pv in L.mapping_items(pnode):
                    if not L.is_scalar(pk):
                        continue
                    ptype = pdefault = None
                    if L.is_mapping(pv):
                        tn = L.mapping_get(pv, "type")
                        dn = L.mapping_get(pv, "default")
                        ptype = tn.value if L.is_scalar(tn) else None
                        pdefault = dn.value if L.is_scalar(dn) else None
                    params.append({"name": ros_plot._strip_quotes(pk.value),
                                   "ptype": ptype or "String", "value": pdefault})
            rec = {"artifact": artifact, "node": node_name, "package": package,
                   "interfaces": ifaces, "params": params}
            out[(package, node_name)] = rec
            out[(package, artifact)] = rec
    return out, pkg_git


def seed_from_rossystem(path):
    """Build a project dict from an existing .rossystem plus its sibling .ros2 files."""
    model = ros_plot.extract_model(path, use_catalogue=True)
    base_dir = os.path.dirname(os.path.abspath(path))

    # index every .ros2 in the system directory and one level of common subdirs
    ros2_index, pkg_git = {}, {}
    seen = set()
    globs = ["*.ros2", "rosnodes/*.ros2", "nodes/*.ros2", "*/*.ros2"]
    for g in globs:
        for f in glob.glob(os.path.join(base_dir, g)):
            f = os.path.abspath(f)
            if f in seen:
                continue
            seen.add(f)
            idx, git = parse_ros2(f)
            ros2_index.update(idx)
            pkg_git.update(git)

    uid = [0]

    def nid(prefix):
        uid[0] += 1
        return "%s%d" % (prefix, uid[0])

    nodes = []
    node_by_modelid = {}
    for mn in model["nodes"]:
        pkg = mn.get("package")
        node_name = mn.get("nodeName")
        artifact = None
        for i in mn["interfaces"]:
            if i.get("artifact"):
                artifact = i["artifact"]
                break
        rec = None
        if pkg and node_name:
            rec = ros2_index.get((pkg, node_name)) or (
                ros2_index.get((pkg, artifact)) if artifact else None)
        backing = "hand"
        cat_file = None
        if rec is None and mn.get("resolved"):
            backing = "cat"
            cat_file = mn.get("catalogueFile")

        # The exposure LABEL ("odom_pub") and the interface NAME it arrow-points at ("odom")
        # are distinct slots in the DSL. Index the source exposures by the name they target so
        # the label survives seeding. Deriving it back from the label instead is not possible:
        # a label spelled anything other than <name>_<kind> ("tf_btnav_sub" -> "tf") could not
        # be re-linked, and its connection was silently dropped.
        exposures, exposures_by_name = {}, {}
        for i in mn["interfaces"]:
            tgt = i.get("ifaceName") or i["label"]
            exposures.setdefault((tgt, i["kind"]), i)
            exposures_by_name.setdefault(tgt, i)

        ifaces = []
        if rec is not None:
            artifact = rec["artifact"]
            claimed = set()
            for i in rec["interfaces"]:
                src = (exposures.get((i["name"], i["kind"]))
                       or exposures_by_name.get(i["name"]))
                if src is not None:
                    claimed.add(src["label"])
                ifaces.append({"id": nid("i"), "name": i["name"], "kind": i["kind"],
                               "type": i.get("type"), "qos": i.get("qos"),
                               "label": src["label"] if src else None,
                               "exposed": src is not None})
            # An exposure whose target the backing .ros2 does not declare would otherwise
            # vanish. Keep it, flagged: validate_project blocks generation on it, so a model
            # that cannot resolve is reported rather than quietly truncated.
            for i in mn["interfaces"]:
                if i["label"] in claimed:
                    continue
                ifaces.append({"id": nid("i"),
                               "name": i.get("ifaceName") or i["label"], "kind": i["kind"],
                               "type": None, "qos": None, "label": i["label"],
                               "exposed": True, "orphan": True})
            params = [{"id": nid("p"), "name": p["name"], "ptype": p["ptype"],
                       "value": p["value"]} for p in rec["params"]]
        else:
            # No local .ros2 recovered: fall back to the interfaces the .rossystem exposed.
            # For a CATALOGUE-backed node the vendored .ros2 is still an authority on which
            # names exist, so an exposure ros_plot could not find there is flagged the same
            # way as one missing from a local artifact -- otherwise the two backings disagree
            # about when a bad arrow target is caught (pre-write gate vs post-write RM086).
            missing = set(mn.get("catalogueMissing") or [])
            for i in mn["interfaces"]:
                iname = i.get("ifaceName") or i["label"]
                ifaces.append({"id": nid("i"), "name": iname,
                               "kind": i["kind"], "type": None, "qos": None,
                               "label": i["label"], "exposed": True,
                               "orphan": iname in missing})
            params = [{"id": nid("p"), "name": p["label"], "ptype": "String",
                       "value": p.get("value")} for p in mn.get("params", [])]
            artifact = artifact or (node_name or mn["label"])

        node = {"id": nid("n"), "label": mn["label"], "backing": backing,
                "pkg": pkg or "", "node": node_name or mn["label"],
                "artifact": artifact, "catalogueFile": cat_file,
                "x": 0, "y": 0, "ifaces": ifaces, "params": params}
        nodes.append(node)
        node_by_modelid[mn["id"]] = node

    # rebuild connections from the model edges, resolving label -> (node, iface)
    conns = []
    for e in model["edges"]:
        fn = node_by_modelid.get(e["fromNode"])
        tn = node_by_modelid.get(e["toNode"])
        if not fn or not tn:
            continue
        fi = _match_iface(fn, e["fromLabel"], e.get("kind"))
        ti = _match_iface(tn, e["toLabel"], None)
        if fi and ti:
            conns.append({"id": nid("c"), "from": {"n": fn["id"], "i": fi["id"]},
                          "to": {"n": tn["id"], "i": ti["id"]}})

    _grid_layout(nodes)
    packages = {n["pkg"]: {"fromGitRepo": pkg_git.get(n["pkg"])}
                for n in nodes if n["backing"] == "hand" and n["pkg"]}

    return {
        "formatVersion": 2,
        "system": {"name": model["systemName"], "fromFile": model.get("fromFile")},
        "packages": packages,
        "nodes": nodes,
        "connections": conns,
        "seededFrom": os.path.abspath(path),
        "diagnostics": {"global": list(model.get("diagnostics", [])), "byNode": {}},
    }


def _match_iface(node, label, kind):
    """Resolve a .rossystem interface/connection label to one of a node's recovered
    interfaces. The exposure label seeded onto the interface is authoritative and is tried
    first; the name-based fallbacks below only apply to projects seeded before labels were
    carried (formatVersion 1) or to labels the source never declared."""
    for f in node["ifaces"]:
        if f.get("label") == label and (kind is None or f["kind"] == kind):
            return f
    for f in node["ifaces"]:
        if f.get("label") == label:
            return f
    base = re.sub(r"_(pub|sub|ss|sc|as|ac)$", "", label)
    cands = node["ifaces"]
    # exact name, optionally constrained by kind
    for f in cands:
        if f["name"] == label and (kind is None or f["kind"] == kind):
            return f
    for f in cands:
        if f["name"] == base and (kind is None or f["kind"] == kind):
            return f
    for f in cands:
        if f["name"] == base:
            return f
    return None


def _grid_layout(nodes):
    cols = max(1, int(len(nodes) ** 0.5 + 0.9999))
    for i, n in enumerate(nodes):
        n["x"] = 60 + (i % cols) * 300
        n["y"] = 80 + (i // cols) * 240


def blank_project(name="new_system"):
    return {
        "formatVersion": 2,
        "system": {"name": name, "fromFile": None},
        "packages": {},
        "nodes": [],
        "connections": [],
        "diagnostics": {"global": [], "byNode": {}},
    }


# ========================================================================================
# Deterministic generation
# ========================================================================================

def _iface_by_id(node, iid):
    for f in node["ifaces"]:
        if f["id"] == iid:
            return f
    return None


def _node_by_id(project, nid_):
    for n in project["nodes"]:
        if n["id"] == nid_:
            return n
    return None


def _type_catalogue_file(typ):
    """The relative catalogue file a type resolves to, or None. Uses rosmodel_lint's own
    index so any disclosure comment we emit matches what the linter looks for."""
    if not typ:
        return None
    idx = L.load_type_index() or {}
    entry = idx.get(typ)
    return entry.get("file") if entry else None


def _local_type_packages(project):
    """Packages that hand-authored nodes declare (candidates for a companion .ros)."""
    return {n["pkg"] for n in project["nodes"] if n["backing"] == "hand" and n["pkg"]}


def _companion_types(project):
    """Types that are NOT in the type catalogue but whose package is authored locally ->
    they need a companion .ros. Returns {package: {(block, TypeName)}}."""
    local_pkgs = _local_type_packages(project)
    out = {}
    for n in project["nodes"]:
        if n["backing"] != "hand":
            continue
        for f in n["ifaces"]:
            typ = f.get("type")
            if not typ or "/" not in typ:
                continue
            parts = typ.split("/")
            if len(parts) != 3:
                continue
            pkg, seg, name = parts
            if pkg in local_pkgs and _type_catalogue_file(typ) is None:
                block = C.TYPE_SEG_TO_ROS_BLOCK.get(seg)
                if block:
                    out.setdefault(pkg, set()).add((block, name))
    return out


def _type_comment(typ, companion_pkgs):
    """Disclosure comment for a type reference (RM089), unless we emit its companion .ros."""
    if not typ or "/" not in typ:
        return ""
    pkg = typ.split("/")[0]
    if pkg in companion_pkgs:
        return ""
    rel = _type_catalogue_file(typ)
    return "  # assets/roscommonobjects/%s" % rel if rel else ""


def emit_ros2(package, git, art_records, companion_pkgs):
    """One AmentPackage block with N artifacts (sorted). art_records: list of node dicts."""
    lines = [package + ":"]
    if git:
        lines.append("  fromGitRepo: " + _q_double(git))
    lines.append("  artifacts:")
    for node in sorted(art_records, key=lambda n: n["artifact"]):
        lines.append("    " + node["artifact"] + ":")
        lines.append("      node: " + node["node"])
        for kind in ARROW_KINDS:
            group = sorted([f for f in node["ifaces"] if f["kind"] == kind],
                           key=lambda f: f["name"])
            if not group:
                continue
            lines.append("      " + C.KIND_TO_BLOCK[kind] + ":")
            for f in group:
                lines.append("        " + _q_single(f["name"]) + ":")
                typ = f.get("type") or "TODO_pkg/msg/Type"
                lines.append("          type: " + _q_single(typ)
                             + _type_comment(typ, companion_pkgs))
                _emit_qos(lines, f.get("qos"), "          ")
        params = node.get("params") or []
        if params:
            lines.append("      parameters:")
            for p in sorted(params, key=lambda p: p["name"]):
                lines.append("        " + _q_single(p["name"]) + ":")
                lines.append("          type: " + (p.get("ptype") or "String"))
                lines.append("          default: " + _fmt_param_value(p.get("ptype"),
                                                                      p.get("value")))
    return "\n".join(lines) + "\n"


def _emit_qos(lines, qos, indent):
    """Emit a qos: block if the interface carries one. Durations are quoted int-ns or
    'infinite' per the grammar; enums are bare keywords."""
    if not qos or not isinstance(qos, dict):
        return
    lines.append(indent + "qos:")
    for key in L.QOS_PINNED:
        if key not in qos or qos[key] in (None, ""):
            continue
        val = qos[key]
        if key in L.QOS_NEWER and key in ("lease_duration", "lifespan", "deadline"):
            val = _q_double(val) if str(val) != "infinite" else _q_double("infinite")
        lines.append(indent + "  " + key + ": " + str(val))


def _companion_ros(package, blocks):
    """A minimal .ros for locally-invented types: bodiless spec entries (legal; RM080 INFO)."""
    lines = [package + ":"]
    by_block = {}
    for block, name in sorted(blocks):
        by_block.setdefault(block, []).append(name)
    for block in L.ROS_SPEC_BLOCKS:              # msgs, srvs, actions
        if block not in by_block:
            continue
        lines.append("  " + block + ":")
        for name in sorted(by_block[block]):
            lines.append("    " + name)
            for body in L.ROS_SPEC_BODIES[block]:   # message / request+response / goal...
                lines.append("      " + body)
    return "\n".join(lines) + "\n"


def _exposure_labels(project):
    """Assign each exposed interface a unique in-file label for the .rossystem.

    An interface is exposed when it carries `exposed` (the source .rossystem declared it) OR
    when a connection touches it. Connectivity alone is NOT the test: a model may declare an
    interface for documentation and deliberately leave it unwired, and treating those as
    unexposed deleted them on every round-trip.

    A label carried over from the source wins verbatim and claims its name first; only
    interfaces without one get a derived label, so a round-trip reproduces the author's
    names rather than renaming them."""
    wanted, seen = [], set()

    def want(n, f):
        key = (n["id"], f["id"])
        if key not in seen:
            seen.add(key)
            wanted.append((n, f))

    for n in project["nodes"]:
        for f in n.get("ifaces", []):
            if f.get("exposed"):
                want(n, f)
    for c in project["connections"]:
        for end in (c["from"], c["to"]):
            n = _node_by_id(project, end["n"])
            f = _iface_by_id(n, end["i"]) if n else None
            if n and f:
                want(n, f)

    labels, used = {}, set()

    # pass 1: source labels are authoritative
    for n, f in wanted:
        lbl = (f.get("label") or "").strip()
        if lbl and lbl not in used:
            used.add(lbl)
            labels[(n["id"], f["id"])] = lbl

    # pass 2: derive the rest from the interface name, disambiguating against pass 1
    rest = [(n, f) for n, f in wanted if (n["id"], f["id"]) not in labels]
    base_counts = {}
    for n, f in rest:
        base_counts[f["name"]] = base_counts.get(f["name"], 0) + 1
    for n, f in rest:
        if base_counts[f["name"]] == 1:
            lbl = f["name"]
        else:
            lbl = f["name"] + "_" + f["kind"]
        if lbl in used:
            lbl = f["name"] + "_" + f["kind"] + "_" + _sanitise(n["label"])
        suffix = 2
        while lbl in used:                       # last resort: never emit a duplicate key
            lbl = "%s_%s_%s_%d" % (f["name"], f["kind"], _sanitise(n["label"]), suffix)
            suffix += 1
        used.add(lbl)
        labels[(n["id"], f["id"])] = lbl
    return labels


def emit_rossystem(project):
    labels = _exposure_labels(project)
    sysname = project["system"].get("name") or "system"
    lines = [sysname + ":"]
    from_file = project["system"].get("fromFile")
    if from_file:
        lines.append("  fromFile: " + _q_double(from_file))
    lines.append("  nodes:")
    for n in project["nodes"]:
        lines.append("    " + _q_double(n["label"]) + ":")
        from_val = "%s.%s" % (n["pkg"], n["node"])
        comment = ""
        if n["backing"] == "cat" and n.get("catalogueFile"):
            comment = "  # assets/rosmodelscatalog/%s" % n["catalogueFile"]
        lines.append("      from: " + _q_double(from_val) + comment)
        exposed = [f for f in n["ifaces"] if (n["id"], f["id"]) in labels]
        exposed.sort(key=lambda f: (ARROW_KINDS.index(f["kind"]), f["name"]))
        if exposed:
            lines.append("      interfaces:")
            for f in exposed:
                lbl = labels[(n["id"], f["id"])]
                tgt = "%s::%s" % (n["artifact"], f["name"])
                lines.append("        - " + _q_double(lbl) + ": " + f["kind"] + "-> "
                             + _q_double(tgt))
    if project["connections"]:
        lines.append("  connections:")
        for c in project["connections"]:
            fn = _node_by_id(project, c["from"]["n"])
            tn = _node_by_id(project, c["to"]["n"])
            fl = labels.get((c["from"]["n"], c["from"]["i"]))
            tl = labels.get((c["to"]["n"], c["to"]["i"]))
            if fl and tl:
                lines.append("    - [" + _q_double(fl) + ", " + _q_double(tl) + "]")
    return "\n".join(lines) + "\n"


def _catalogue_artifact_types(cat_file, artifact, cache):
    """Resolve {ifaceName: type} for a catalogue artifact by composing its vendored .ros2 under
    assets/rosmodelscatalog/. node_index.json stores only the kind, never the type, so a
    catalogue interface starts type-less; this recovers the real type the language server sees.
    `cache` is keyed by cat_file so each .ros2 is composed at most once. Degrades to {} when the
    file is missing or won't compose (the caller then treats the type as unknown)."""
    if cat_file not in cache:
        by_art = {}
        path = os.path.join(ASSETS, "rosmodelscatalog", cat_file or "")
        if cat_file and os.path.isfile(path):
            idx, _ = parse_ros2(path)
            for (_pkg, _k), rec in idx.items():
                m = by_art.setdefault(rec["artifact"], {})
                for i in rec["interfaces"]:
                    if i.get("type"):
                        m[i["name"]] = i["type"]
        cache[cat_file] = by_art
    return cache[cat_file].get(artifact, {})


def _effective_iface_type(node, iface, cache):
    """The interface's own type, or -- for a catalogue-backed node whose interface is type-less
    -- the type recovered from the catalogue .ros2. Empty string when genuinely unknown."""
    t = (iface.get("type") or "").strip()
    if t:
        return t
    if node.get("backing") == "cat" and node.get("catalogueFile"):
        m = _catalogue_artifact_types(node["catalogueFile"], node.get("artifact"), cache)
        return (m.get(iface.get("name")) or "").strip()
    return ""


def catalogue_types_map(catalogue):
    """For every catalogue node, {key: {ifaceName: type}} resolved from its vendored .ros2.
    Embedded at render so the live editor knows catalogue interface types offline (no fetch)."""
    out = {}
    cache = {}
    for key, entry in (catalogue or {}).items():
        types = _catalogue_artifact_types(entry.get("file"), entry.get("artifact"), cache)
        if types:
            out[key] = types
    return out


def validate_project(project):
    """Generation gate. rosmodel_lint is WEAKER than the real language server on three checks,
    so these are enforced here BEFORE any file is written: the default `generate` must never
    emit a file the oracle would reject. Returns a diagnostics dict {'global':[...],
    'byNode':{id:[...]}}; empty means it is safe to generate."""
    glob_errs = []
    by_node = {}

    def flag(nid_, msg):
        by_node.setdefault(nid_, []).append(msg)

    # B3: an empty `nodes:` block is "missing RULE_BEGIN" to the server.
    if not project.get("nodes"):
        glob_errs.append("System has no nodes — the language server rejects an empty "
                         "'nodes:' block. Add at least one node before generating.")

    # B2: a hand-authored interface without a resolvable message type would emit a
    # placeholder the server cannot resolve ("Couldn't resolve reference to TopicSpec").
    for n in project.get("nodes", []):
        if n.get("backing") != "hand":
            continue
        for f in n.get("ifaces", []):
            typ = (f.get("type") or "").strip()
            if not typ or typ.startswith("TODO"):
                flag(n["id"], "interface '%s' (%s) has no message type — set a type before "
                              "generating (the server cannot resolve a placeholder)."
                              % (f.get("name", "?"), f.get("kind", "?")))

    # Seeding kept an exposure whose target the backing artifact does not declare. Emitting it
    # would produce "Couldn't resolve reference to <Kind>" from the server, so block here —
    # the alternative (dropping it at seed time) loses the author's model without saying so.
    for n in project.get("nodes", []):
        for f in n.get("ifaces", []):
            if f.get("orphan"):
                flag(n["id"], "interface '%s' (%s) is exposed as '%s' but artifact '%s' does "
                              "not declare it — the server cannot resolve the arrow target. "
                              "Fix the name, or drop the exposure."
                              % (f.get("name", "?"), f.get("kind", "?"),
                                 f.get("label", "?"), n.get("artifact", "?")))

    # B1 + N1: both endpoints of a connection must share the same type ("A connection can only
    # be formed by interfaces with the same type"). Catalogue interfaces are type-less in
    # node_index, so resolve their real type from the vendored .ros2 first; otherwise a
    # catalogue endpoint would slip past the t1/t2 guard and silently ship a rejected file.
    cat_cache = {}
    for c in project.get("connections", []):
        fn = _node_by_id(project, c["from"]["n"])
        tn = _node_by_id(project, c["to"]["n"])
        ff = _iface_by_id(fn, c["from"]["i"]) if fn else None
        tf = _iface_by_id(tn, c["to"]["i"]) if tn else None
        if not (ff and tf):
            continue
        t1 = _effective_iface_type(fn, ff, cat_cache)
        t2 = _effective_iface_type(tn, tf, cat_cache)
        if t1 and t2 and t1 != t2:
            m = ("connection type mismatch: %s '%s' (%s) -> %s '%s' (%s) — endpoints must "
                 "share one type." % (fn["label"], ff["name"], t1, tn["label"], tf["name"], t2))
            flag(fn["id"], m)
            flag(tn["id"], m)

    return {"global": glob_errs, "byNode": by_node}


def generate_files(project):
    """Return {relpath: content} for every file the project generates."""
    files = {}
    companions = _companion_types(project)
    companion_pkgs = set(companions.keys())

    # group hand-authored nodes by package -> one .ros2 each
    by_pkg = {}
    for n in project["nodes"]:
        if n["backing"] == "hand" and n["pkg"]:
            by_pkg.setdefault(n["pkg"], []).append(n)
    for pkg, recs in sorted(by_pkg.items()):
        git = (project.get("packages", {}).get(pkg) or {}).get("fromGitRepo")
        files[pkg + ".ros2"] = emit_ros2(pkg, git, recs, companion_pkgs)

    for pkg, blocks in sorted(companions.items()):
        files[pkg + ".ros"] = _companion_ros(pkg, blocks)

    files[project["system"].get("name", "system") + ".rossystem"] = emit_rossystem(project)
    return files


# ========================================================================================
# Validation
# ========================================================================================

def run_lint(paths):
    """Run rosmodel_lint over the generated files; return (errors, warnings, infos, text)."""
    findings = []
    for p in paths:
        lint = L.Linter(p, use_catalogue=True)
        lint.run()
        findings.extend(lint.findings)
    errs = [f for f in findings if f.severity == L.ERROR]
    warns = [f for f in findings if f.severity == L.WARNING]
    infos = [f for f in findings if f.severity == L.INFO]
    return errs, warns, infos, findings


def run_oracle(outdir, model_paths):
    """Stage catalogue deps then ask the real language server. Returns (ok, text)."""
    try:
        import collect_deps
    except Exception as exc:
        return False, "collect_deps unavailable: %s" % exc
    oracle_dir = os.path.join(os.path.dirname(_HERE), "tests", "oracle")
    ask = os.path.join(oracle_dir, "ask_oracle.py")
    if not os.path.isfile(ask):
        return False, "ask_oracle.py not found at %s" % ask
    try:
        collect_deps.collect(model_paths, outdir)
    except Exception as exc:
        return False, "dep staging failed: %s" % exc
    python = os.environ.get("ROSMODEL_PYTHON", sys.executable)
    try:
        proc = subprocess.run([python, ask, outdir], capture_output=True, text=True,
                              timeout=300)
    except Exception as exc:
        return False, "oracle invocation failed: %s" % exc
    out = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
    ok = "ACCEPTED" in out and "REJECTED" not in out
    return ok, out


# ========================================================================================
# Autocomplete datasets
# ========================================================================================

def _parse_popular_packages(md_path):
    """Pull package names out of references/popular-ros-packages.md — the FIRST table column
    only (the 'Package' column, e.g. **ros-planning/navigation**), taking the last path
    segment and keeping only valid lowercase ROS package tokens. Restricting to column 1
    avoids scraping English words out of the Purpose column (and, approach, analysis, ...)."""
    names = set()
    if not os.path.isfile(md_path):
        return names
    for line in open(md_path, encoding="utf-8", errors="replace"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells:
            continue
        cell = re.sub(r"[`\[\]\*]|\(.*?\)", "", cells[0]).strip()   # column 1 only
        if not cell or set(cell) <= set("-: "):                      # skip the header rule row
            continue
        tok = cell.split("/")[-1].strip()                           # owner/repo -> repo
        if re.fullmatch(r"[a-z][a-z0-9_]{1,}", tok):
            names.add(tok)
    return names


def load_autocomplete():
    """The three offline datasets, degrading gracefully when a file is missing."""
    warnings = []
    types = []
    tpath = os.path.join(ASSETS, "type_index.json")
    if os.path.isfile(tpath):
        try:
            with open(tpath, encoding="utf-8") as h:
                td = json.load(h)
            types = sorted(k for k in td.get("types", {}).keys())
        except Exception as exc:
            warnings.append("type_index.json unreadable: %s" % exc)
    else:
        warnings.append("assets/type_index.json missing — type autocomplete disabled")

    catalogue = {}
    packages = set()
    npath = os.path.join(ASSETS, "node_index.json")
    if os.path.isfile(npath):
        try:
            with open(npath, encoding="utf-8") as h:
                nd = json.load(h)
            catalogue = nd.get("nodes", {})
            for key in catalogue:
                packages.add(key.split(".")[0])
        except Exception as exc:
            warnings.append("node_index.json unreadable: %s" % exc)
    else:
        warnings.append("assets/node_index.json missing — catalogue picker disabled")

    packages |= _parse_popular_packages(
        os.path.join(PLUGIN_ROOT, "references", "popular-ros-packages.md"))
    for t in types:
        packages.add(t.split("/")[0])

    # catalogue interface types, resolved from the vendored .ros2 files, so the live editor
    # can type-check catalogue connections offline (node_index carries only the kind).
    cat_types = catalogue_types_map(catalogue)

    return {"types": types, "packages": sorted(packages), "catalogue": catalogue,
            "catalogueTypes": cat_types, "warnings": warnings}


# ========================================================================================
# Editor HTML
# ========================================================================================

def render_editor(project, diagnostics=None, banner=None):
    ac = load_autocomplete()
    if diagnostics:
        project = dict(project)
        project["diagnostics"] = diagnostics
    payload = {
        "project": project,
        "types": ac["types"],
        "packages": ac["packages"],
        "catalogue": ac["catalogue"],
        "catalogueTypes": ac.get("catalogueTypes", {}),
        "kindOrder": ARROW_KINDS,
        "kindLabels": {k: C.KIND_LABELS[k] for k in ARROW_KINDS},
        "banner": banner,
        "acWarnings": ac["warnings"],
    }
    data = json.dumps(payload, ensure_ascii=False)
    return (_EDITOR_TEMPLATE
            .replace("/*__PALETTE_CSS__*/", C.PALETTE_CSS)
            .replace("/*__JS_PRIMITIVES__*/", C.JS_PRIMITIVES)
            .replace("/*__DATA__*/null", data)), ac["warnings"]


# The editor template lives in a sibling module string to keep this file readable.
from _studio_editor import EDITOR_TEMPLATE as _EDITOR_TEMPLATE  # noqa: E402


# ========================================================================================
# CLI
# ========================================================================================

def _load_project(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def cmd_init(args):
    seed_failed = False
    if args.files:
        src = args.files[0]
        if not os.path.isfile(src):
            print("ros_studio: init source not found: %s" % src, file=sys.stderr)
            return 1
        project = seed_from_rossystem(src)
        if len(args.files) > 1:
            print("ros_studio: init seeds from the first file only; ignoring %d more."
                  % (len(args.files) - 1), file=sys.stderr)
        if not project.get("nodes"):
            # a real path was given but nothing was recovered -- surface it, don't pretend
            seed_failed = True
    else:
        project = blank_project()
    out = os.path.abspath(args.out or "project.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(project, handle, indent=2, ensure_ascii=False)
    print(out)
    for d in project.get("diagnostics", {}).get("global", []):
        print("  seed diag: %s" % d, file=sys.stderr)
    if seed_failed:
        print("ros_studio: seeding %s recovered ZERO nodes — the file may be malformed or "
              "empty. Wrote a project with no nodes." % os.path.basename(args.files[0]),
              file=sys.stderr)
        return 1
    return 0


def cmd_render(args):
    project = _load_project(args.project)
    html, warnings = render_editor(project)
    out = os.path.abspath(args.out or os.path.join(
        os.path.dirname(os.path.abspath(args.project)), "ros-studio.html"))
    with open(out, "w", encoding="utf-8") as handle:
        handle.write(html)
    print(out)
    for w in warnings:
        print("  autocomplete: %s" % w, file=sys.stderr)
    if args.open_after:
        ros_plot._open_file(out)
    return 0


def cmd_generate(args):
    project = _load_project(args.project)
    outdir = os.path.abspath(args.outdir or os.path.join(
        os.path.dirname(os.path.abspath(args.project)), "generated"))

    # Generation gate: refuse to write anything the real language server would reject, even
    # though rosmodel_lint would pass it. This closes the exit-0-but-oracle-REJECTS gap.
    gate = validate_project(project)
    if gate["global"] or gate["byNode"]:
        for m in gate["global"]:
            print("  GATE %s" % m)
        for nid_, msgs in gate["byNode"].items():
            for m in msgs:
                print("  GATE %s" % m)
        n_errs = len(gate["global"]) + sum(len(v) for v in gate["byNode"].values())
        html, _ = render_editor(project, diagnostics=gate,
                                banner="Generation blocked: %d issue(s) the language server "
                                       "would reject — see the flagged nodes." % n_errs)
        err_html = os.path.splitext(os.path.abspath(args.project))[0] + ".error.html"
        with open(err_html, "w", encoding="utf-8") as handle:
            handle.write(html)
        print("\nERROR: generation refused (nothing written); re-rendered editor with "
              "diagnostics -> %s" % err_html)
        return 1

    os.makedirs(outdir, exist_ok=True)
    files = generate_files(project)
    written = []
    for rel, content in sorted(files.items()):
        p = os.path.join(outdir, rel)
        with open(p, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        written.append(p)
        print("wrote %s" % p)

    errs, warns, infos, findings = run_lint(written)
    print("\nrosmodel_lint: %d error(s), %d warning(s), %d info(s)"
          % (len(errs), len(warns), len(infos)))
    for f in errs + warns:
        print("  %-8s %s:%s %s %s"
              % (f.severity, os.path.basename(f.file or ""),
                 f.line, f.rule, f.message))

    if errs:
        # re-render the editor with diagnostics injected onto nodes
        diag = _diagnostics_for_project(project, findings, files)
        html, _ = render_editor(project, diagnostics=diag,
                                banner="Generation produced %d error(s) — see the flagged "
                                       "nodes." % len(errs))
        err_html = os.path.splitext(os.path.abspath(args.project))[0] + ".error.html"
        with open(err_html, "w", encoding="utf-8") as handle:
            handle.write(html)
        print("\nERROR: re-rendered editor with diagnostics -> %s" % err_html)
        return 1

    if args.oracle:
        print("\n--- oracle (real language server) ---")
        ok, text = run_oracle(outdir, written)
        print(text)
        if not ok:
            print("oracle did NOT return a clean ACCEPTED.", file=sys.stderr)
            return 1
    return 0


def _diagnostics_for_project(project, findings, files):
    """Map linter findings back to project node ids by matching the offending node label /
    package in the generated file the finding came from. Best-effort surface for the editor."""
    by_node = {}
    labels = {n["label"]: n["id"] for n in project["nodes"]}
    pkgs = {}
    for n in project["nodes"]:
        if n["pkg"]:
            pkgs.setdefault(n["pkg"], []).append(n["id"])
    unmatched = []
    for f in findings:
        if f.severity not in (L.ERROR, L.WARNING):
            continue
        msg = "%s %s (%s:%s)" % (f.rule, f.message, os.path.basename(
            f.file or ""), f.line)
        hits = []
        for lbl, nid_ in labels.items():
            if lbl and lbl in f.message:
                hits = [nid_]
                break
        if not hits:
            for pkg, ids in pkgs.items():
                if pkg and pkg in f.message:
                    hits = ids
                    break
        if hits:
            for nid_ in hits:
                by_node.setdefault(nid_, []).append(msg)
        elif f.severity == L.ERROR:
            unmatched.append(msg)
    return {"global": unmatched, "byNode": by_node}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ros_studio.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd")

    p_init = sub.add_parser("init", help="build project.json (seed from .rossystem or blank)")
    p_init.add_argument("files", nargs="*")
    p_init.add_argument("--out", default=None)
    p_init.set_defaults(func=cmd_init)

    p_render = sub.add_parser("render", help="emit the self-contained editor HTML")
    p_render.add_argument("project")
    p_render.add_argument("--out", default=None)
    p_render.add_argument("--open", dest="open_after", action="store_true")
    p_render.set_defaults(func=cmd_render)

    p_gen = sub.add_parser("generate", help="emit files, lint, optionally ask the oracle")
    p_gen.add_argument("project")
    p_gen.add_argument("--outdir", default=None)
    p_gen.add_argument("--oracle", action="store_true")
    p_gen.set_defaults(func=cmd_generate)

    # convenience: `ros_studio.py --json project.json` dumps generated files without writing
    parser.add_argument("--json", metavar="PROJECT", default=None,
                        help="print generated files as JSON for PROJECT and exit")

    args = parser.parse_args(argv)
    if args.json:
        project = _load_project(args.json)
        print(json.dumps(generate_files(project), indent=2, ensure_ascii=False))
        return 0
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
