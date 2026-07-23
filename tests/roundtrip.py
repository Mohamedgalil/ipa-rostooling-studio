#!/usr/bin/env python3
"""
roundtrip.py -- semantic round-trip test harness for RosTooling .ros2 / .rossystem models.

Work item E1, CoreSense x Humanoid (Fraunhofer IPA).

WHY THIS EXISTS
---------------
Byte-diffing a regenerated model against its corpus original is meaningless here and is
explicitly forbidden by the project brief:

  * 26 of 52 corpus .rossystem files contain tabs; indent widths of 3, 5, 6, 7 and 11 all
    occur; the working tree is 100% CRLF while every stored blob is pure LF
    (a core.autocrlf=true artefact -- see emission-profile.md 1.2).
  * Our emitter deliberately produces a CLEAN NORMALISED subset. It is *supposed* to differ
    byte-wise from the messy originals.

So a byte comparison fails on nearly every file and proves nothing. This harness compares
MEANING instead: both sides are read with the SAME reader, reduced to a canonical
name-keyed structure, and deep-compared.

WHAT "SAME READER" MEANS
------------------------
rossdl -- the only executable consumer of these DSLs available to us -- parses them with
yaml.safe_load (rossdl/rossdl_cmake/rossdl_cmake/__init__.py:28,388,417,455,472).
This harness uses the same YAML front end, plus a pre-normalisation pass and a DSL-faithful
scalar typer that together close the gaps between YAML and the real Xtext grammar.

READER FIDELITY -- MEASURED, NOT ASSUMED
----------------------------------------
YAML is an APPROXIMATION of the indentation-sensitive Xtext grammar, not the grammar itself.
Measured on the full corpus (253 .ros2 + 52 .rossystem):

    raw yaml.safe_load           .ros2 228/253   .rossystem 26/52
    + pre-normalisation          .ros2 238/253   .rossystem 39/52

The files that remain unreadable are genuinely malformed (mis-indented blocks, C-style
/* */ comments that the DSL's SL_COMMENT terminal does not accept either). They are NOT
silently tolerated -- read_model() reports them as errors and the process exits non-zero.

The pre-normalisation pass performs only transformations that are semantics-preserving
UNDER THE XTEXT GRAMMAR, where whitespace is hidden and BEGIN/END are synthesised from
indentation:

    1. strip UTF-8 BOM
    2. CRLF/CR -> LF                          (checkout artefact, emission-profile 1.2 / rule 3)
    3. tabs in leading indent -> spaces       (26/52 .rossystem files; YAML forbids tab indent)
    4. "type:Array [String]" -> "type: Array [String]"
                                              (10 .ros2 files; 'type:' is a keyword TOKEN in the
                                               grammar so no space is required, but YAML needs one)
    5. "-[a, b]" -> "- [a, b]"                (3 .rossystem files; same class of issue)
    6. strip trailing whitespace              (trailing tabs break the YAML scanner)

Each rule is justified in fixtures/manifest.md against the file that motivated it.

KNOWN, DELIBERATE LIMITATIONS
-----------------------------
  * No .rossystem language server exists at all (validator-rules.md 0.2), and the shipped
    .ros2 LS jar requires Java 19 while this machine has 1.8.0_481 (grammar-subset.md 7).
    NOTHING here has been executed against the real oracle. This harness checks
    self-consistency of emitter output, not conformance to the true parser.
  * Duplicate mapping keys are LOSSY in YAML. MT.rossystem declares 32 node keys but
    yaml.safe_load returns 30 -- 'robot_state_publisher' and 'bt_navigator' each appear
    twice and the earlier definition is silently discarded. A naive dict-based harness
    would therefore compare a model that is missing two nodes and never notice.
    read_model() installs a duplicate-detecting loader and reports every duplicate.
  * Quoting style is invisible to the grammar for EString positions (emission-profile
    rule 15) and is correctly not compared -- EXCEPT that quotedness is retained for
    parameter VALUES, where it is semantically load-bearing (see dsl_typed_value).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "roundtrip.py requires PyYAML.\n"
        "    python -m pip install pyyaml\n"
        "PyYAML is the same front end rossdl uses (rossdl_cmake/__init__.py:23).\n"
    )
    raise SystemExit(3)


# ======================================================================================
# 1. PRE-NORMALISATION
# ======================================================================================

# Block and field keys of the pinned grammar subset. Sources:
#   Ros2.xtext (AmentPackage, Artifact, interfaces, QoS), Ros.xtext (Node),
#   RosSystem.xtext (System, RosNode, Process), Basics.xtext (Parameter).
# 'msgs'/'srvs'/'actions' are included for READING .ros files only; grammar-subset.md 5.2
# forbids EMITTING them in .ros2.
DSL_KEYS = (
    "fromGitRepo", "fromFile", "artifacts", "dependencies", "subSystems", "processes",
    "threads", "nodes", "connections", "interfaces", "parameters", "publishers",
    "subscribers", "serviceservers", "serviceclients", "actionservers", "actionclients",
    "node", "namespace", "from", "type", "ns", "value", "qos", "profile", "history",
    "depth", "reliability", "durability", "msgs", "srvs", "actions",
)

_KEY_NO_SPACE = re.compile(r"^(\s*(?:-\s*)?)(%s):(?=\S)" % "|".join(DSL_KEYS))
_DASH_BRACKET = re.compile(r"^(\s*)-\[")
_LEADING_WS = re.compile(r"[ \t]*")


def prenormalise(text: str, tab_width: int = 2) -> str:
    """Make messy corpus text readable by a YAML scanner without changing its meaning
    under the Xtext grammar. See module docstring for the justification of each rule."""
    if text.startswith("﻿"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    out = []
    for line in text.split("\n"):
        indent = _LEADING_WS.match(line).group(0)
        line = indent.replace("\t", " " * tab_width) + line[len(indent):]
        line = _KEY_NO_SPACE.sub(r"\1\2: ", line)
        line = _DASH_BRACKET.sub(r"\1- [", line)
        out.append(line.rstrip())

    text = "\n".join(out)
    if text and not text.endswith("\n"):
        text += "\n"
    return text


# ======================================================================================
# 2. READER -- YAML with scalar-style retention and duplicate-key detection
# ======================================================================================

class Scalar(str):
    """A string that remembers whether it was quoted in the source.

    Needed because quotedness is semantically load-bearing for parameter values:
    `value: true` is a ParameterBoolean, `value: "true"` is a ParameterString
    (Basics.xtext:139,173 -- the BOOLEAN terminal cannot match a STRING token).
    """
    __slots__ = ("style",)

    def __new__(cls, value, style):
        obj = str.__new__(cls, value)
        obj.style = style          # None = plain/unquoted; '"' or "'" = quoted
        return obj

    @property
    def quoted(self) -> bool:
        return self.style in ('"', "'")

    # str subclasses with extra state need this or copy/deepcopy drops `style`,
    # which would silently turn a quoted "true" back into a boolean.
    def __reduce__(self):
        return (Scalar, (str(self), self.style))


class DslLoader(yaml.SafeLoader):
    """SafeLoader with YAML's type guessing switched OFF and duplicate keys recorded.

    Implicit resolvers are cleared so every plain scalar arrives as a raw lexeme. YAML 1.1
    would otherwise resolve `True` to a boolean -- but in this DSL `True` is NOT a boolean:
    it fails the BOOLEAN terminal and falls through the ParameterValue alternation to
    ParameterString (emission-profile 1.4 / 7). Typing is done afterwards by
    dsl_typed_value(), which follows the grammar's terminal precedence instead of YAML's.
    """

    def __init__(self, stream):
        super().__init__(stream)
        self.duplicate_keys = []

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                self.duplicate_keys.append((str(key), key_node.start_mark.line + 1))
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


DslLoader.yaml_implicit_resolvers = {
    ch: [] for ch in DslLoader.yaml_implicit_resolvers
}
DslLoader.add_constructor(
    "tag:yaml.org,2002:str",
    lambda loader, node: Scalar(node.value, node.style),
)


class ReadError(Exception):
    pass


def read_model(path: str, tab_width: int = 2):
    """Read one model file. Returns (data, meta). Raises ReadError if unparseable."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise ReadError("cannot open %s: %s" % (path, exc))

    text = prenormalise(raw.decode("utf-8", "replace"), tab_width=tab_width)
    loader = DslLoader(text)
    try:
        data = loader.get_single_data()
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = " at line %d" % (mark.line + 1) if mark else ""
        raise ReadError("%s: unreadable%s: %s"
                        % (path, where, getattr(exc, "problem", str(exc))))
    finally:
        dups = list(loader.duplicate_keys)
        loader.dispose()

    if data is None:
        raise ReadError("%s: empty model" % path)
    if not isinstance(data, dict):
        raise ReadError("%s: top level is %s, expected a mapping"
                        % (path, type(data).__name__))

    meta = {
        "path": path,
        "duplicate_keys": dups,
        "crlf_in_source": b"\r\n" in raw,
        "final_newline": raw.endswith(b"\n"),
        "tabs_in_source": b"\t" in raw,
    }
    return data, meta


