#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ros_studio.py -- the Python companion for /ros-studio, an interactive authoring editor for
RosTooling models. The editor itself is a self-contained vanilla-JS page (no network); this
script owns everything the browser cannot: seeding a project from existing files,
DETERMINISTIC file generation, and REAL validation against rosmodel_lint (always) and the
language-server oracle (opt-in).

    ros_studio.py init [FILE.rossystem | DIR ...] [--out project.json] [--name NAME]
        Build a project.json. With a .rossystem argument, seed from it: reuse ros_plot's
        extractor for the system structure and open the sibling .ros2 files (via
        rosmodel_lint's compose) to recover each interface's type and the artifacts'
        parameters, the sibling .ros files to recover the message FIELDS, and a line-oriented
        pass to recover the COMMENTS (PyYAML discards them). Every comment that cannot be
        attached to a model element is reported. Several files, or a directory, are indexed
        across the whole tree and MERGED into one project (ids re-issued, colliding node
        labels renamed, a subSystems: reference to a system that is itself being merged
        collapsed onto it). With no argument, emit a blank project.

    ros_studio.py render project.json [--out ros-studio.html] [--open]
        Emit the self-contained editor HTML, with the three autocomplete datasets
        (message/service/action types, package names, node catalogue) embedded so
        autocomplete works offline.

    ros_studio.py generate project.json [--outdir DIR] [--oracle] [--diff]
        Deterministically emit .ros2 / .rossystem / companion .ros (reusing rosmodel_lint's
        vocabulary), then run rosmodel_lint over the result. With --oracle, stage catalogue
        dependencies (collect_deps) and run the real language server (ask_oracle). On a
        generation/lint ERROR, re-render the editor with the diagnostics injected onto the
        offending nodes (written next to the project as <project>.error.html). With --diff,
        also print the model-level diff against the seed source (see below).

    ros_studio.py diff project.json [--against FILE.rossystem] [--json]
        What changed since the seed. Compares the GENERATED model against the .rossystem the
        project was seeded from (project["seededFrom"]) at the MODEL level -- nodes,
        exposures, connections, parameters, artifacts, message specs -- not as text, because
        the emitter's fixed key order, quoting and sorting make a text diff unreadable.

This SUPERSEDES /ros-plot for authoring; /ros-plot stays as the lightweight read-only path.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

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

# The three QoS fields whose value is (EString | 'infinite') (Ros2.xtext:38-41). Everything
# else in QOS_PINNED is either an enum keyword or Integer0, so only these three are quoted.
QOS_DURATIONS = ("lease_duration", "lifespan", "deadline")

# Enum vocabularies for the QoS editor. L.QOS_ENUMS is the linter's own table, but it has no
# `liveliness` entry: check_qos short-circuits on QOS_NEWER before it reaches the enum branch,
# so the linter never validates that value and never needed the list. The grammar does --
# ('liveliness:' Liveliness=('automatic'|'manual')) (Ros2.xtext:38) -- and the editor must
# offer exactly those two, or it hands the author a value the parser cannot lex.
QOS_UI_ENUMS = dict(L.QOS_ENUMS, liveliness=["automatic", "manual"])


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
# Comments: capture at seed, re-emit at generate
#
# `generate` used to write only its own provenance comments, so every explanatory comment the
# author had written was deleted on the first edit cycle -- 30+ of them on the TurtleBot 3
# example. PyYAML discards comments outright, so the linter's compose path cannot help; the
# capture below is a separate line-oriented pass keyed by the ELEMENT a comment annotates
# rather than by line number, because a line number does not survive an edit and an element
# identity does.
#
# POLICY (asserted by tests/studio_roundtrip.py, stated in commands/ros-studio.md):
#   PRESERVED   a leading comment block attaches to the next modeled element; a trailing
#               comment attaches to the element on its own line. Modeled elements are: the
#               system, each subSystems: entry, each node, each exposure, each connection; and
#               in the .ros2 the package, each artifact, each interface (plus its `type:` line)
#               and each parameter.
#   NORMALISED  indentation follows the emitted element, not the source; the `# ` spacing is
#               normalised; and a leading block that preceded a block KEY (`nodes:`,
#               `interfaces:`, ...) re-emerges before the FIRST element inside that block,
#               because the model has no slot for the key itself.
#   DROPPED     everything the project model does not carry -- `processes:`, node-level
#               .rossystem `parameters:`, `qos:` internals, and trailing comments on block keys.
#               `init` REPORTS every one of these with its line number (SKILL.md rule 12)
#               instead of discarding it silently.
# ========================================================================================

# A key line with nothing after the colon: 'nodes:', '"amcl":', "'nav_status':".
RE_BARE_KEY = re.compile(r'^(?P<k>"[^"]*"|\'[^\']*\'|[^\s:#]+)\s*:\s*$')
RE_EXPOSURE = re.compile(r'^-\s*(?P<k>"[^"]*"|\'[^\']*\'|[^\s:]+)\s*:\s*'
                         r'(?P<kind>pub|sub|ss|sc|as|ac)->')
# `-[a, b]` with no space after the dash is legal DSL (whitespace is hidden) and 3 corpus files
# write it that way, so the dash and the bracket are not required to be separated.
RE_CONNECTION = re.compile(r'^-\s*\[\s*(?P<a>"[^"]*"|\'[^\']*\'|[^\s,\]]+)\s*,'
                           r'\s*(?P<b>"[^"]*"|\'[^\']*\'|[^\s,\]]+)\s*\]')
ROS2_ITEM_BLOCKS = set(C.KIND_TO_BLOCK.values()) | {"parameters"}


def _clean_comment(text):
    """A comment is '#' to end of line (SL_COMMENT, Basics.xtext:386), so a newline inside one
    would terminate it and turn the remainder of the text into code. Collapse every break."""
    return re.sub(r"[\r\n]+", " ", "" if text is None else str(text)).rstrip()


def _comment_list(value):
    """A leading comment block, from either a JSON list or a textarea's newline-joined text.
    Interior blank entries are kept (they are the author's paragraph breaks, and the TurtleBot 3
    header uses them); leading/trailing ones are dropped, so a textarea's final newline does not
    grow a stray '#' on every save."""
    if value is None:
        return []
    items = value if isinstance(value, (list, tuple)) else str(value).split("\n")
    out = []
    for item in items:
        for part in ("" if item is None else str(item)).split("\n"):
            out.append(_clean_comment(part))
    while out and out[-1] == "":
        out.pop()
    while out and out[0] == "":
        out.pop(0)
    return out


def _comment_block(value, indent):
    """The leading comment block as emitted lines. An empty entry is a bare '#', never '# '."""
    return [indent + ("# " + t if t else "#") for t in _comment_list(value)]


def _note_suffix(note, auto=None):
    """A trailing comment for one emitted line. `auto` is the emitter's own provenance body
    (RM088/RM089), which must not be lost to an edit: an authored comment REPLACES it when the
    comment already names that file -- repeating the path teaches the reader nothing, and the
    TurtleBot 3 example's own from: comments are exactly the provenance line -- and otherwise
    the provenance is kept with the authored text appended."""
    note = _clean_comment(note)
    auto = (auto or "").strip()
    if not note:
        return "  # " + auto if auto else ""
    if auto and auto.rsplit("/", 1)[-1] not in note:
        note = auto + " -- " + note
    return "  # " + note


def _split_comment(raw):
    """(code, comment-body or None) for one source line. Where the comment STARTS is decided by
    rosmodel_lint.ros_split_comment so the studio and the checker agree that a '#' inside a
    quoted EString is content -- `foo: # c` is a comment, `type: 'a#b'` is not."""
    line = raw.rstrip("\r\n")
    code, had = L.ros_split_comment(line)
    if not had:
        return line, None
    body = line[len(code):]
    if body.startswith("#"):
        body = body[1:]
    if body.startswith(" "):
        body = body[1:]
    return code, body.rstrip()


def _iter_source(path):
    """(lineno, code, comment-body-or-None, indent, stripped-code) per line, skipping lines that
    carry no code and no comment."""
    try:
        handle = open(path, encoding="utf-8", errors="replace")
    except (IOError, OSError):
        return
    with handle:
        for lineno, raw in enumerate(handle, 1):
            code, note = _split_comment(raw)
            body = code.strip()
            indent = len(code) - len(code.lstrip(" \t"))
            yield lineno, code, note, indent, body


def scan_rossystem_comments(path):
    """{'header', 'fromFile', 'subSystems': {ref: {...}}, 'nodes': {label: {...}},
    'connections': {(a,b): {...}}, 'dropped': [(line, what, text)]} for one .rossystem."""
    res = {"header": [], "fromFile": "", "subSystems": {}, "nodes": {}, "connections": {},
           "dropped": []}
    pending = []
    sect = node = sub = node_indent = None
    root_seen = False
    for lineno, _code, note, indent, body in _iter_source(path):
        if not body:
            if note is not None:
                pending.append(note)
            continue

        key = RE_BARE_KEY.match(body)
        kw = ros_plot._strip_quotes(key.group("k")) if key else None

        if key and not root_seen and indent == 0:
            root_seen = True
            res["header"], pending = pending, []
            if note:
                res["dropped"].append((lineno, "the system key line", note))
            continue
        if body.startswith("fromFile:"):
            res["fromFile"] = note or ""
            continue
        if key and kw in ("nodes", "connections", "subSystems", "processes"):
            sect, node, sub, node_indent = kw, None, None, None
            if note:
                res["dropped"].append((lineno, "the '%s:' block key" % kw, note))
            continue
        if key and kw == "interfaces" and node is not None:
            sub = "interfaces"
            if note:
                res["dropped"].append((lineno, "the 'interfaces:' block key", note))
            continue
        if key and kw == "parameters":
            # node-level `parameters:` is not carried by the project model (the studio writes
            # parameters into the .ros2 artifact, not into the .rossystem node), so everything
            # inside it is reported rather than half-preserved.
            if node is not None:
                sub = "parameters"
            else:
                sect = "parameters"
            if note:
                res["dropped"].append((lineno, "the 'parameters:' block key", note))
            continue
        # A 'components+=SubSystem*' entry is one bare (optionally quoted) EString per indented
        # line -- there is no `key:` and no bracket list (RM093), so RE_BARE_KEY cannot see it
        # and it has to be matched positionally. The '- ' form is tolerated for the same reason
        # check_subsystems tolerates a block sequence: the corpus writes both.
        if sect == "subSystems" and not key and ":" not in body:
            ref = body[1:].strip() if body.startswith("-") else body
            ref = ros_plot._strip_quotes(ref)
            if ref:
                res["subSystems"][ref] = {"before": pending, "line": note or ""}
                pending = []
                continue

        # `<=`, not `==`: the corpus indents with 3, 5, 6, 7 and 11 spaces and does not always
        # keep sibling node keys on the same column. Anything DEEPER than the current node key
        # belongs to that node, and nothing deeper is a bare key anyway (an exposure starts with
        # '-', a parameter's `value:` carries a value).
        if key and sect == "nodes" and (node_indent is None or indent <= node_indent):
            node_indent = indent
            node = {"before": pending, "line": note or "", "from": "", "ifaces": {}}
            res["nodes"][kw], pending, sub = node, [], None
            continue

        m = RE_EXPOSURE.match(body)
        if m and node is not None and sub == "interfaces":
            node["ifaces"][ros_plot._strip_quotes(m.group("k"))] = {
                "before": pending, "line": note or ""}
            pending = []
            continue
        m = RE_CONNECTION.match(body)
        if m and sect == "connections":
            res["connections"][(ros_plot._strip_quotes(m.group("a")),
                                ros_plot._strip_quotes(m.group("b")))] = {
                "before": pending, "line": note or ""}
            pending = []
            continue
        if body.startswith("from:") and node is not None and sub is None:
            node["from"] = note or ""
            continue
        if note:
            res["dropped"].append((lineno, "a line the project model does not carry", note))
    for text in pending:
        res["dropped"].append((0, "the end of the file, with no element after it", text))
    return res


def scan_ros2_comments(path):
    """{'packages': {pkg: {'header', 'artifacts': {art: {...}}}}, 'dropped': [...]} for one
    .ros2. Interfaces are keyed (block, name) because a publisher and a subscriber may share a
    name -- and in the corpus they routinely do."""
    res = {"packages": {}, "dropped": []}
    pending = []
    pkg = art = block = item = None
    art_indent = item_indent = None
    in_arts = False

    def drop(lineno, what, note):
        if note:
            res["dropped"].append((lineno, what, note))

    for lineno, _code, note, indent, body in _iter_source(path):
        if not body:
            if note is not None:
                pending.append(note)
            continue
        key = RE_BARE_KEY.match(body)
        kw = ros_plot._strip_quotes(key.group("k")) if key else None

        if key and indent == 0:
            pkg = {"header": pending, "artifacts": {}}
            res["packages"][kw], pending = pkg, []
            art = block = item = art_indent = item_indent = None
            in_arts = False
            drop(lineno, "the package key line", note)
            continue
        if key and kw == "artifacts" and pkg is not None:
            in_arts, art, block, art_indent, item_indent = True, None, None, None, None
            drop(lineno, "the 'artifacts:' block key", note)
            continue
        if key and kw in ROS2_ITEM_BLOCKS and art is not None:
            block, item, item_indent = kw, None, None
            drop(lineno, "the '%s:' block key" % kw, note)
            continue
        if key and kw == "qos":
            item = None                     # qos field lines are values, not modeled elements
            drop(lineno, "the 'qos:' block key", note)
            continue
        # `<=` for the same reason as the .rossystem node key above; the block keywords are
        # matched by NAME before this, so a `publishers:` deeper down cannot land here.
        if key and in_arts and (art_indent is None or indent <= art_indent) and pkg is not None:
            art_indent = indent
            art = {"before": pending, "line": note or "", "ifaces": {}, "params": {}}
            pkg["artifacts"][kw], pending = art, []
            block = item = item_indent = None
            continue
        if key and art is not None and block is not None \
                and (item_indent is None or indent == item_indent):
            item_indent = indent
            item = {"before": pending, "line": note or "", "type": ""}
            pending = []
            if block == "parameters":
                art["params"][kw] = item
            else:
                art["ifaces"][(block, kw)] = item
            continue
        if body.startswith("type:") and item is not None:
            item["type"] = note or ""
            continue
        drop(lineno, "a line the project model does not carry", note)
    for text in pending:
        res["dropped"].append((0, "the end of the file, with no element after it", text))
    return res


def _comments(slots):
    """A `comments` object with the empty slots left out, so an element with no comments is
    byte-identical to a formatVersion-2 one and the JSON stays readable. Returns None, not {},
    so the caller can skip the key entirely."""
    out = {}
    for key, value in slots.items():
        if isinstance(value, (list, tuple)):
            if _comment_list(value):
                out[key] = list(value)
        elif _clean_comment(value):
            out[key] = _clean_comment(value)
    return out or None


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


# The reverse of C.TYPE_SEG_TO_ROS_BLOCK: a .ros block back to the segment a qualified type
# name spells. RosQNP.xtend names every spec '<pkg>/msg/<Name>' (or /srv/, /action/), so the
# project key and the file layout are two views of one identity.
ROS_BLOCK_TO_TYPE_SEG = {v: k for k, v in C.TYPE_SEG_TO_ROS_BLOCK.items()}


def parse_ros(path):
    """Map a .ros PackageSet to {'<pkg>/<seg>/<Name>': {'fields': {body: [{type, name}]}}},
    plus a list of package-level members this project has no slot for.

    Not composed as YAML: `float32 x` nested under an un-colonned `Pose` folds into ONE
    multi-line plain scalar, so PyYAML would hand back a spec with no fields -- exactly the
    loss this function exists to stop. It reuses rosmodel_lint's indentation parser, the same
    one check_ros() walks, so the studio and the checker agree about where a field sits.

    SEVERAL top-level packages per file are legal (PackageSet is package+=Package_Impl*;
    tests/oracle/cases/_deps/common_msgs.ros declares nine and the oracle accepts it), so this
    keeps walking at depth 0 instead of stopping after the first.

    A field is exactly two tokens, a Type then a Data (Basics.xtext:201-204), and
    MessagePart+=MessagePart* has no line separator -- so 'time stamp string id' is TWO fields
    on one line and is read as such (RM078 is a warning, not an error).
    """
    types, extras = {}, []
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except (IOError, OSError):
        return types, extras

    pkg = block = spec = body = None
    d_block = d_spec = d_body = None
    for node in L.parse_ros_indent(lines):
        text, depth = node["text"], node["depth"]
        # close every level this line dedented out of, innermost first
        if d_body is not None and depth <= d_body:
            body = d_body = None
        if d_spec is not None and depth <= d_spec:
            spec = d_spec = None
        if d_block is not None and depth <= d_block:
            block = d_block = None

        if depth == 0:
            pkg = text[:-1].strip() if text.endswith(":") else None
            continue
        if pkg is None:
            continue

        if block is None:
            key = text[:-1].strip() if text.endswith(":") else text.split(":")[0].strip()
            if key in L.ROS_SPEC_BLOCKS:
                block, d_block = key, depth
            elif key in L.ROS_PACKAGE_PREFIX_KEYS:
                # 'fromGitRepo:' / 'dependencies:' on a .ros PACKAGE. The project models a
                # package's fromGitRepo only for its .ros2 (project["packages"]), and the two
                # files are different artefacts that may disagree, so this is reported rather
                # than merged into a slot that does not mean the same thing.
                extras.append((pkg, node["line"], text))
            continue

        if spec is None:
            if text.endswith(":"):
                continue                       # a spec name carries NO trailing ':' (Ros.xtext:81)
            spec = ros_plot._strip_quotes(text.strip())
            d_spec = depth
            types.setdefault("%s/%s/%s" % (pkg, ROS_BLOCK_TO_TYPE_SEG[block], spec),
                             {"fields": {b: [] for b in L.ROS_SPEC_BODIES[block]}})
            continue

        if body is None:
            if text in L.ROS_SPEC_BODIES[block]:
                body, d_body = text, depth
            continue

        key = "%s/%s/%s" % (pkg, ROS_BLOCK_TO_TYPE_SEG[block], spec)
        toks = L.ros_tokenise(text)
        for i in range(0, len(toks) - 1, 2):
            types[key]["fields"].setdefault(body, []).append(
                {"type": toks[i], "name": toks[i + 1]})
        if len(toks) % 2:
            extras.append((pkg, node["line"],
                           "%s (odd token count -- '%s' has no name and was not read)"
                           % (text, toks[-1])))
    return types, extras


def resolve_subsystem(ref, base_dir):
    """One `subSystems:` reference -> (catalogue file or None, {label: {'from', 'interfaces':
    {name: kind}}}). {} when the reference resolves to nothing.

    A subsystem's connectable interfaces are exactly what its OWN `interfaces:` block declares
    -- never what the .ros2 behind its `from:` declares (checkIfInterfaceInSystem,
    RosSystemValidator.xtend:87-109, and RM091's message says the same). Both branches below
    read that block and nothing else.

    assets/node_index.json is consulted FIRST because it is what rosmodel_lint's
    check_subsystems resolves against, so the studio and the checker never disagree about what
    a reference exposes. A project-local system the catalogue has never seen falls back to a
    sibling `<ref>.rossystem`, which offline is the only other place the answer can come from.
    """
    entry = (L.load_system_index() or {}).get(ref)
    if entry is not None and not entry.get("hasOwnSubsystems"):
        # nested subSystems: is a ClassCastException in the real validator (RM091); refusing to
        # walk it here means generate never re-emits a reference we could not read.
        return entry.get("file"), entry.get("nodes") or {}

    for cand in (ref, os.path.splitext(os.path.basename(ref))[0]):
        sibling = os.path.join(base_dir, cand + ".rossystem")
        if not os.path.isfile(sibling):
            continue
        sub_model = ros_plot.extract_model(sibling, use_catalogue=False)
        out = {}
        for mn in sub_model["nodes"]:
            ifaces = {}
            for i in mn["interfaces"]:
                ifaces[i.get("ifaceName") or i["label"]] = i["kind"]
            out[mn["label"]] = {"from": mn.get("from"), "interfaces": ifaces}
        return None, out
    return None, {}


def _subsystem_project_nodes(ref, sub_nodes, nid):
    """Materialise a resolved subsystem's nodes as read-only project nodes (`backing: "sub"`).

    They are ordinary members of project["nodes"] so that a connection endpoint stays one
    (node id, iface id) pair everywhere -- the label/name split this whole model rests on --
    but emit_rossystem skips them in the `nodes:` block: re-declaring a node the subsystem
    already provides is RM090.
    """
    index = L.load_node_index() or {}
    out = []
    for label in sorted(sub_nodes):
        info = sub_nodes[label] or {}
        frm = info.get("from") or ""
        pkg, _, node_name = frm.partition(".")
        cat = index.get(frm) or {}
        ifaces = []
        for name, kind in sorted((info.get("interfaces") or {}).items()):
            if kind not in ARROW_KINDS:
                continue
            # `exposed` is False on purpose: this file does not expose them, the referenced one
            # does. _exposure_labels still labels the ones a connection touches, which is what
            # decides whether the connections: block can name them.
            ifaces.append({"id": nid("i"), "name": name, "kind": kind, "type": None,
                           "qos": None, "label": name, "exposed": False})
        out.append({"id": nid("n"), "label": label, "backing": "sub", "subRef": ref,
                    "pkg": pkg, "node": node_name or label,
                    "artifact": cat.get("artifact") or node_name or label,
                    "catalogueFile": cat.get("file"), "namespace": None,
                    "x": 0, "y": 0, "ifaces": ifaces, "params": []})
    return out


SEED_GLOBS = ["*.ros2", "rosnodes/*.ros2", "nodes/*.ros2", "*/*.ros2"]
SEED_ROS_GLOBS = ["*.ros", "msgs/*.ros", "rosnodes/*.ros", "nodes/*.ros", "*/*.ros"]


def _drop_catalogued_types(types):
    """Keep only the specs the project is allowed to (re)define, and say how many it dropped.

    A .ros sitting in the tree is very often a VENDORED message package -- the same nine
    packages `_deps/common_msgs.ros` carries. Those are already in assets/roscommonobjects and
    collect_deps stages them for the oracle run, so copying their definitions into the project
    would make `generate` write a second Package_Impl with the same name (RM009, "every
    '<name>/msg/<Type>' qualified name ambiguous").

    The filter is per PACKAGE, not per type: one extra spec in an otherwise catalogued package
    still makes `generate` write a whole second <pkg>.ros. _validate_types() applies the same
    rule to what the author types into the editor, so seeding and authoring cannot disagree
    about which packages are this project's to own."""
    owned = _catalogue_packages()
    kept, dropped = {}, 0
    for key, spec in types.items():
        if str(key).split("/")[0] in owned:
            dropped += 1
        else:
            kept[key] = spec
    return kept, dropped


def seed_from_rossystem(path, base_index=None):
    """Build a project dict from an existing .rossystem plus its sibling .ros2/.ros files.

    `base_index` is the multi-file seeder's shared workspace index, (ros2_index, pkg_git,
    types); the file's OWN directory is indexed on top of it, so a sibling always beats a
    namesake found elsewhere in the tree. Left None, the behaviour is exactly the single-file
    one: only this file's directory and the three conventional subdirs are opened.
    """
    model = ros_plot.extract_model(path, use_catalogue=True)
    base_dir = os.path.dirname(os.path.abspath(path))

    workspace = base_index or ({}, {}, {})

    # index every .ros2 in the system directory and one level of common subdirs
    ros2_index, pkg_git = dict(workspace[0]), dict(workspace[1])
    ros2_cmts, ros2_drops, dropped = {}, {}, []
    seen = set()
    for g in SEED_GLOBS:
        for f in glob.glob(os.path.join(base_dir, g)):
            f = os.path.abspath(f)
            if f in seen:
                continue
            seen.add(f)
            idx, git = parse_ros2(f)
            ros2_index.update(idx)
            pkg_git.update(git)
            scanned = scan_ros2_comments(f)
            ros2_cmts.update(scanned["packages"])
            # held per file, not merged: a .ros2 sitting in the directory that no node in this
            # system references contributes nothing to generation, so its comments are not
            # "dropped by us" and reporting them would be noise.
            ros2_drops[f] = (list(scanned["packages"].keys()),
                             [(os.path.basename(f),) + d for d in scanned["dropped"]])

    # Message FIELDS. Without this a sibling .ros was read by nothing, so a `generate` that
    # regenerated it wrote back the type NAMES with empty bodies -- STATUS.md sec 8 defect 2,
    # the same silent loss the exposure label fix closed one level up.
    ros_types = dict(workspace[2])
    ros_extras = []
    for g in SEED_ROS_GLOBS:
        for f in sorted(glob.glob(os.path.join(base_dir, g))):
            found, extras = parse_ros(os.path.abspath(f))
            ros_types.update(found)
            ros_extras += [(os.path.basename(f), ln, txt) for _p, ln, txt in extras]
    ros_types, ros_catalogued = _drop_catalogued_types(ros_types)
    ros_extras.sort()

    # comments live in the source TEXT, which the YAML compose path above throws away
    sys_cmts = scan_rossystem_comments(path)
    dropped += [(os.path.basename(path),) + d for d in sys_cmts["dropped"]]

    uid = [0]

    def nid(prefix):
        uid[0] += 1
        return "%s%d" % (prefix, uid[0])

    nodes = []
    diagnostics_extra = []
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

        # Attach the captured comments. The .rossystem side is keyed by the exposure LABEL and
        # the .ros2 side by (block, interface name): the same two identities the emitter writes
        # back out, so a comment cannot drift onto a different element across a round-trip.
        ncmt = sys_cmts["nodes"].get(mn["label"]) or {}
        acmt = {}
        if rec is not None:
            acmt = ((ros2_cmts.get(pkg) or {}).get("artifacts") or {}).get(artifact) or {}
        used_sys_ifaces = set()
        for f in ifaces:
            lbl = f.get("label") or ""
            sc = (ncmt.get("ifaces") or {}).get(lbl) or {}
            if sc:
                used_sys_ifaces.add(lbl)
            rc = (acmt.get("ifaces") or {}).get((C.KIND_TO_BLOCK[f["kind"]], f["name"])) or {}
            cmt = _comments({"before": sc.get("before"), "line": sc.get("line"),
                             "ros2Before": rc.get("before"), "ros2Line": rc.get("line"),
                             "ros2Type": rc.get("type")})
            if cmt:
                f["comments"] = cmt
        for p in params:
            rc = (acmt.get("params") or {}).get(p["name"]) or {}
            cmt = _comments({"ros2Before": rc.get("before"), "ros2Line": rc.get("line")})
            if cmt:
                p["comments"] = cmt
        for lbl, sc in sorted((ncmt.get("ifaces") or {}).items()):
            if lbl in used_sys_ifaces:
                continue
            texts = _comment_list(sc.get("before"))
            if sc.get("line"):
                texts.append(sc["line"])
            for text in texts:
                dropped.append((os.path.basename(path), 0,
                                "exposure '%s' of node '%s', which this project does not model"
                                % (lbl, mn["label"]), text))

        # `namespace:` is an optional RosNode member (RosSystem.xtext:64) that ros_plot has
        # always read and ros_studio used to drop on the floor -- the same silent data loss as
        # the exposure label, and the one that matters for a multi-robot system.
        node = {"id": nid("n"), "label": mn["label"], "backing": backing,
                "pkg": pkg or "", "node": node_name or mn["label"],
                "artifact": artifact, "catalogueFile": cat_file,
                "namespace": mn.get("namespace"),
                "x": 0, "y": 0, "ifaces": ifaces, "params": params}
        cmt = _comments({"before": ncmt.get("before"), "line": ncmt.get("line"),
                         "from": ncmt.get("from"),
                         "ros2Before": acmt.get("before"), "ros2Line": acmt.get("line")})
        if cmt:
            node["comments"] = cmt
        nodes.append(node)
        node_by_modelid[mn["id"]] = node

    # `subSystems:` reuses a whole pre-built composition. Its nodes are NOT in this file's
    # nodes: block, so ros_plot resolved every connection endpoint that lands on one to a
    # ghost -- and the seeder dropped those connections. On the TurtleBot 3 example that was 6
    # of 9, silently, with `generate` still reporting "0 error(s)": the same class of loss the
    # exposure LABEL fix closed, arriving through a different door.
    sub_systems, sub_exposure = [], {}
    for sub in model["subSystems"]:
        ref = sub["ref"]
        cat_file, sub_nodes = resolve_subsystem(ref, base_dir)
        entry = {"ref": ref, "file": cat_file}
        cmt = _comments(sys_cmts["subSystems"].get(ref) or {})
        if cmt:
            entry["comments"] = cmt
        sub_systems.append(entry)
        made = _subsystem_project_nodes(ref, sub_nodes, nid)
        if not made:
            diagnostics_extra.append(
                "subSystems: '%s' exposes nothing this project could resolve — any connection "
                "naming one of its interfaces cannot be re-linked and will NOT be re-emitted. "
                "The reference itself is preserved." % ref)
        for n in made:
            nodes.append(n)
            for f in n["ifaces"]:
                # a connections: endpoint resolves by name only -- there is no artifact-
                # qualified form -- so a label two subsystem nodes both declare (turtlebot's
                # "tf") is genuinely ambiguous (RM065). Bind the first in sorted node order:
                # either binding emits the identical connections: line, so the choice only has
                # to be deterministic.
                sub_exposure.setdefault(f["name"], (n, f))

    # rebuild connections from the model edges, resolving label -> (node, iface)
    conns, used_conns = [], set()
    for e in model["edges"]:
        fn = node_by_modelid.get(e["fromNode"])
        tn = node_by_modelid.get(e["toNode"])
        fi = _match_iface(fn, e["fromLabel"], e.get("kind")) if fn else None
        ti = _match_iface(tn, e["toLabel"], None) if tn else None
        if not (fn and fi):
            fn, fi = sub_exposure.get(e["fromLabel"], (None, None))
        if not (tn and ti):
            tn, ti = sub_exposure.get(e["toLabel"], (None, None))
        if fn and ti and fi and tn:
            conn = {"id": nid("c"), "from": {"n": fn["id"], "i": fi["id"]},
                    "to": {"n": tn["id"], "i": ti["id"]}}
            # a connection has no name of its own -- the LABEL PAIR is its identity, in the
            # source and in emit_rossystem alike, so that is the key the comments hang off.
            key = (e["fromLabel"], e["toLabel"])
            cc = sys_cmts["connections"].get(key)
            if cc is not None:
                used_conns.add(key)
                cmt = _comments({"before": cc.get("before"), "line": cc.get("line")})
                if cmt:
                    conn["comments"] = cmt
            conns.append(conn)
    for key, cc in sorted(sys_cmts["connections"].items()):
        if key in used_conns:
            continue
        texts = _comment_list(cc.get("before"))
        if cc.get("line"):
            texts.append(cc["line"])
        for text in texts:
            dropped.append((os.path.basename(path), 0,
                            "connection [%s, %s], which this project does not model"
                            % key, text))

    _grid_layout(nodes)
    packages = {}
    for n in nodes:
        if n["backing"] != "hand" or not n["pkg"]:
            continue
        entry = {"fromGitRepo": pkg_git.get(n["pkg"])}
        cmt = _comments({"header": (ros2_cmts.get(n["pkg"]) or {}).get("header")})
        if cmt:
            entry["comments"] = cmt
        packages[n["pkg"]] = entry
    used_pkgs = set(packages)
    for f, (pkgs, drops) in sorted(ros2_drops.items()):
        if used_pkgs.intersection(pkgs):
            dropped += drops

    for label in sorted(set(sys_cmts["nodes"]) - set(n["label"] for n in nodes)):
        nc = sys_cmts["nodes"][label]
        texts = _comment_list(nc.get("before"))
        for slot in ("line", "from"):
            if nc.get(slot):
                texts.append(nc[slot])
        for text in texts:
            dropped.append((os.path.basename(path), 0,
                            "node '%s', which this project does not model" % label, text))

    # ros_plot's _resolve() only knows this file's own nodes:, so it reports every subSystems:
    # endpoint as "dangling" -- true for the read-only viewer, false here now that the reference
    # is resolved. Matched on the label it names rather than on the whole sentence, so a reword
    # in ros_plot drops the filter (noisy) instead of silencing a real dangling endpoint.
    diagnostics = [d for d in model.get("diagnostics", [])
                   if not any("endpoint '%s' matches no declared interface" % lbl in d
                              for lbl in sub_exposure)]
    diagnostics += diagnostics_extra
    if ros_catalogued:
        diagnostics.append(
            "%d spec(s) in the sibling .ros file(s) belong to packages the vendored type "
            "catalogue owns; their definitions are NOT copied into the project (redeclaring a "
            "catalogued package is RM009). Only locally invented types are editable here."
            % ros_catalogued)
    for fname, line, text in ros_extras:
        diagnostics.append(
            "%s:%d  '%s' is a .ros package member this project has no slot for; it will NOT "
            "be re-emitted." % (fname, line, text))
    diagnostics += _dropped_comment_diagnostics(dropped)

    project = {
        # 3: elements carry a `comments` object (see the comment policy above) and the system
        # carries `subSystems`. 4: `types` carries the message FIELDS of locally defined specs
        # (and a merged project carries `seededFromAll`). An older project simply has none of
        # them and loads unchanged -- every reader below uses .get() with an empty default.
        "formatVersion": 4,
        "system": {"name": model["systemName"], "fromFile": model.get("fromFile")},
        "subSystems": sub_systems,
        "packages": packages,
        "types": ros_types,
        "nodes": nodes,
        "connections": conns,
        "seededFrom": os.path.abspath(path),
        "diagnostics": {"global": diagnostics, "byNode": {}},
    }
    cmt = _comments({"header": sys_cmts.get("header"), "fromFile": sys_cmts.get("fromFile")})
    if cmt:
        project["comments"] = cmt
    return project


# ========================================================================================
# Multi-file seeding
#
# `init` used to print "init seeds from the first file only; ignoring N more", so a system
# whose nodes live across directories could not be seeded at all. Everything below turns N
# .rossystem files (and/or a directory holding them) into ONE project.
#
# Three things make that more than a concatenation:
#   * ids are per-seed counters (n1, i1, ...), so two seeds collide on every one of them;
#   * a node LABEL is a key in the emitted nodes: block -- two of them is RM009, an ERROR;
#   * a system listed on the command line may ALSO be reached through another's subSystems:,
#     and declaring the same node both inline and by reference is RM090.
# ========================================================================================

def _iter_seed_sources(paths):
    """Expand init's arguments into (rossystem files, roots to index, missing arguments).

    A directory contributes every .rossystem beneath it; a plain file contributes itself. The
    result is sorted, so the merge order -- and therefore every disambiguated label the merge
    derives -- is the same on every machine and in every shell."""
    files, roots, missing = [], [], []
    for raw in paths:
        p = os.path.abspath(raw)
        if os.path.isdir(p):
            roots.append(p)
            for base, _dirs, names in os.walk(p):
                files += [os.path.join(base, n) for n in names if n.endswith(".rossystem")]
        elif os.path.isfile(p):
            files.append(p)
            roots.append(os.path.dirname(p))
        else:
            missing.append(raw)
    seen, uniq = set(), []
    for f in sorted(files):
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq, sorted(set(roots)), missing


def _index_workspace(roots):
    """(ros2_index, pkg_git, types) over whole directory TREES.

    seed_from_rossystem() only ever opened the seeded file's own directory plus rosnodes/,
    nodes/ and one level of '*/'. That is the reason a system whose artifacts sit in a sibling
    tree seeded every node as catalogue-backed or not at all. Walked in sorted order so a name
    that genuinely appears twice resolves the same way every run; the file's OWN directory is
    indexed on top of this afterwards, so a sibling always wins."""
    ros2_index, pkg_git, types = {}, {}, {}
    for root in roots:
        for base, dirs, names in os.walk(root):
            dirs.sort()
            for name in sorted(names):
                path = os.path.join(base, name)
                if name.endswith(".ros2"):
                    idx, git = parse_ros2(path)
                    ros2_index.update(idx)
                    pkg_git.update(git)
                elif name.endswith(".ros"):
                    found, _extras = parse_ros(path)
                    types.update(found)
    types, _dropped = _drop_catalogued_types(types)
    return ros2_index, pkg_git, types


def _unique_label(label, used, hint):
    """A node label that is free, derived from `label` and the system it came from. RM009 is an
    ERROR -- two nodes: keys with one name are two distinct RosNode objects answering to it --
    so a collision has to be renamed rather than reported and left."""
    if label not in used:
        return label
    cand = "%s_%s" % (label, _sanitise(hint))
    n = 2
    while cand in used:
        cand = "%s_%s_%d" % (label, _sanitise(hint), n)
        n += 1
    return cand


def _system_keys(project, path):
    """The names a `subSystems:` entry could use to reach this source: its system name and its
    file's basename. resolve_subsystem() accepts either, so the merge has to match on both or
    it collapses one spelling and not the other."""
    keys = {os.path.splitext(os.path.basename(path))[0]}
    name = (project.get("system") or {}).get("name")
    if name:
        keys.add(name)
    return keys


def seed_from_many(paths, roots=None, name=None):
    """Seed ONE project from several .rossystem files. `paths` is already expanded and sorted.

    The first source decides the system name (unless --name overrides), its fromFile and its
    file header: those are single-valued in a .rossystem, and inventing a fourth answer would
    be worse than adopting one and saying so. Everything dropped is reported, never silently
    discarded (SKILL.md rule 12).
    """
    workspace = _index_workspace(roots or sorted({os.path.dirname(p) for p in paths}))
    seeds = [(p, seed_from_rossystem(p, workspace)) for p in paths]

    uid = [0]

    def nid(prefix):
        uid[0] += 1
        return "%s%d" % (prefix, uid[0])

    first = seeds[0][1]
    merged = blank_project(name or first["system"].get("name") or "merged_system")
    merged["system"]["fromFile"] = first["system"].get("fromFile")
    if first.get("comments"):
        merged["comments"] = first["comments"]
    diags = []
    for path, project in seeds:
        base = os.path.basename(path)
        for d in project.get("diagnostics", {}).get("global", []):
            diags.append("%s: %s" % (base, d))

    # --- pass A: every real node, re-identified and de-duplicated by label ----------------
    label_used = set()
    node_map = {}          # (source index, old node id) -> merged node
    iface_map = {}         # (source index, old node id, old iface id) -> merged iface
    real_index = {}        # system key -> {label: merged node}
    for si, (path, project) in enumerate(seeds):
        sysname = project["system"].get("name") or os.path.basename(path)
        for n in project["nodes"]:
            if n.get("backing") == "sub":
                continue
            new = dict(n)
            new["id"] = nid("n")
            label = _unique_label(n["label"], label_used, sysname)
            if label != n["label"]:
                diags.append("%s: node '%s' collides with one already merged and was renamed "
                             "to '%s' (two nodes: keys with one name is RM009). Its "
                             "connections follow the rename."
                             % (os.path.basename(path), n["label"], label))
            label_used.add(label)
            new["label"] = label
            new["ifaces"] = []
            for f in n.get("ifaces") or []:
                nf = dict(f)
                nf["id"] = nid("i")
                new["ifaces"].append(nf)
                iface_map[(si, n["id"], f["id"])] = nf
            new["params"] = [dict(p, id=nid("p")) for p in n.get("params") or []]
            merged["nodes"].append(new)
            node_map[(si, n["id"])] = new
            for key in _system_keys(project, path):
                real_index.setdefault(key, {})[n["label"]] = new

    # --- pass B: subSystems: shadows -----------------------------------------------------
    # A shadow is a read-only stand-in (backing "sub") for a node the referenced file declares,
    # and emit_rossystem deliberately writes none of them: the referenced file provides them.
    # So if a source on the command line IS that referenced file, the same node would be
    # declared twice -- RM090 -- and the fix is to keep the real node, drop the reference, and
    # re-point every endpoint that named the shadow.
    #
    # Decided per REF before any folding: collapsing a reference whose nodes only PARTLY
    # resolve would drop the entry and leave an unemittable shadow behind.
    resolvable, unresolved = {}, set()
    for si, (path, project) in enumerate(seeds):
        for n in project["nodes"]:
            if n.get("backing") != "sub":
                continue
            ref = n.get("subRef") or ""
            hit = None
            for key in (ref, os.path.splitext(os.path.basename(ref))[0]):
                hit = (real_index.get(key) or {}).get(n["label"])
                if hit is not None:
                    break
            if hit is None:
                unresolved.add(ref)
            else:
                resolvable[(ref, n["label"])] = hit
    collapsed = {ref for ref, _lbl in resolvable if ref not in unresolved}

    shadow = {}
    for si, (path, project) in enumerate(seeds):
        for n in project["nodes"]:
            if n.get("backing") != "sub":
                continue
            ref = n.get("subRef") or ""
            target = resolvable.get((ref, n["label"])) if ref in collapsed else None
            if target is None:
                target = shadow.get((ref, n["label"]))
            if target is None:
                new = dict(n)
                new["id"] = nid("n")
                label = _unique_label(n["label"], label_used, ref)
                label_used.add(label)
                new["label"] = label
                new["ifaces"] = []
                for f in n.get("ifaces") or []:
                    nf = dict(f)
                    nf["id"] = nid("i")
                    new["ifaces"].append(nf)
                    iface_map[(si, n["id"], f["id"])] = nf
                new["params"] = []
                merged["nodes"].append(new)
                node_map[(si, n["id"])] = new
                shadow[(ref, n["label"])] = new
                continue
            # fold: bind this shadow's interfaces to the target's by NAME, which is the only
            # identity a connections: endpoint has (there is no artifact-qualified form).
            node_map[(si, n["id"])] = target
            by_name = {}
            for tf in target["ifaces"]:
                by_name.setdefault(tf["name"], tf)
            for f in n.get("ifaces") or []:
                tf = by_name.get(f["name"])
                if tf is not None:
                    iface_map[(si, n["id"], f["id"])] = tf

    # --- pass C: connections --------------------------------------------------------------
    seen_conn = set()
    for si, (path, project) in enumerate(seeds):
        for c in project.get("connections") or []:
            fn = node_map.get((si, c["from"]["n"]))
            tn = node_map.get((si, c["to"]["n"]))
            ff = iface_map.get((si, c["from"]["n"], c["from"]["i"]))
            tf = iface_map.get((si, c["to"]["n"], c["to"]["i"]))
            if not (fn and tn and ff and tf):
                diags.append("%s: a connection could not be re-linked after the merge and was "
                             "NOT carried over (an endpoint's node or interface did not "
                             "survive)." % os.path.basename(path))
                continue
            key = (fn["id"], ff["id"], tn["id"], tf["id"])
            if key in seen_conn:
                continue                      # the same edge reached through two sources
            seen_conn.add(key)
            new = dict(c)
            new["id"] = nid("c")
            new["from"] = {"n": fn["id"], "i": ff["id"]}
            new["to"] = {"n": tn["id"], "i": tf["id"]}
            merged["connections"].append(new)

    # --- pass D: subSystems entries, packages, types ---------------------------------------
    seen_ref = set()
    for path, project in seeds:
        for s in project.get("subSystems") or []:
            if s["ref"] in collapsed:
                diags.append("%s: subSystems: '%s' names a system this merge also carries "
                             "inline, so the reference was DROPPED and its endpoints re-linked "
                             "onto the merged nodes — declaring a node both here and by "
                             "reference is RM090." % (os.path.basename(path), s["ref"]))
                continue
            if s["ref"] in seen_ref:
                continue
            seen_ref.add(s["ref"])
            merged["subSystems"].append(s)
        for pkg, entry in sorted((project.get("packages") or {}).items()):
            if pkg not in merged["packages"]:
                merged["packages"][pkg] = entry
            elif merged["packages"][pkg] != entry:
                diags.append("%s: package '%s' is described differently by two sources; the "
                             "first one merged wins (fromGitRepo %r)."
                             % (os.path.basename(path), pkg,
                                merged["packages"][pkg].get("fromGitRepo")))
        for key, spec in sorted((project.get("types") or {}).items()):
            if key not in merged["types"]:
                merged["types"][key] = spec
            elif merged["types"][key] != spec:
                diags.append("%s: message type '%s' is defined differently by two sources; the "
                             "first one merged wins." % (os.path.basename(path), key))

    for path, project in seeds[1:]:
        if project["system"].get("fromFile") and (project["system"]["fromFile"]
                                                  != merged["system"]["fromFile"]):
            diags.append("%s: fromFile %r was dropped — a .rossystem has exactly one, and the "
                         "merge adopted the first source's."
                         % (os.path.basename(path), project["system"]["fromFile"]))
        if project.get("comments"):
            diags.append("%s: its file header comment was dropped — the merged file carries "
                         "the first source's." % os.path.basename(path))

    _grid_layout(merged["nodes"])
    merged["seededFrom"] = os.path.abspath(paths[0])
    merged["seededFromAll"] = [os.path.abspath(p) for p in paths]
    merged["diagnostics"] = {"global": [
        "merged %d .rossystem file(s) into one project: %s. The system is named '%s' (%s)."
        % (len(paths), ", ".join(os.path.basename(p) for p in paths),
           merged["system"]["name"],
           "--name" if name else "adopted from the first source")] + diags, "byNode": {}}
    return merged


def _dropped_comment_diagnostics(dropped, limit=12):
    """SKILL.md rule 12: a comment the emitter will not reproduce must be REPORTED, never
    silently discarded. One line per comment, naming the file, the line and what it annotated,
    so the author can re-place it by hand instead of discovering the loss in a diff."""
    if not dropped:
        return []
    out = ["%d comment(s) could not be attached to a model element and will NOT be re-emitted "
           "(see commands/ros-studio.md for which positions are preserved):" % len(dropped)]
    for item in dropped[:limit]:
        fname, line, what, text = item
        where = "%s:%d" % (fname, line) if line else fname
        out.append("  %s  on %s -- \"%s\"" % (where, what, _clean_comment(text)))
    if len(dropped) > limit:
        out.append("  … and %d more." % (len(dropped) - limit))
    return out


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
        "formatVersion": 4,
        "system": {"name": name, "fromFile": None},
        "subSystems": [],
        "packages": {},
        "types": {},
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


def _catalogue_packages():
    """Package names the vendored type catalogue owns. A locally DEFINED type in one of them
    would be written into a <pkg>.ros that collect_deps also stages from
    assets/roscommonobjects/ for the oracle run: two Package_Impl entries with one name, which
    makes every '<name>/msg/<Type>' qualified name ambiguous (RM009).

    Read off the entries that carry a `file`, which is exactly the map render_editor embeds as
    DATA.typeFiles -- so the page's companionTypes() cannot disagree with this about which
    packages the project owns."""
    idx = L.load_type_index() or {}
    return {k.split("/")[0] for k in idx if "/" in k and (idx[k] or {}).get("file")}


def _local_type_packages(project):
    """Packages a companion .ros may be written for: every hand-authored node's package, plus
    every package a locally DEFINED type names.

    The second half is what makes a type invented in the editor emittable at all. A definition
    is reached through project["types"], not through an interface, so a spec no interface
    happens to reference -- the inner type of a self-referencing message, say -- was collected
    by nothing and written nowhere."""
    pkgs = {n["pkg"] for n in project["nodes"] if n["backing"] == "hand" and n["pkg"]}
    for key in project.get("types") or {}:
        parts = str(key).split("/")
        if len(parts) == 3 and parts[0] and _type_catalogue_file(key) is None:
            pkgs.add(parts[0])
    return pkgs


def _companion_types(project):
    """Types that are NOT in the type catalogue but whose package is authored locally ->
    they need a companion .ros. Returns {package: {(block, TypeName)}}."""
    local_pkgs = _local_type_packages(project)
    out = {}
    for key in project.get("types") or {}:
        parts = str(key).split("/")
        if len(parts) != 3:
            continue
        pkg, seg, name = parts
        block = C.TYPE_SEG_TO_ROS_BLOCK.get(seg)
        if pkg in local_pkgs and block and _type_catalogue_file(key) is None:
            out.setdefault(pkg, set()).add((block, name))
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


def _type_auto_note(typ, companion_pkgs):
    """The RM089 disclosure BODY for a type reference (no '# '), or "" when the type resolves to
    nothing or we are about to emit its companion .ros. _note_suffix() merges it with whatever
    the author wrote on that line, so the disclosure survives an edit."""
    if not typ or "/" not in typ:
        return ""
    pkg = typ.split("/")[0]
    if pkg in companion_pkgs:
        return ""
    rel = _type_catalogue_file(typ)
    return "assets/roscommonobjects/%s" % rel if rel else ""


def _fold_artifacts(recs):
    """Collapse node records that name the SAME artifact into one artifact block.

    Two `.rossystem` nodes may legitimately share a `from: pkg.ARTIFACT` -- two instances of
    one node type, and after a multi-file merge two systems reusing the same package almost
    always do. The artifact is one definition either way, so emitting it once per referring
    node produced a duplicate key: RM009, and a file the language server rejects.

    Interfaces and parameters are UNIONED, keyed by (kind, name) and name, because each
    referring node exposes only the subset it wires and the artifact must declare all of
    them. First writer wins on a collision, and validate_project reports the disagreement
    before anything is written -- see the artifact-conflict gate."""
    folded, order = {}, []
    for rec in recs:
        key = rec["artifact"]
        if key not in folded:
            folded[key] = dict(rec, ifaces=list(rec.get("ifaces") or []),
                               params=list(rec.get("params") or []))
            order.append(key)
            continue
        into = folded[key]
        have = {(f["kind"], f["name"]) for f in into["ifaces"]}
        for f in rec.get("ifaces") or []:
            if (f["kind"], f["name"]) not in have:
                have.add((f["kind"], f["name"]))
                into["ifaces"].append(f)
        have_p = {p["name"] for p in into["params"]}
        for p in rec.get("params") or []:
            if p["name"] not in have_p:
                have_p.add(p["name"])
                into["params"].append(p)
    return [folded[k] for k in order]


def emit_ros2(package, git, art_records, companion_pkgs, pkg_comments=None):
    """One AmentPackage block with N artifacts (sorted). art_records: list of node dicts."""
    lines = _comment_block((pkg_comments or {}).get("header"), "")
    lines.append(package + ":")
    if git:
        lines.append("  fromGitRepo: " + _q_double(git))
    lines.append("  artifacts:")
    for node in sorted(art_records, key=lambda n: n["artifact"]):
        nc = node.get("comments") or {}
        lines.extend(_comment_block(nc.get("ros2Before"), "    "))
        lines.append("    " + node["artifact"] + ":" + _note_suffix(nc.get("ros2Line")))
        lines.append("      node: " + node["node"])
        for kind in ARROW_KINDS:
            group = sorted([f for f in node["ifaces"] if f["kind"] == kind],
                           key=lambda f: f["name"])
            if not group:
                continue
            lines.append("      " + C.KIND_TO_BLOCK[kind] + ":")
            for f in group:
                fc = f.get("comments") or {}
                lines.extend(_comment_block(fc.get("ros2Before"), "        "))
                lines.append("        " + _q_single(f["name"]) + ":"
                             + _note_suffix(fc.get("ros2Line")))
                typ = f.get("type") or "TODO_pkg/msg/Type"
                lines.append("          type: " + _q_single(typ)
                             + _note_suffix(fc.get("ros2Type"),
                                            _type_auto_note(typ, companion_pkgs)))
                _emit_qos(lines, f.get("qos"), "          ")
        params = node.get("params") or []
        if params:
            lines.append("      parameters:")
            for p in sorted(params, key=lambda p: p["name"]):
                pc = p.get("comments") or {}
                lines.extend(_comment_block(pc.get("ros2Before"), "        "))
                lines.append("        " + _q_single(p["name"]) + ":"
                             + _note_suffix(pc.get("ros2Line")))
                lines.append("          type: " + (p.get("ptype") or "String"))
                lines.append("          default: " + _fmt_param_value(p.get("ptype"),
                                                                      p.get("value")))
    return "\n".join(lines) + "\n"


def _emit_qos(lines, qos, indent):
    """Emit a qos: block if the interface carries one. Durations are quoted int-ns or
    'infinite' per the grammar; enums are bare keywords."""
    if not qos or not isinstance(qos, dict):
        return
    body = []
    for key in L.QOS_PINNED:
        if key not in qos or qos[key] in (None, ""):
            continue
        val = str(qos[key])
        if key in QOS_DURATIONS:
            # 'infinite' is a grammar KEYWORD in (EString | 'infinite'), not an EString.
            # Quoting it used to be unconditional here, which made every `deadline: infinite`
            # come back out as deadline: "infinite" -- an RM035 ERROR ("not an integer
            # string"), so `generate` refused its own output. (The 3.1.0 server accepts the
            # quoted form, so this never showed up in an --oracle run; only the linter caught
            # it, and only once the field became editable.)
            if val != "infinite":
                val = _q_double(val)
        body.append(indent + "  " + key + ": " + val)
    # a dict whose every value is blank must not open a bodiless `qos:` -- that is a parse
    # error, and the editor can produce such a dict by clearing the last field.
    if body:
        lines.append(indent + "qos:")
        lines.extend(body)


def _companion_ros(package, blocks, types=None):
    """A .ros for locally-invented types, WITH the message fields the project defines.

    A bodiless spec is legal -- '(BEGIN message=MessageDefinition END)?' is optional, hence
    RM080 INFO and not an error -- but when the source defined fields it is silent data loss
    (STATUS.md sec 8 defect 2: a regenerated .ros came back with type names and no fields).
    The emitted form with its fields is oracle-ACCEPTED, 0 errors (case 10, ours-turtlesim-msgs).

    Layout is the four-BEGIN ladder of ros2-syntax.md 11: package 0 / block 2 / spec name 4
    (no trailing ':' -- the one named element in the language without one) / body keyword 6 /
    field 8. Every body keyword of the block is written even when it has no fields, because
    Ros.xtext:81-104 makes the keyword itself mandatory and only its indented body optional
    (a bodiless `response` is the normal shape, RM073)."""
    types = types or {}
    lines = [package + ":"]
    by_block = {}
    for block, name in sorted(blocks):
        by_block.setdefault(block, []).append(name)
    for block in L.ROS_SPEC_BLOCKS:              # msgs, srvs, actions
        if block not in by_block:
            continue
        lines.append("  " + block + ":")
        seg = ROS_BLOCK_TO_TYPE_SEG[block]
        for name in sorted(by_block[block]):
            lines.append("    " + name)
            fields = ((types.get("%s/%s/%s" % (package, seg, name)) or {}).get("fields")) or {}
            for body in L.ROS_SPEC_BODIES[block]:   # message / request+response / goal...
                lines.append("      " + body)
                for f in fields.get(body) or []:
                    typ = str(f.get("type") or "").strip()
                    fname = str(f.get("name") or "").strip()
                    # One field per line. MessagePart+=MessagePart* has no line separator so
                    # several per line PARSE (RM078 is a warning), but emission-profile rule 2
                    # says readable; a half-filled row is blocked by validate_project, never
                    # dropped here.
                    if typ and fname:
                        lines.append("        " + typ + " " + fname)
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

    # pass 0: a `subSystems:` node's exposure label belongs to the REFERENCED file. It cannot be
    # renamed here -- it is the exact string a connections: endpoint has to spell -- so it claims
    # its name before any local exposure can take it. Two subsystem nodes declaring the same
    # label (turtlebot's "tf") both map to that one string: that ambiguity is the source file's
    # (RM065), and inventing a distinguishing label here would emit an endpoint that resolves to
    # nothing.
    for n, f in wanted:
        if n.get("backing") != "sub":
            continue
        lbl = (f.get("label") or f.get("name") or "").strip()
        if lbl:
            labels[(n["id"], f["id"])] = lbl
            used.add(lbl)

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
    pc = project.get("comments") or {}
    sysname = project["system"].get("name") or "system"
    lines = _comment_block(pc.get("header"), "")
    lines.append(sysname + ":")
    from_file = project["system"].get("fromFile")
    if from_file:
        lines.append("  fromFile: " + _q_double(from_file) + _note_suffix(pc.get("fromFile")))
    # ROSSYSTEM_TOP_KEYS: fromFile -> subSystems -> processes -> nodes -> parameters ->
    # connections (rule 25). 'components+=SubSystem*' is a repetition, so each entry is one bare
    # (optionally quoted) EString on its own indented line -- there is no bracket form (RM093).
    subs = project.get("subSystems") or []
    if subs:
        lines.append("  subSystems:")
        for s in subs:
            sc = s.get("comments") or {}
            lines.extend(_comment_block(sc.get("before"), "    "))
            auto = "assets/rosmodelscatalog/%s" % s["file"] if s.get("file") else ""
            lines.append("    " + _q_double(s["ref"]) + _note_suffix(sc.get("line"), auto))
    lines.append("  nodes:")
    for n in project["nodes"]:
        # provided by the subSystems: block above -- re-declaring it under this file's own
        # nodes: is RM090 ("two distinct RosNode objects answer to the same name").
        if n.get("backing") == "sub":
            continue
        nc = n.get("comments") or {}
        lines.extend(_comment_block(nc.get("before"), "    "))
        lines.append("    " + _q_double(n["label"]) + ":" + _note_suffix(nc.get("line")))
        from_val = "%s.%s" % (n["pkg"], n["node"])
        auto = ""
        if n["backing"] == "cat" and n.get("catalogueFile"):
            auto = "assets/rosmodelscatalog/%s" % n["catalogueFile"]
        lines.append("      from: " + _q_double(from_val)
                     + _note_suffix(nc.get("from"), auto))
        # ROSSYSTEM_NODE_KEYS fixes from -> namespace -> interfaces -> parameters
        # (RosSystem.xtext:60-75); emitting it anywhere else is RM039. The value is a plain
        # EString, so it is quoted like every other EString we write.
        ns = (n.get("namespace") or "").strip()
        if ns:
            lines.append("      namespace: " + _q_double(ns))
        exposed = [f for f in n["ifaces"] if (n["id"], f["id"]) in labels]
        exposed.sort(key=lambda f: (ARROW_KINDS.index(f["kind"]), f["name"]))
        if exposed:
            lines.append("      interfaces:")
            for f in exposed:
                fc = f.get("comments") or {}
                lbl = labels[(n["id"], f["id"])]
                tgt = "%s::%s" % (n["artifact"], f["name"])
                lines.extend(_comment_block(fc.get("before"), "        "))
                lines.append("        - " + _q_double(lbl) + ": " + f["kind"] + "-> "
                             + _q_double(tgt) + _note_suffix(fc.get("line")))
    if project["connections"]:
        lines.append("  connections:")
        for c in project["connections"]:
            fl = labels.get((c["from"]["n"], c["from"]["i"]))
            tl = labels.get((c["to"]["n"], c["to"]["i"]))
            if fl and tl:
                cc = c.get("comments") or {}
                lines.extend(_comment_block(cc.get("before"), "    "))
                lines.append("    - [" + _q_double(fl) + ", " + _q_double(tl) + "]"
                             + _note_suffix(cc.get("line")))
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
    """The interface's own type, or -- for a catalogue- or subSystems-backed node whose
    interface is type-less -- the type recovered from the catalogue .ros2. Empty string when
    genuinely unknown. A `sub` node is included because node_index carries only the kind for a
    subsystem's exposures, so without this every connection to one would slip past the
    same-type gate that the language server does enforce."""
    t = (iface.get("type") or "").strip()
    if t:
        return t
    if node.get("backing") in ("cat", "sub") and node.get("catalogueFile"):
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

    # B3: an empty `nodes:` block is "missing RULE_BEGIN" to the server. Counted over the nodes
    # that are actually WRITTEN into it: a `subSystems:` node is skipped by emit_rossystem, so a
    # project holding only those would still open a bodiless nodes: block here.
    if not [n for n in project.get("nodes") or [] if n.get("backing") != "sub"]:
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

    # Two nodes may share one `from: pkg.ARTIFACT` (see _fold_artifacts), and the .ros2 then
    # carries one artifact block for both. That is only safe while they agree about it: if one
    # says 'scan' is a LaserScan and the other says Odometry, folding silently keeps the first
    # and the second node's interface quietly changes type. Report instead.
    seen_art = {}
    for n in project.get("nodes", []):
        if n.get("backing") != "hand" or not n.get("pkg"):
            continue
        key = (n["pkg"], n.get("artifact"))
        first = seen_art.setdefault(key, n)
        if first is n:
            continue
        if first.get("node") != n.get("node"):
            flag(n["id"], "node '%s' and '%s' both declare artifact '%s.%s' but name different "
                          "ROS nodes (%r vs %r) — one artifact cannot be both."
                 % (first.get("label", "?"), n.get("label", "?"), n["pkg"], n.get("artifact"),
                    first.get("node"), n.get("node")))
        types = {(f["kind"], f["name"]): f.get("type") for f in first.get("ifaces") or []}
        for f in n.get("ifaces") or []:
            other = types.get((f["kind"], f["name"]))
            if other is not None and f.get("type") and other != f.get("type"):
                flag(n["id"], "interface '%s' (%s) is %s here but %s on node '%s', which shares "
                              "artifact '%s.%s' — the generated .ros2 declares it once, so the "
                              "two must agree."
                     % (f.get("name", "?"), f.get("kind", "?"), f.get("type"), other,
                        first.get("label", "?"), n["pkg"], n.get("artifact")))

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

    # A hand-authored interface whose type resolves NOWHERE -- not in the vendored catalogue and
    # not in a companion .ros this run writes. rosmodel_lint only warns (RM081/RM076: linking is
    # cross-file and it sees one file at a time), but the server answers "Couldn't resolve
    # reference to TopicSpec" and REJECTS. Reachable whenever the type's package differs from
    # the node's own -- 'foo_pkg' node publishing 'foo_msgs/msg/Bar' writes no foo_msgs.ros --
    # so the fix is to define the spec, which the message-types panel now allows.
    emitted = _emitted_type_names(project)
    for n in project.get("nodes", []):
        if n.get("backing") != "hand":
            continue
        for f in n.get("ifaces", []):
            typ = (f.get("type") or "").strip()
            if not typ or typ.startswith("TODO") or "/" not in typ:
                continue                      # already flagged above, or not a reference
            if typ in emitted or _type_catalogue_file(typ) is not None:
                continue
            flag(n["id"], "interface '%s' (%s) has type '%s', which neither the vendored "
                          "catalogue nor this project defines — the server cannot resolve it. "
                          "Define it under 'message types (.ros)', or use a catalogued type."
                          % (f.get("name", "?"), f.get("kind", "?"), typ))

    glob_errs += _validate_types(project)
    return {"global": glob_errs, "byNode": by_node}


def _emitted_type_names(project):
    """The qualified names of every spec a companion .ros this run writes will declare."""
    out = set()
    for pkg, blocks in _companion_types(project).items():
        for block, name in blocks:
            out.add("%s/%s/%s" % (pkg, ROS_BLOCK_TO_TYPE_SEG[block], name))
    return out


def _validate_types(project):
    """Pre-write gate for the locally DEFINED message specs (project["types"]).

    Everything rosmodel_lint checks about a .ros field line (RM074-RM077) is left to it -- it
    runs over the written file and `generate` refuses on its errors. Only the three the linter
    cannot decide from one file are enforced here, because each one ships a file the real
    language server rejects:

      * a half-filled row would simply not be emitted -> silent loss, the defect class this
        whole model exists to close;
      * a quoted SpecBaseRef that resolves neither in the catalogue nor in a companion this
        run writes is RM076, a WARNING (linking is cross-file, so the linter cannot see it) --
        but the oracle reports "Couldn't resolve reference to TopicSpec" as an ERROR, verified
        on a bare same-package name in ros2-syntax.md 11;
      * a definition in a package the catalogue also owns collides with the file collect_deps
        stages next to it (RM009).
    """
    out = []
    declared = project.get("types") or {}
    if not declared:
        return out
    local_pkgs = _local_type_packages(project)
    cat_pkgs = _catalogue_packages()
    emitted = _emitted_type_names(project)

    for key in sorted(declared):
        parts = str(key).split("/")
        if len(parts) != 3 or parts[1] not in C.TYPE_SEG_TO_ROS_BLOCK or not parts[0]:
            out.append("message type '%s' is not '<package>/<msg|srv|action>/<Name>' — "
                       "RosQNP.xtend qualifies every spec that way and no other shape can "
                       "ever link." % key)
            continue
        pkg, seg, name = parts
        if pkg in cat_pkgs:
            out.append("message type '%s' defines a spec in '%s', a package the vendored "
                       "catalogue owns — the generated %s.ros and the staged catalogue file "
                       "would both declare it (RM009). Use a package name of your own."
                       % (key, pkg, pkg))
            continue
        block = C.TYPE_SEG_TO_ROS_BLOCK[seg]
        for body in L.ROS_SPEC_BODIES[block]:
            for f in (declared[key].get("fields") or {}).get(body) or []:
                typ = str(f.get("type") or "").strip()
                fname = str(f.get("name") or "").strip()
                if not typ or not fname:
                    out.append("%s / %s: a field row is half-filled (type %r, name %r) — a "
                               "MessagePart is exactly two tokens, a Type then a Data "
                               "(Basics.xtext:201-204). Complete it or remove it; it would "
                               "not be written."
                               % (key, body, typ or "", fname or ""))
                    continue
                ref = typ[:-2] if typ.endswith("[]") else typ
                if not (len(ref) >= 2 and ref[0] == ref[-1] and ref[0] in "\"'"):
                    continue                     # primitive or malformed -> RM074/075, linter's
                inner = ref[1:-1]
                if inner in emitted or _type_catalogue_file(inner) is not None:
                    continue
                out.append("%s / %s: field '%s' references '%s', which neither the vendored "
                           "catalogue nor this project defines — the server answers "
                           "\"Couldn't resolve reference to TopicSpec\". Define it (its "
                           "package must be one of: %s) or point the field elsewhere."
                           % (key, body, fname, inner,
                              ", ".join(sorted(local_pkgs)) or "none yet"))
    return out


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
        entry = project.get("packages", {}).get(pkg) or {}
        files[pkg + ".ros2"] = emit_ros2(pkg, entry.get("fromGitRepo"), _fold_artifacts(recs),
                                         companion_pkgs, entry.get("comments"))

    for pkg, blocks in sorted(companions.items()):
        files[pkg + ".ros"] = _companion_ros(pkg, blocks, project.get("types"))

    files[project["system"].get("name", "system") + ".rossystem"] = emit_rossystem(project)
    return files


# ========================================================================================
# Model-level diff against the seed
#
# project.json carries `seededFrom`, so "what have I changed since the source .rossystem"
# is finally answerable -- and only became worth answering once the round-trip was lossless:
# before that a diff was dominated by spurious deletions (7 of 10 connections on the
# TurtleBot 3 example) and said nothing about the author's edits.
#
# A TEXT diff of the two files is unreadable and mostly false. The emitter fixes key order
# (ROSSYSTEM_TOP_KEYS / ROSSYSTEM_NODE_KEYS, rule 25), quotes every EString, sorts a node's
# interfaces by (kind, name) and its parameters by name, and re-places comments by the
# documented policy -- so a round-trip that changed NOTHING still rewrites most lines.
# Everything below instead reduces both sides to the SAME fact tree and diffs that:
#
#   {"system":      {"name","fromFile"},
#    "subSystems":  [ref, ...],
#    "nodes":       {label: {"from","namespace",
#                            "exposures":  {exposureLabel: "kind-> artifact::name"},
#                            "parameters": {label: value}}},
#    "connections": ["fromLabel -> toLabel", ...],
#    "packages":    {pkg: {"fromGitRepo",
#                          "artifacts": {artifact: {"node",
#                                                   "interfaces": {"kind name": type},
#                                                   "qos":        {"kind name": "k=v; ..."},
#                                                   "parameters": {name: "Type = default"}}}}},
#    "types":       {"pkg/seg/Name": {body: ["type name", ...]}}}
#
# Two builders produce it. source_facts() reads FILES with the same parsers `init` seeds
# from; project_facts() predicts what generation will write from the project alone. They are
# meant to agree exactly -- `diff` cross-checks them and says so if they do not, and
# tests/studio_parity.js holds project_facts() to source_facts(<generated>) on every fixture
# as well as to the editor's own projectFacts().
# ========================================================================================

_FACT_SECTIONS = ("system", "subSystems", "nodes", "connections", "packages", "types")


def _facts_tree():
    return {"system": {"name": "", "fromFile": ""}, "subSystems": [], "nodes": {},
            "connections": [], "packages": {}, "types": {}}


def _fact_str(v):
    """Every leaf of the tree is a STRING, so the two builders can never disagree about
    None-vs-"" or 1-vs-"1" for a value both sides ultimately read back out of a text file."""
    return "" if v is None else str(v)


def _qos_fact(qos):
    """A qos: block as one line, in the grammar's pinned field order (QOS_PINNED) -- the same
    order _emit_qos writes, so the parsed and the predicted form agree."""
    if not qos or not isinstance(qos, dict):
        return ""
    out = []
    for key in L.QOS_PINNED:
        val = qos.get(key)
        if val in (None, ""):
            continue
        out.append("%s=%s" % (key, val))
    return "; ".join(out)


def _unquote_emitted(s):
    """Undo one layer of the emitter's own quoting. The source side of the diff reads the
    default back through the YAML composer, which has already resolved the quote style and the
    \\\\ / \\" escapes _q_double writes, so the predicted side has to resolve them too or a
    String parameter containing a quote reads as a change on every run."""
    s = str(s)
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        inner = s[1:-1]
        return inner.replace("\\\\", "\x00").replace('\\"', '"').replace("\x00", "\\") \
            if s[0] == '"' else inner
    return s


def _param_fact(ptype, value):
    """`type` + `default` as one leaf, spelled the way the FILE spells it: the project side
    runs _fmt_param_value (which quotes a String) and then unquotes, because the source side
    reads through a parser that already did."""
    return "%s = %s" % (ptype or "String",
                        _unquote_emitted(_fmt_param_value(ptype, value)))


def _iface_fact_key(kind, name):
    return "%s %s" % (kind, name)


def source_facts(path):
    """Fact tree for an existing .rossystem plus the sibling .ros2/.ros files.

    Read through ros_plot.extract_model / parse_ros2 / parse_ros -- exactly the parsers
    seed_from_rossystem uses -- so a difference this reports is a model difference and never
    a parser disagreement between the two sides of the diff.

    Only the artifacts a node of THIS system actually resolves to are included: a stray .ros2
    sitting in the directory contributes nothing to generation, so counting it would report a
    removal the author never made. Same rule the seeder applies when it builds
    project["packages"].
    """
    facts = _facts_tree()
    model = ros_plot.extract_model(path, use_catalogue=True)
    base_dir = os.path.dirname(os.path.abspath(path))

    facts["system"] = {"name": _fact_str(model["systemName"]),
                       "fromFile": _fact_str(model.get("fromFile"))}
    facts["subSystems"] = [_fact_str(s["ref"]) for s in model.get("subSystems") or []]

    ros2_index, pkg_git = {}, {}
    seen = set()
    for g in SEED_GLOBS:
        for f in glob.glob(os.path.join(base_dir, g)):
            f = os.path.abspath(f)
            if f in seen:
                continue
            seen.add(f)
            idx, git = parse_ros2(f)
            ros2_index.update(idx)
            pkg_git.update(git)

    ros_types = {}
    for g in SEED_ROS_GLOBS:
        for f in sorted(glob.glob(os.path.join(base_dir, g))):
            found, _extras = parse_ros(os.path.abspath(f))
            ros_types.update(found)
    # A package the vendored catalogue owns is neither side's to change (redeclaring one is
    # RM009 and the seeder refuses to carry it), so it is excluded from BOTH sides rather than
    # reported as a wholesale deletion the author cannot act on.
    ros_types, _catalogued = _drop_catalogued_types(ros_types)
    for key, spec in ros_types.items():
        facts["types"][key] = {body: ["%s %s" % (f.get("type"), f.get("name"))
                                      for f in fields]
                               for body, fields in (spec.get("fields") or {}).items()}

    for mn in model["nodes"]:
        artifact = None
        for i in mn["interfaces"]:
            if i.get("artifact"):
                artifact = i["artifact"]
                break
        rec = {"from": _fact_str(mn.get("from")),
               "namespace": _fact_str(mn.get("namespace")),
               "exposures": {}, "parameters": {}}
        for i in mn["interfaces"]:
            rec["exposures"][i["label"]] = "%s-> %s" % (i.get("rawKind") or i["kind"],
                                                        _fact_str(i.get("target")))
        for p in mn.get("params") or []:
            rec["parameters"][p["label"]] = _fact_str(p.get("value"))
        facts["nodes"][mn["label"]] = rec

        pkg, node_name = mn.get("package"), mn.get("nodeName")
        art = None
        if pkg and node_name:
            art = ros2_index.get((pkg, node_name)) or (
                ros2_index.get((pkg, artifact)) if artifact else None)
        if art is None:
            continue                      # catalogue-backed or unresolved: writes no .ros2
        pentry = facts["packages"].setdefault(
            art["package"], {"fromGitRepo": _fact_str(pkg_git.get(art["package"])),
                             "artifacts": {}})
        arec = {"node": _fact_str(art["node"]), "interfaces": {}, "qos": {},
                "parameters": {}}
        for f in art["interfaces"]:
            key = _iface_fact_key(f["kind"], f["name"])
            arec["interfaces"][key] = _fact_str(f.get("type"))
            q = _qos_fact(f.get("qos"))
            if q:
                arec["qos"][key] = q
        for p in art["params"]:
            arec["parameters"][p["name"]] = _param_fact(p.get("ptype"), p.get("value"))
        pentry["artifacts"][art["artifact"]] = arec

    for e in model["edges"]:
        facts["connections"].append("%s -> %s" % (e["fromLabel"], e["toLabel"]))
    return facts


def project_facts(project):
    """The same fact tree, predicted from the project WITHOUT writing anything.

    This is the "after" side the editor previews, so it must describe what generation actually
    writes rather than what the project happens to hold. Three things are dropped on purpose,
    each mirroring an emitter rule:
      * a `backing == "sub"` node is provided by the subSystems: block, so emit_rossystem does
        not re-declare it (RM090);
      * a node-level `parameters:` block has no slot in the project at all, so nothing is
        emitted for it -- which is exactly the loss the diff exists to make visible;
      * only a hand-authored node's package produces a .ros2, and only a locally invented type
        produces a .ros.
    """
    facts = _facts_tree()
    facts["system"] = {"name": _fact_str(project["system"].get("name") or "system"),
                       "fromFile": _fact_str(project["system"].get("fromFile"))}
    facts["subSystems"] = [_fact_str(s["ref"]) for s in project.get("subSystems") or []]

    labels = _exposure_labels(project)
    for n in project["nodes"]:
        if n.get("backing") == "sub":
            continue
        rec = {"from": "%s.%s" % (n["pkg"], n["node"]),
               "namespace": _fact_str((n.get("namespace") or "").strip()),
               "exposures": {}, "parameters": {}}
        for f in n["ifaces"]:
            lbl = labels.get((n["id"], f["id"]))
            if lbl is None:
                continue
            rec["exposures"][lbl] = "%s-> %s::%s" % (f["kind"], n.get("artifact") or "",
                                                     f["name"])
        facts["nodes"][n["label"]] = rec

    for c in project["connections"]:
        fl = labels.get((c["from"]["n"], c["from"]["i"]))
        tl = labels.get((c["to"]["n"], c["to"]["i"]))
        if fl and tl:
            facts["connections"].append("%s -> %s" % (fl, tl))

    by_pkg = {}
    for n in project["nodes"]:
        if n["backing"] == "hand" and n["pkg"]:
            by_pkg.setdefault(n["pkg"], []).append(n)
    for pkg, recs in by_pkg.items():
        entry = project.get("packages", {}).get(pkg) or {}
        pentry = facts["packages"].setdefault(
            pkg, {"fromGitRepo": _fact_str(entry.get("fromGitRepo")), "artifacts": {}})
        for n in recs:
            arec = {"node": _fact_str(n["node"]), "interfaces": {}, "qos": {},
                    "parameters": {}}
            for f in n["ifaces"]:
                key = _iface_fact_key(f["kind"], f["name"])
                # the placeholder emit_ros2 writes for a type-less interface: the file will
                # spell it, so the fact tree has to as well.
                arec["interfaces"][key] = _fact_str(f.get("type") or "TODO_pkg/msg/Type")
                q = _qos_fact(f.get("qos"))
                if q:
                    arec["qos"][key] = q
            for p in n.get("params") or []:
                arec["parameters"][p["name"]] = _param_fact(p.get("ptype"), p.get("value"))
            pentry["artifacts"][_fact_str(n.get("artifact"))] = arec

    for pkg, blocks in _companion_types(project).items():
        seg_of = ROS_BLOCK_TO_TYPE_SEG
        for block, name in blocks:
            key = "%s/%s/%s" % (pkg, seg_of[block], name)
            fields = ((project.get("types") or {}).get(key) or {}).get("fields") or {}
            facts["types"][key] = {
                body: ["%s %s" % (str(f.get("type") or "").strip(),
                                  str(f.get("name") or "").strip())
                       for f in (fields.get(body) or [])
                       if str(f.get("type") or "").strip()
                       and str(f.get("name") or "").strip()]
                for body in L.ROS_SPEC_BODIES[block]}
    return facts


_FACT_MISSING = object()


def _fact_summary(value):
    """A one-line stand-in for a whole subtree, so an added or removed node reports as ONE
    line instead of one per leaf underneath it."""
    if isinstance(value, dict):
        parts = []
        for k in sorted(value):
            v = value[k]
            if isinstance(v, (dict, list)):
                if v:                      # an empty sub-block is not news; omit it
                    parts.append("%s: %d" % (k, len(v)))
            elif v != "":
                parts.append("%s=%s" % (k, v))
        return "; ".join(parts) or "(empty)"
    if isinstance(value, list):
        return "%d item(s)" % len(value)
    return str(value)


def _diff_walk(path, before, after, out):
    if before is _FACT_MISSING and after is _FACT_MISSING:
        return
    if before is _FACT_MISSING:
        out.append({"op": "added", "path": path, "before": "", "after": _fact_summary(after)})
        return
    if after is _FACT_MISSING:
        out.append({"op": "removed", "path": path, "before": _fact_summary(before),
                    "after": ""})
        return
    if isinstance(before, dict) and isinstance(after, dict):
        for k in sorted(set(before) | set(after)):
            _diff_walk("%s.%s" % (path, k) if path else str(k),
                       before.get(k, _FACT_MISSING), after.get(k, _FACT_MISSING), out)
        return
    if isinstance(before, list) and isinstance(after, list):
        # A list is diffed as a MULTISET plus an order check. `connections` has no key of its
        # own -- the label pair IS its identity -- and a message body's field list is ordered
        # but its entries are not unique, so neither can be walked by index without reporting
        # one insertion as a rewrite of every line after it.
        b, a = list(before), list(after)
        rest = list(a)
        for item in b:
            if item in rest:
                rest.remove(item)
            else:
                out.append({"op": "removed", "path": path, "before": item, "after": ""})
        left = list(b)
        for item in a:
            if item in left:
                left.remove(item)
            else:
                out.append({"op": "added", "path": path, "before": "", "after": item})
        if b != a and sorted(b) == sorted(a):
            out.append({"op": "reordered", "path": path,
                        "before": "%d item(s)" % len(b), "after": "same, different order"})
        return
    if before != after:
        out.append({"op": "changed", "path": path, "before": _fact_summary(before),
                    "after": _fact_summary(after)})


def diff_facts(before, after):
    """Ordered change records between two fact trees. Sections keep the tree's own order
    (system, subSystems, nodes, connections, packages, types) so the report reads top-down
    the way the file does."""
    out = []
    for sec in _FACT_SECTIONS:
        _diff_walk(sec, before.get(sec, _FACT_MISSING), after.get(sec, _FACT_MISSING), out)
    return out


_DIFF_OP_MARK = {"added": "+", "removed": "-", "changed": "~", "reordered": "%"}


def _diff_show(s):
    """An absent value is spelled, not left blank: "namespace  -> /robot1" reads as if the
    arrow were part of the value."""
    return "(none)" if s == "" else s


def format_diff(records):
    """Render change records as text. Mirrored BYTE-FOR-BYTE by the editor's diffText() so the
    "changed since the seed" tab and the companion's report cannot tell two stories."""
    if not records:
        return "no model-level change since the seed."
    width = 0
    for r in records:
        width = max(width, len(r["path"]))
    width = min(width, 46)
    lines, section = [], None
    for r in records:
        sec = r["path"].split(".")[0]
        if sec != section:
            section = sec
            lines.append("  " + sec)
        detail = r["after"] if r["op"] == "added" else (
            r["before"] if r["op"] == "removed"
            else "%s -> %s" % (_diff_show(r["before"]), _diff_show(r["after"])))
        lines.append("    %s %s  %s" % (_DIFF_OP_MARK[r["op"]], r["path"].ljust(width),
                                        detail))
    counts = {}
    for r in records:
        counts[r["op"]] = counts.get(r["op"], 0) + 1
    tail = ", ".join("%d %s" % (counts[k], k) for k in sorted(counts))
    lines.append("")
    lines.append("  %d change(s): %s" % (len(records), tail))
    return "\n".join(lines)


def seed_sources(project):
    """The .rossystem file(s) this project was seeded from, absolute, existing ones only."""
    paths = project.get("seededFromAll") or (
        [project["seededFrom"]] if project.get("seededFrom") else [])
    return [p for p in paths if os.path.isfile(p)]


def merged_source_facts(paths):
    """One fact tree over several seed sources.

    A merge is not a concatenation, because seed_from_many UNIQUIFIES a node label two sources
    both declare (RM009). The rename is replayed here with the SAME rule and the same hint --
    _unique_label(label, used, systemName), pass A of seed_from_many -- so a collision reads as
    the rename it is instead of as a deletion plus an unrelated addition.

    What is NOT replayed is pass B, the subSystems: shadow collapse: when one source is reached
    through another's subSystems:, the merge keeps the real node and drops the reference. That
    surfaces below as a subSystems removal, which is what the emitted file really says.
    """
    facts = _facts_tree()
    used = set()
    for i, p in enumerate(paths):
        one = source_facts(p)
        if i == 0:
            facts["system"] = one["system"]
        facts["subSystems"] += one["subSystems"]
        facts["connections"] += one["connections"]
        hint = one["system"].get("name") or os.path.basename(p)
        for label, rec in one["nodes"].items():
            merged_label = _unique_label(label, used, hint)
            used.add(merged_label)
            facts["nodes"].setdefault(merged_label, rec)
        for pkg, entry in one["packages"].items():
            tgt = facts["packages"].setdefault(pkg, {"fromGitRepo": entry["fromGitRepo"],
                                                     "artifacts": {}})
            for art, arec in entry["artifacts"].items():
                tgt["artifacts"].setdefault(art, arec)
        for key, spec in one["types"].items():
            facts["types"].setdefault(key, spec)
    return facts


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

    # {type: relative .ros file} -- the same lookup _type_catalogue_file() does, embedded so
    # the page can reproduce _type_comment()/_companion_types() byte-for-byte in its .ros2
    # preview. Without it the preview would have to guess whether a type discloses a source
    # file, and tests/studio_parity.js could not hold the two emitters to the same bytes.
    type_files = {}
    if os.path.isfile(tpath):
        try:
            with open(tpath, encoding="utf-8") as h:
                td = json.load(h)
            for name, entry in (td.get("types") or {}).items():
                rel = (entry or {}).get("file")
                if rel:
                    type_files[name] = rel
        except Exception:
            pass          # already reported above; the preview degrades to "no comment"

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

    return {"types": types, "typeFiles": type_files, "packages": sorted(packages),
            "catalogue": catalogue, "catalogueTypes": cat_types, "warnings": warnings}


# ========================================================================================
# Editor HTML
# ========================================================================================

def render_editor(project, diagnostics=None, banner=None):
    ac = load_autocomplete()
    if diagnostics:
        project = dict(project)
        project["diagnostics"] = diagnostics
    # The seed's fact tree travels WITH the page so the Commit modal can answer "what have I
    # changed" offline: the editor rebuilds the after-side from the live project (projectFacts,
    # the mirror of project_facts) and diffs against this. Absent when the project was created
    # blank or the source has since moved -- the tab then says which, rather than showing an
    # empty diff that would read as "nothing changed".
    seeds = seed_sources(project)
    recorded = project.get("seededFromAll") or (
        [project["seededFrom"]] if project.get("seededFrom") else [])
    seed_facts = merged_source_facts(seeds) if seeds else None
    seed_note = None
    if not recorded:
        seed_note = "this project was not seeded from a .rossystem, so there is no source to " \
                    "compare against."
    elif not seeds:
        seed_note = "the seed source is no longer where the project recorded it (%s)." \
                    % ", ".join(recorded)
    payload = {
        "project": project,
        "seedFacts": seed_facts,
        "seedNote": seed_note,
        "seedFrom": [os.path.basename(p) for p in (seeds or recorded)],
        "seedMerged": len(seeds) > 1,
        "types": ac["types"],
        "typeFiles": ac.get("typeFiles", {}),
        "packages": ac["packages"],
        "catalogue": ac["catalogue"],
        "catalogueTypes": ac.get("catalogueTypes", {}),
        "kindOrder": ARROW_KINDS,
        "kindLabels": {k: C.KIND_LABELS[k] for k in ARROW_KINDS},
        "blocks": {k: C.KIND_TO_BLOCK[k] for k in ARROW_KINDS},
        # The QoS vocabulary the editor offers comes from the LINTER's tables, not from a
        # hand-copy in the page: the control can then never offer a field or a value that
        # rosmodel_lint would reject, and its inline severities mirror the rules directly
        # (RM031 info / RM034 warning / RM035 error).
        "qos": {
            "fields": L.QOS_PINNED,
            "enums": QOS_UI_ENUMS,
            "newer": L.QOS_NEWER,
            "discouraged": L.QOS_DISCOURAGED,
            "durations": list(QOS_DURATIONS),
            "int32Min": L.INT32_MIN,
            "int32Max": L.INT32_MAX,
        },
        "typeSegBlocks": C.TYPE_SEG_TO_ROS_BLOCK,
        # The .ros vocabulary, again taken from the LINTER's tables rather than hand-copied
        # into the page: the field editor can then never offer a type rosmodel_lint would
        # reject, and its inline severities mirror RM074/RM075/RM077 directly. `arrays` is
        # NOT derived from `scalars` -- time, duration and Header have no array rule, so
        # 'time[]' is a parse error (Basics.xtext:212 lists exactly fourteen).
        "ros": {
            "blocks": L.ROS_SPEC_BLOCKS,
            "bodies": L.ROS_SPEC_BODIES,
            "scalars": L.ROS_SCALAR_TYPES,
            "arrays": L.ROS_ARRAY_TYPES,
            "nameKeywords": sorted(L.ROS_FIELD_NAME_KEYWORDS),
        },
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
    seed_failed = None
    if args.files:
        sources, roots, missing = _iter_seed_sources(args.files)
        if missing:
            for m in missing:
                print("ros_studio: init source not found: %s" % m, file=sys.stderr)
            return 1
        if not sources:
            print("ros_studio: no .rossystem found under: %s" % ", ".join(args.files),
                  file=sys.stderr)
            return 1
        if len(sources) == 1:
            # ONE source keeps the original path exactly, workspace index and all: a directory
            # argument is what asks for the tree-wide index, a plain file is not.
            single_file = os.path.isfile(os.path.abspath(args.files[0]))
            project = seed_from_rossystem(
                sources[0], None if single_file and len(args.files) == 1
                else _index_workspace(roots))
            if args.name:
                project["system"]["name"] = args.name
        else:
            project = seed_from_many(sources, roots, args.name)
        if not project.get("nodes"):
            # a real path was given but nothing was recovered -- surface it, don't pretend
            seed_failed = os.path.basename(sources[0])
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
              "empty. Wrote a project with no nodes." % seed_failed, file=sys.stderr)
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


def _stage_local_subsystems(project, outdir):
    """Copy a project-local `subSystems:` target into the output directory, unchanged.

    The generated directory is meant to be a model set the checker and the language server can
    consume on their own. A catalogued reference resolves through assets/, but a project-local
    one resolves only by sitting NEXT TO the referencing file -- so without this every endpoint
    it provides raises RM050 there and `generate` refuses its own correct output. collect_deps
    already stages the same file for the --oracle run (its docstring, "subSystems: entries are
    staged and re-linted the same way"); this puts it in place one step earlier, for the lint.

    Its OWN project-local .ros2 files come with it: the real language server resolved neither
    the node nor its interfaces without them (oracle run on tests/fixtures/subsystems, REJECTED
    with "Couldn't resolve reference to Node 'sub_probe_base.base_driver'" until they were
    staged), and an unresolved node then reports as a same-type connection error two lines
    further down, which is a thoroughly misleading way to learn a file is missing.

    Copied, never rewritten: it is a different model with its own author. A name the studio
    itself generated always wins, so staging can never overwrite this project's own output.
    Returns what it wrote."""
    seeded = project.get("seededFromAll") or (
        [project["seededFrom"]] if project.get("seededFrom") else [])
    if not seeded:
        return []
    # a merged project was seeded from several directories, and a reference kept by one source
    # can only resolve next to THAT source.
    bases, out = [], []
    for s in seeded:
        d = os.path.dirname(os.path.abspath(s))
        if d not in bases:
            bases.append(d)

    def stage(src):
        dst = os.path.join(outdir, os.path.basename(src))
        if (not os.path.isfile(src) or os.path.exists(dst)
                or os.path.abspath(src) == os.path.abspath(dst)):
            return None
        shutil.copyfile(src, dst)
        out.append(dst)
        return dst

    for s in project.get("subSystems") or []:
        if s.get("file"):
            continue                      # catalogued: assets/ resolves it, nothing to stage
        done = False
        for base in bases:
            if done:
                break
            for cand in (s.get("ref") or "", os.path.basename(s.get("ref") or "")):
                src = os.path.join(base, os.path.splitext(cand)[0] + ".rossystem")
                if not stage(src):
                    continue
                for mn in ros_plot.extract_model(src, use_catalogue=False)["nodes"]:
                    if mn.get("package"):
                        stage(os.path.join(base, mn["package"] + ".ros2"))
                done = True
                break
    return out


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

    staged = _stage_local_subsystems(project, outdir)
    for p in staged:
        print("staged %s (subSystems: dependency, copied unchanged)" % p)

    # lint covers what THIS project wrote; a staged file is someone else's model and its
    # findings are not this run's to report.
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

    if getattr(args, "diff", False):
        print("\n--- changed since the seed ---")
        text, _records, notes = _diff_report(project)
        print(text if text is not None else "  (nothing to diff against)")
        for n in notes:
            print("\n  note: %s" % n)

    if args.oracle:
        print("\n--- oracle (real language server) ---")
        # a staged subSystems: target is walked too -- it can carry catalogue references of its
        # own that collect_deps still has to vendor in before the server sees the directory.
        ok, text = run_oracle(outdir, written + staged)
        print(text)
        if not ok:
            print("oracle did NOT return a clean ACCEPTED.", file=sys.stderr)
            return 1
    return 0


def _generated_facts(project):
    """The fact tree of what generation ACTUALLY writes: emit into a temp directory and read
    it back with source_facts(). Deliberately not project_facts() -- that one predicts, this
    one observes, and `diff` compares the two so an emitter that starts dropping something the
    project holds is reported instead of cancelling out on both sides of the diff."""
    work = tempfile.mkdtemp(prefix="ros-studio-diff-")
    try:
        files = generate_files(project)
        for rel, content in files.items():
            with open(os.path.join(work, rel), "w", encoding="utf-8",
                      newline="\n") as handle:
                handle.write(content)
        sysfile = project["system"].get("name", "system") + ".rossystem"
        return source_facts(os.path.join(work, sysfile))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _diff_report(project, against=None):
    """(text, records, notes). `against` overrides the recorded seed source(s)."""
    notes = []
    if against:
        sources = [os.path.abspath(against)]
        if not os.path.isfile(sources[0]):
            return None, None, ["no such file: %s" % sources[0]]
    else:
        sources = seed_sources(project)
        recorded = project.get("seededFromAll") or (
            [project["seededFrom"]] if project.get("seededFrom") else [])
        for p in recorded:
            if not os.path.isfile(p):
                notes.append("seed source has moved or been deleted: %s" % p)
        if not sources:
            return None, None, (notes or ["this project records no seededFrom -- it was "
                                          "created blank, so there is nothing to diff "
                                          "against. Use --against FILE.rossystem."])
    before = merged_source_facts(sources)
    if len(sources) > 1:
        notes.append("merged seed (%d sources): the label uniquifier is replayed on the seed "
                     "side, but a subSystems: reference the merge collapsed reads below as a "
                     "removal." % len(sources))
    after = _generated_facts(project)
    predicted = diff_facts(project_facts(project), after)
    if predicted:
        notes.append("project_facts() and the generated files disagree in %d place(s) — the "
                     "editor's preview of this diff will differ from the report below. This "
                     "is an emitter/predictor bug, not an edit: %s"
                     % (len(predicted), "; ".join(r["path"] for r in predicted[:6])))
    records = diff_facts(before, after)
    return format_diff(records), records, notes


def cmd_diff(args):
    project = _load_project(args.project)
    text, records, notes = _diff_report(project, args.against)
    if text is None:
        for n in notes:
            print("ros_studio: %s" % n, file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"records": records, "notes": notes}, indent=2, ensure_ascii=False))
        return 0
    src = ", ".join(os.path.basename(p) for p in
                    ([os.path.abspath(args.against)] if args.against
                     else seed_sources(project)))
    print("diff -- %s since %s\n" % (os.path.basename(args.project), src))
    print(text)
    for n in notes:
        print("\n  note: %s" % n)
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
    p_init.add_argument("files", nargs="*",
                        help=".rossystem file(s) and/or directories to seed from; several are "
                             "merged into one project")
    p_init.add_argument("--out", default=None)
    p_init.add_argument("--name", default=None,
                        help="system name for the seeded project (a merge otherwise adopts "
                             "the first source's)")
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
    p_gen.add_argument("--diff", action="store_true",
                       help="also print the model-level diff against the seed source")
    p_gen.set_defaults(func=cmd_generate)

    p_diff = sub.add_parser("diff", help="model-level diff of the generated model against "
                                         "the .rossystem the project was seeded from")
    p_diff.add_argument("project")
    p_diff.add_argument("--against", default=None,
                        help="diff against this .rossystem instead of the recorded seed")
    p_diff.add_argument("--json", action="store_true",
                        help="emit the change records as JSON")
    p_diff.set_defaults(func=cmd_diff)

    # convenience: `ros_studio.py --json project.json` dumps generated files without writing
    parser.add_argument("--json", metavar="PROJECT", default=None,
                        help="print generated files as JSON for PROJECT and exit")
    # Parity hooks. tests/studio_parity.js holds the editor's projectFacts() to --facts and its
    # "changed since the seed" tab to --preview-diff; `diff` itself reports whether --facts and
    # the files `generate` actually writes agree.
    parser.add_argument("--facts", metavar="PROJECT", default=None,
                        help="print the project's fact tree as JSON and exit")
    parser.add_argument("--preview-diff", metavar="PROJECT", dest="preview_diff", default=None,
                        help="print the diff the EDITOR previews (predicted, not generated) "
                             "and exit")

    args = parser.parse_args(argv)
    if getattr(args, "facts", None) and not getattr(args, "cmd", None):
        print(json.dumps(project_facts(_load_project(args.facts)), indent=2,
                         ensure_ascii=False, sort_keys=True))
        return 0
    if getattr(args, "preview_diff", None) and not getattr(args, "cmd", None):
        project = _load_project(args.preview_diff)
        seeds = seed_sources(project)
        if not seeds:
            print("no seed source recorded.")
            return 0
        print(format_diff(diff_facts(merged_source_facts(seeds), project_facts(project))))
        return 0
    if args.json and not getattr(args, "cmd", None):
        project = _load_project(args.json)
        print(json.dumps(generate_files(project), indent=2, ensure_ascii=False))
        return 0
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