# ======================================================================================
# 3. DSL-FAITHFUL SCALAR TYPING
# ======================================================================================

# Basics.xtext:173  terminal BOOLEAN: 'true'|'false';         -- lowercase only
# Basics.xtext      terminal DECINT / DOUBLE
_DECINT_RE = re.compile(r"[+-]?[0-9]+\Z")
# DOUBLE requires a '.' or an exponent; a bare 10 is a DECINT and silently becomes a
# ParameterInteger even under `type: Double` (emission-profile rule 19).
_DOUBLE_RE = re.compile(r"[+-]?(?:[0-9]*\.[0-9]*(?:[eE][+-]?[0-9]+)?|[0-9]*[eE][+-]?[0-9]+)\Z")


def dsl_typed_value(value):
    """Type a scalar the way the grammar's terminal precedence does, not the way YAML does.

    Returns a (type_name, python_value) pair so that a change of TYPE is reported as a
    difference even when the printed text looks similar. This is what catches the two
    silent-corruption traps documented in emission-profile 1.4:
        `type: Boolean` + `value: True`  -> ('string', 'True')   not a boolean
        `type: Double`  + `value: 10`    -> ('integer', 10)      not a double
    """
    if value is None:
        return ("null", None)
    if isinstance(value, (list, tuple)):
        return ("sequence", tuple(dsl_typed_value(v) for v in value))
    if isinstance(value, dict):
        return ("mapping", tuple(sorted((str(k), dsl_typed_value(v))
                                        for k, v in value.items())))

    text = str(value)
    if isinstance(value, Scalar) and value.quoted:
        return ("string", text)          # quoted -> STRING token, never BOOLEAN/DECINT
    if text in ("true", "false"):
        return ("boolean", text == "true")
    if _DECINT_RE.match(text):
        return ("integer", int(text))
    if _DOUBLE_RE.match(text) and any(c in text for c in ".eE"):
        return ("double", float(text))
    return ("string", text)


def unquote(text) -> str:
    """Strip quotes that survived inside a plain YAML scalar.

    `- "tf": pub-> "node::tf"` yields the plain scalar `pub-> "node::tf"`, in which the
    quotes are literal characters rather than YAML syntax.
    """
    s = str(text).strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


# ======================================================================================
# 4. CANONICALISATION
# ======================================================================================
#
# The canonical form is a FLAT dict mapping a semantic path to a value:
#
#     node[gazebo].interface[clock].kind        -> 'pub'
#     artifact[amcl].publisher[amcl_pose].type  -> 'geometry_msgs/msg/...'
#
# Flattening makes missing / extra / changed reporting exact, and makes the comparison
# ordering-insensitive by construction for everything that the grammar keys by NAME.
#
# ORDER SENSITIVITY -- per the spec files:
#   * Named collections (nodes, artifacts, interfaces, parameters, publishers, ...) are
#     resolved BY NAME by the grammar and the validators. RosSystemConnection resolves
#     [RosInterface|EString] by name (emission-profile rule 28). Order is therefore NOT
#     semantic and is NOT compared.
#   * `connections:` is a set of (from, to) pairs; order carries no meaning.
#   * `dependencies:` / `subSystems:` are sets.
#   * The four grammar-FIXED member sequences (emission-profile rules 21-23) are a
#     different matter: emitting them out of order is a PARSE ERROR, not a different
#     model. They are checked separately by check_member_order(), which reads textual
#     order from the loaded mapping (dicts preserve insertion order in Python 3.7+).

INTERFACE_KINDS = {
    "publishers": "pub", "subscribers": "sub",
    "serviceservers": "ss", "serviceclients": "sc",
    "actionservers": "as", "actionclients": "ac",
}
ARROW_RE = re.compile(r"\A(pub|sub|ss|sc|as|ac)\s*->\s*(.*)\Z", re.S)
QOS_FIELDS = ("profile", "history", "depth", "reliability", "durability")

# Grammar-fixed member orders. Violating one is a parse error, not a model difference.
FIXED_ORDER = {
    "ament_package": ["fromGitRepo", "artifacts", "dependencies"],      # Ros2.xtext:13-24
    "rossystem_node": ["from", "namespace", "interfaces", "parameters"],  # RosSystem.xtext:60-75
    "interface": ["type", "ns", "qos"],                                  # Ros2.xtext:49-112
    "ros2_parameter": ["type", "ns", "value", "qos"],                    # Ros2.xtext:114-124
}


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    text = str(value).strip()
    return [text] if text else []


def _mapping(value):
    return value if isinstance(value, dict) else {}


class Canon:
    """A canonical model: flat semantic paths plus the notes gathered while building it."""

    def __init__(self, kind, name, path):
        self.kind = kind
        self.name = name
        self.path = path
        self.facts = {}
        self.notes = []

    def put(self, key, value):
        # Never overwrite. The corpus contains genuine duplicate names (MT.rossystem
        # duplicate node keys; pickQrCode duplicate interface local names), and silently
        # keeping the last one is exactly the data loss this harness exists to expose.
        # Colliding paths are suffixed #2, #3, ... so the canonical form stays lossless
        # and the duplicate shows up as a real difference rather than vanishing.
        if key in self.facts:
            index = 2
            while "%s#%d" % (key, index) in self.facts:
                index += 1
            self.notes.append("duplicate canonical path %s -- kept as %s#%d"
                              % (key, key, index))
            key = "%s#%d" % (key, index)
        self.facts[key] = value

    def note(self, message):
        self.notes.append(message)


def canonicalise(data, path, meta=None):
    """Reduce raw loaded data to a canonical model. Dispatches on file extension."""
    if len(data) != 1:
        # The grammar has exactly one root element per file.
        raise ReadError("%s: expected exactly 1 root element, found %d (%s)"
                        % (path, len(data), ", ".join(map(str, list(data)[:5]))))

    root_name, body = next(iter(data.items()))
    body = _mapping(body)
    is_ros2 = path.lower().endswith(".ros2")
    canon = Canon("ros2" if is_ros2 else "rossystem", str(root_name), path)
    canon.put("model.name", str(root_name))

    for name, line in (meta or {}).get("duplicate_keys", []):
        canon.note("DUPLICATE KEY %r at line %d -- earlier definition discarded by the "
                   "YAML reader; the DSL would have kept both" % (name, line))

    (_canon_ros2 if is_ros2 else _canon_rossystem)(canon, body)
    return canon


# ---------------------------------------------------------------- .ros2 (AmentPackage)

def _canon_ros2(canon, body):
    if "fromGitRepo" in body:
        canon.put("package.fromGitRepo", unquote(body["fromGitRepo"]))
    for dep in _as_list(body.get("dependencies")):
        canon.put("dependency[%s]" % unquote(dep), True)

    for art_name, art_body in _mapping(body.get("artifacts")).items():
        art = unquote(art_name)
        art_body = _mapping(art_body)
        canon.put("artifact[%s]" % art, True)
        if "node" in art_body:
            canon.put("artifact[%s].node" % art, unquote(art_body["node"]))

        for block, kind in INTERFACE_KINDS.items():
            for iface_name, iface_body in _mapping(art_body.get(block)).items():
                iface = unquote(iface_name)
                if iface == "":
                    canon.note("EMPTY interface name in %s of artifact %s "
                               "(emission-profile rule 20)" % (block, art))
                base = "artifact[%s].%s[%s]" % (art, kind, iface)
                iface_body = _mapping(iface_body)
                canon.put(base, True)
                if "type" in iface_body:
                    canon.put(base + ".type", unquote(iface_body["type"]))
                if "ns" in iface_body:
                    canon.put(base + ".ns", unquote(iface_body["ns"]))
                _canon_qos(canon, base, iface_body.get("qos"))

        for par_name, par_body in _mapping(art_body.get("parameters")).items():
            par = unquote(par_name)
            if par == "":
                canon.note("EMPTY parameter name in artifact %s "
                           "(emission-profile rule 20)" % art)
            base = "artifact[%s].parameter[%s]" % (art, par)
            par_body = _mapping(par_body)
            canon.put(base, True)
            if "type" in par_body:
                # Parameter TYPE is a bare grammar keyword (Boolean/Integer/Array[T]/...),
                # never a quoted EString -- emission-profile rule 16.
                canon.put(base + ".type", str(par_body["type"]).strip())
            if "default" in par_body:
                # 'default:' is a member of ParameterType (Basics.xtext:72-110), NOT of Parameter,
                # and it is legal on every scalar type -- not only on Array[T]. It is a DIFFERENT
                # metamodel slot from 'value:'. Extracting it as its own fact is what makes a
                # default:->value: rewrite surface as a real difference; folding the two together
                # (or omitting default: entirely, as this harness did before 2026-07-21) scores a
                # silent semantic change as a clean PASS.
                canon.put(base + ".default", dsl_typed_value(par_body["default"]))
            if "ns" in par_body:
                canon.put(base + ".ns", unquote(par_body["ns"]))
            if "value" in par_body:
                canon.put(base + ".value", dsl_typed_value(par_body["value"]))
            _canon_qos(canon, base, par_body.get("qos"))


def _canon_qos(canon, base, qos):
    if qos is None or not isinstance(qos, dict):
        return
    for field in QOS_FIELDS:
        if field in qos:
            canon.put("%s.qos.%s" % (base, field), str(qos[field]).strip())
    for field in ("lease_duration", "liveliness", "lifespan", "deadline"):
        if field in qos:
            # grammar-subset.md 5.1 -- absent from the pinned oracle's token set.
            canon.note("QoS field %r is HEAD-only and absent from the pinned LS jar; "
                       "emitting it is a syntax error against the oracle" % field)
            canon.put("%s.qos.%s" % (base, field), str(qos[field]).strip())


# ------------------------------------------------------------------- .rossystem (System)

def _canon_rossystem(canon, body):
    if "fromFile" in body:
        canon.put("system.fromFile", unquote(body["fromFile"]))
    else:
        # validator-rules.md 2.2 -- fromFileHelper dereferences a null fromFile.
        canon.note("no fromFile: -- corpus-normal (32/52) but trips the unguarded null "
                   "dereference in RosSystemValidator.fromFileHelper")

    for sub in _as_list(body.get("subSystems")):
        canon.put("subSystem[%s]" % unquote(sub), True)

    for proc_name, proc_body in _mapping(body.get("processes")).items():
        proc = unquote(proc_name)
        proc_body = _mapping(proc_body)
        canon.put("process[%s]" % proc, True)
        if "threads" in proc_body:
            canon.put("process[%s].threads" % proc, dsl_typed_value(proc_body["threads"]))
        for node in _as_list(proc_body.get("nodes")):
            canon.put("process[%s].node[%s]" % (proc, unquote(node)), True)

    for node_name, node_body in _mapping(body.get("nodes")).items():
        node = unquote(node_name)
        node_body = _mapping(node_body)
        canon.put("node[%s]" % node, True)
        if "from" in node_body:
            canon.put("node[%s].from" % node, unquote(node_body["from"]))
        if "namespace" in node_body:
            canon.put("node[%s].namespace" % node, unquote(node_body["namespace"]))
        _canon_interfaces(canon, "node[%s]" % node, node_body.get("interfaces"))
        _canon_params(canon, "node[%s]" % node, node_body.get("parameters"))

    # The SYSTEM-level parameters: block is the ros.Parameter rule
    # (RosSystem.xtext:34-38 -> 'parameters:' BEGIN parameter+=Parameter* END), i.e. a
    # MAPPING of name -> {type, ns, value}. That is a different shape from the
    # node-level RosParameter list handled by _canon_params. ur5e_cell_moveit.rossystem
    # is the corpus witness.
    _canon_declared_params(canon, "system", body.get("parameters"))

    for entry in _as_list(body.get("connections")):
        if isinstance(entry, (list, tuple)) and len(entry) == 2:
            src, dst = unquote(entry[0]), unquote(entry[1])
            canon.put("connection[%s -> %s]" % (src, dst), True)
        else:
            canon.note("unrecognised connection entry %r -- expected a 2-element "
                       "[from , to] sequence (RosSystem.xtext:123-124)" % (entry,))


def _canon_interfaces(canon, base, interfaces):
    seen = set()
    for entry in _as_list(interfaces):
        if not isinstance(entry, dict):
            canon.note("unrecognised interface entry %r under %s" % (entry, base))
            continue
        for local_name, spec in entry.items():
            local = unquote(local_name)
            match = ARROW_RE.match(str(spec).strip())
            if not match:
                canon.note("interface %r under %s has no pub->/sub->/ss->/sc->/as->/ac-> "
                           "arrow: %r" % (local, base, str(spec)))
                continue
            kind, target = match.group(1), unquote(match.group(2))
            if local in seen:
                # emission-profile rule 28 -- duplicates break name-based cross-referencing.
                canon.note("DUPLICATE interface local name %r under %s" % (local, base))
            seen.add(local)
            key = "%s.interface[%s]" % (base, local)
            canon.put(key + ".kind", kind)
            canon.put(key + ".target", target)


def _canon_declared_params(canon, base, params):
    """Canonicalise a DECLARED parameter block: a mapping of name -> {type, ns, value}.

    Used for the .rossystem system-level `parameters:` block. The .ros2 artifact
    `parameters:` block has the same shape and is handled inline in _canon_ros2.
    """
    for name, spec in _mapping(params).items():
        key = "%s.parameter[%s]" % (base, unquote(name))
        spec = _mapping(spec)
        canon.put(key, True)
        if "type" in spec:
            # Bare grammar keyword, never a quoted EString -- emission-profile rule 16.
            canon.put(key + ".type", str(spec["type"]).strip())
        if "default" in spec:
            # Distinct slot from value: -- see the note in _canon_ros2.
            canon.put(key + ".default", dsl_typed_value(spec["default"]))
        if "ns" in spec:
            canon.put(key + ".ns", unquote(spec["ns"]))
        if "value" in spec:
            canon.put(key + ".value", dsl_typed_value(spec["value"]))


def _canon_params(canon, base, params):
    """Canonicalise an ASSIGNED parameter block: a list of `- name: ref` (+ `value:`).

    Used for the .rossystem node-level `parameters:` block (RosParameter).
    """
    if isinstance(params, dict):
        # Defensive: a node-level block written in the declared (mapping) shape.
        canon.note("parameter block under %s is a mapping, not a `- name: ref` list; "
                   "read as a declared-parameter block" % base)
        _canon_declared_params(canon, base, params)
        return
    for entry in _as_list(params):
        if not isinstance(entry, dict):
            canon.note("unrecognised parameter entry %r under %s" % (entry, base))
            continue
        names = [k for k in entry if k != "value"]
        if len(names) != 1:
            canon.note("parameter entry under %s has %d name keys (expected 1): %r"
                       % (base, len(names), list(entry)))
            if not names:
                continue
        name = unquote(names[0])
        key = "%s.parameter[%s]" % (base, name)
        canon.put(key + ".ref", unquote(entry[names[0]]))
        if "value" in entry:
            canon.put(key + ".value", dsl_typed_value(entry["value"]))


# ======================================================================================
# 5. GRAMMAR-FIXED MEMBER ORDER (a parse-error check, not a model difference)
# ======================================================================================

def check_member_order(data, path):
    """Verify the four member sequences the grammar fixes. Emitting them out of order is
    a syntax error. Python dicts preserve insertion order, so the loaded mapping still
    carries the textual order."""
    problems = []

    def verify(mapping, rule, where):
        expected = FIXED_ORDER[rule]
        present = [k for k in mapping if k in expected]
        ranked = sorted(present, key=expected.index)
        if present != ranked:
            problems.append("%s: %s order is %s, grammar requires %s"
                            % (where, rule, " -> ".join(present), " -> ".join(ranked)))

    if not isinstance(data, dict) or len(data) != 1:
        return problems
    root, body = next(iter(data.items()))
    body = _mapping(body)

    if path.lower().endswith(".ros2"):
        verify(body, "ament_package", str(root))
        for art_name, art_body in _mapping(body.get("artifacts")).items():
            for block in INTERFACE_KINDS:
                for iname, ibody in _mapping(_mapping(art_body).get(block)).items():
                    if isinstance(ibody, dict):
                        verify(ibody, "interface", "%s/%s/%s" % (art_name, block, iname))
            for pname, pbody in _mapping(_mapping(art_body).get("parameters")).items():
                if isinstance(pbody, dict):
                    verify(pbody, "ros2_parameter", "%s/parameters/%s" % (art_name, pname))
    else:
        for node_name, node_body in _mapping(body.get("nodes")).items():
            if isinstance(node_body, dict):
                verify(node_body, "rossystem_node", str(node_name))
    return problems


# ======================================================================================
# 6. COMPARISON
# ======================================================================================

_CATEGORY_PATTERNS = (
    (re.compile(r"\.qos\."), "qos"),
    (re.compile(r"\.type\Z"), "type"),
    (re.compile(r"\.value\Z"), "value"),
    (re.compile(r"\.default\Z"), "default"),
    (re.compile(r"\.kind\Z|\.target\Z"), "interface"),
    (re.compile(r"^connection\["), "connection"),
    (re.compile(r"\.parameter\["), "parameter"),
    (re.compile(r"\.interface\["), "interface"),
    (re.compile(r"^node\["), "node"),
    (re.compile(r"^artifact\[[^\]]+\]\.(pub|sub|ss|sc|as|ac)\["), "interface"),
    (re.compile(r"^artifact\["), "artifact"),
    (re.compile(r"^process\["), "process"),
    (re.compile(r"^subSystem\["), "subsystem"),
    (re.compile(r"^dependency\["), "dependency"),
)


def categorise(key: str) -> str:
    for pattern, label in _CATEGORY_PATTERNS:
        if pattern.search(key):
            return label
    return "model"


def _render(value):
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
        return "%s:%r" % (value[0], value[1])
    return repr(value)


def compare(left: Canon, right: Canon):
    """Deep-compare two canonical models. Returns a list of difference dicts."""
    diffs = []
    lk, rk = set(left.facts), set(right.facts)

    for key in sorted(lk - rk):
        diffs.append({"kind": "missing", "category": categorise(key), "path": key,
                      "left": _render(left.facts[key]), "right": None})
    for key in sorted(rk - lk):
        diffs.append({"kind": "extra", "category": categorise(key), "path": key,
                      "left": None, "right": _render(right.facts[key])})
    for key in sorted(lk & rk):
        if left.facts[key] != right.facts[key]:
            diffs.append({"kind": "changed", "category": categorise(key), "path": key,
                          "left": _render(left.facts[key]),
                          "right": _render(right.facts[key])})

    if left.kind != right.kind:
        diffs.insert(0, {"kind": "changed", "category": "model", "path": "model.kind",
                         "left": left.kind, "right": right.kind})
    return diffs


# ======================================================================================
# 7. REPORTING
# ======================================================================================

_ORDER = {"missing": 0, "extra": 1, "changed": 2}


def report(diffs, left, right, stream=sys.stdout, show_notes=True):
    stream.write("ORIGINAL   %s\n" % left.path)
    stream.write("REGENERATED %s\n" % right.path)
    stream.write("facts: %d original / %d regenerated\n"
                 % (len(left.facts), len(right.facts)))

    if show_notes:
        for side, canon in (("original", left), ("regenerated", right)):
            for note in canon.notes:
                stream.write("  NOTE [%s] %s\n" % (side, note))

    if not diffs:
        stream.write("\nRESULT: SEMANTICALLY EQUAL (%d facts compared)\n" % len(left.facts))
        return

    by_cat = {}
    for d in diffs:
        by_cat.setdefault(d["category"], []).append(d)

    stream.write("\nRESULT: %d SEMANTIC DIFFERENCE(S)\n\n" % len(diffs))
    stream.write("  %-12s %7s %7s %8s\n" % ("category", "missing", "extra", "changed"))
    stream.write("  %s\n" % ("-" * 38))
    for cat in sorted(by_cat):
        items = by_cat[cat]
        stream.write("  %-12s %7d %7d %8d\n" % (
            cat,
            sum(1 for d in items if d["kind"] == "missing"),
            sum(1 for d in items if d["kind"] == "extra"),
            sum(1 for d in items if d["kind"] == "changed"),
        ))
    stream.write("\n")

    for cat in sorted(by_cat):
        stream.write("  [%s]\n" % cat)
        for d in sorted(by_cat[cat], key=lambda x: (_ORDER[x["kind"]], x["path"])):
            if d["kind"] == "missing":
                stream.write("    - MISSING  %s = %s\n" % (d["path"], d["left"]))
            elif d["kind"] == "extra":
                stream.write("    + EXTRA    %s = %s\n" % (d["path"], d["right"]))
            else:
                stream.write("    ~ CHANGED  %s\n" % d["path"])
                stream.write("        original    %s\n" % d["left"])
                stream.write("        regenerated %s\n" % d["right"])
        stream.write("\n")


# ======================================================================================
# 8. SELF-TEST PERTURBATIONS
# ======================================================================================
#
# A file compared to itself passes even if compare() were `return []`. These perturbations
# make the identity test mean something:
#
#   perturb_text   -- semantically NEUTRAL reformatting. Must compare EQUAL. Proves the
#                     harness is insensitive to exactly the corpus noise (tabs, indent
#                     width, quote character, CRLF, final newline) that makes byte-diffing
#                     useless.
#   perturb_model  -- semantically NEUTRAL reordering of every mapping. Must compare EQUAL.
#                     Proves ordering-insensitivity where the grammar keys by name.
#   mutate_model   -- semantically REAL damage. Must compare DIFFERENT. Proves compare()
#                     is not vacuous.

def perturb_text(text: str, rng: random.Random) -> str:
    """Reformat without changing meaning: widen the indent ladder 2->4, convert the
    indent to tabs, flip single quotes to double, use CRLF, drop the final newline."""
    out = []
    for line in prenormalise(text).split("\n"):
        indent = _LEADING_WS.match(line).group(0)
        rest = line[len(indent):]
        if rest and "'" in rest and '"' not in rest:
            rest = re.sub(r"'([^'\"]*)'", r'"\1"', rest)
        units = len(indent) // 2
        odd = " " * (len(indent) % 2)
        out.append(("\t" * units) + odd + rest)
    return "\r\n".join(out).rstrip("\r\n")


def perturb_model(data, rng: random.Random):
    """Recursively reorder every mapping. Sequence order is preserved -- connections and
    interface lists are compared as sets by canonicalise(), so shuffling them would test
    nothing extra, while reordering mappings directly exercises name-keyed lookup."""
    if isinstance(data, dict):
        items = list(data.items())
        rng.shuffle(items)
        return {k: perturb_model(v, rng) for k, v in items}
    if isinstance(data, list):
        return [perturb_model(v, rng) for v in data]
    return data


def mutate_model(data, rng: random.Random):
    """Apply one real semantic change. Returns (mutated_copy, description) or (None, why)."""
    data = copy.deepcopy(data)
    root, body = next(iter(data.items()))
    if not isinstance(body, dict):
        return None, "root body is not a mapping"

    container = body.get("nodes") if "nodes" in body else body.get("artifacts")
    label = "node" if "nodes" in body else "artifact"
    if not isinstance(container, dict) or not container:
        return None, "no nodes:/artifacts: block to mutate"

    victim = sorted(container)[0]
    del container[victim]
    return data, "deleted %s %r" % (label, victim)


# ======================================================================================
# 9. CLI
# ======================================================================================

def _load(path, tab_width):
    data, meta = read_model(path, tab_width=tab_width)
    return data, meta, canonicalise(data, path, meta)


def cmd_compare(args):
    try:
        _, _, left = _load(args.original, args.tab_width)
        _, _, right = _load(args.regenerated, args.tab_width)
    except ReadError as exc:
        sys.stderr.write("READ ERROR: %s\n" % exc)
        return 2

    diffs = compare(left, right)
    if args.json:
        json.dump({"original": left.path, "regenerated": right.path,
                   "equal": not diffs, "differences": diffs,
                   "notes": {"original": left.notes, "regenerated": right.notes}},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        report(diffs, left, right)
    return 1 if diffs else 0


def cmd_selftest(args):
    """Identity, neutral-perturbation and negative-control checks over the given files."""
    rng = random.Random(20260721)
    failures = 0
    width = max((len(os.path.basename(p)) for p in args.files), default=20)

    print("%-*s  %-10s %-14s %-14s %-12s" % (
        width, "FIXTURE", "IDENTITY", "TEXT-PERTURB", "ORDER-PERTURB", "NEG-CONTROL"))
    print("-" * (width + 56))

    for path in args.files:
        name = os.path.basename(path)
        try:
            raw = open(path, "rb").read().decode("utf-8", "replace")
            data, meta, canon = _load(path, args.tab_width)
        except (ReadError, OSError) as exc:
            print("%-*s  READ ERROR: %s" % (width, name, exc))
            failures += 1
            continue

        results = {}

        # (a) identity: the file against itself.
        results["identity"] = "PASS" if not compare(canon, canon) else "FAIL"

        # (b) neutral text reformatting must compare equal.
        try:
            ptxt = perturb_text(raw, rng)
            ploader = DslLoader(prenormalise(ptxt, args.tab_width))
            pdata = ploader.get_single_data()
            pdups = list(ploader.duplicate_keys)
            ploader.dispose()
            pcanon = canonicalise(pdata, path, {"duplicate_keys": pdups})
            d = compare(canon, pcanon)
            results["text"] = "PASS" if not d else "FAIL(%d)" % len(d)
        except Exception as exc:
            results["text"] = "ERROR"
            if args.verbose:
                print("      text-perturb error: %s" % exc)

        # (c) neutral mapping reordering must compare equal.
        try:
            ocanon = canonicalise(perturb_model(data, rng), path, meta)
            d = compare(canon, ocanon)
            results["order"] = "PASS" if not d else "FAIL(%d)" % len(d)
        except Exception as exc:
            results["order"] = "ERROR"
            if args.verbose:
                print("      order-perturb error: %s" % exc)

        # (d) negative control: real damage MUST be detected.
        mutated, why = mutate_model(data, rng)
        if mutated is None:
            results["negative"] = "N/A"
        else:
            d = compare(canon, canonicalise(mutated, path, meta))
            results["negative"] = "PASS(%d)" % len(d) if d else "FAIL"

        if any(str(v).startswith(("FAIL", "ERROR")) for v in results.values()):
            failures += 1

        print("%-*s  %-10s %-14s %-14s %-12s" % (
            width, name, results["identity"], results["text"],
            results["order"], results["negative"]))

        if args.verbose:
            for note in canon.notes:
                print("      NOTE %s" % note)
            for problem in check_member_order(data, path):
                print("      ORDER %s" % problem)

    print()
    print("%d fixture(s), %d failure(s)" % (len(args.files), failures))
    return 1 if failures else 0


def cmd_order(args):
    rc = 0
    for path in args.files:
        try:
            data, _ = read_model(path, tab_width=args.tab_width)
        except ReadError as exc:
            print("READ ERROR: %s" % exc)
            rc = 2
            continue
        problems = check_member_order(data, path)
        print("%s: %s" % (os.path.basename(path),
                          "OK" if not problems else "%d problem(s)" % len(problems)))
        for p in problems:
            print("    %s" % p)
            rc = rc or 1
    return rc


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="roundtrip.py",
        description="Semantic round-trip comparison for RosTooling .ros2 / .rossystem "
                    "models. Byte-diffing is intentionally not offered.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="exit codes: 0 equal / 1 semantic difference / 2 read error / 3 usage",
    )
    parser.add_argument("--tab-width", type=int, default=2,
                        help="spaces per tab when de-tabbing indentation (default 2)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("compare", help="compare an original against a regenerated model")
    p.add_argument("original")
    p.add_argument("regenerated")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("selftest",
                       help="identity + neutral-perturbation + negative-control checks")
    p.add_argument("files", nargs="+")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_selftest)

    p = sub.add_parser("order", help="check the grammar-fixed member sequences")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_order)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
