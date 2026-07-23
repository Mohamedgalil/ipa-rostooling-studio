# RosTooling Emission Profile

**Work item E1 — CoreSense x Humanoid, Fraunhofer IPA**

Derivation of the clean, normalised output style the generator skill must emit for `.ros2` and
`.rossystem` files.

- **Corpus A** — `material/code/ros-model-examples/` — 229 `.ros2`, 51 `.rossystem`, 31 `.ros`.
  Hand-authored, inconsistent. Used for *frequency* evidence and for negative examples.
- **Corpus B** — `material/code/CS_ros2model_TBs/` — 24 `.ros2`, 1 `.rossystem`.
  Machine-extracted, internally consistent. **Weighted decisive** where the two conflict.
- **Grammar authority** — `RosTooling/plugins/.../{Basics,Ros}.xtext`, `.../Ros2.xtext`,
  `.../RosSystem.xtext`, and the two `*Validator.xtend` files.

Every rule below carries either a grammar citation (hard constraint) or a corpus count
(convention). Where the two corpora disagree, the disagreement is stated explicitly rather than
smoothed over.

> **Verification status.** No rule here has been executed against the shipped Xtext language
> server. `java -version` on this machine is `1.8.0_481`; the `*-ls.jar` files declare
> `Bundle-RequiredExecutionEnvironment: JavaSE-19` and `Build-Jdk-Spec: 19`, so they need a
> **JDK 19 or newer — provision Java 21 (Temurin LTS)**. Rules justified by grammar text are as
> reliable as reading; rules justified only by corpus frequency are conventions, not guarantees.
> See §6.
>
> *Corrected 2026-07-21:* this document previously said "Java 11+" in two places, contradicting
> `docs/grammar-subset.md` §1. The Java 11 figure came from the *class-file major version* (55) of
> the individual validator classes, which is a different thing from the bundle's declared execution
> environment. Provisioning a JDK 11 would **not** have been sufficient.

---

## 1. Measured findings

### 1.1 Indentation

Distribution of leading-whitespace widths on indented lines:

| Width | Corpus A `.ros2` | Corpus B `.ros2` |
|------:|-----------------:|-----------------:|
| 2 | 466 | 24 |
| 3 | 4 | — |
| 4 | 497 | 23 |
| 5 | — | 1 |
| 6 | 1 377 | 95 |
| 7 | 2 | — |
| 8 | 7 035 | 337 |
| 10 | 11 812 | 717 |
| 11 | 1 | — |
| 12 | 323 | 114 |
| 92 | 5 | — |
| **total** | **21 522** | **1 311** |

Even multiples of two: **21 510 / 21 522 = 99.94 %** (A) and **1 310 / 1 311 = 99.92 %** (B).
Every non-multiple-of-2 width is a singleton typo (the width-92 lines are a single wrapped
paste artefact).

Tabs, by file:

| | files with ≥1 tab |
|---|---|
| Corpus B `.ros2` | 0 / 24 |
| Corpus B `.rossystem` | 0 / 1 |
| Corpus A `.ros2` | 26 / 229 |
| Corpus A `.rossystem` | 26 / 51 |
| Corpus A `.ros` | 6 / 31 |

Corpus B is tab-free. Corpus A mixes tabs and spaces in half its system files — exactly the mess
the profile exists to avoid.

The nesting is a strict 2-space ladder. Corpus B `.ros2`:

```
nav2_amcl:                              0
  artifacts:                            2
    amcl:                               4
      node: amcl                        6
      publishers:                       6
        'amcl/transition_event':        8
          type: 'lifecycle_msgs/...'   10
          qos:                         10
            reliability: reliable      12
```

Corpus B `.rossystem`:

```
manufacturing_tb:                                    0
  nodes:                                             2
    robot_state_publisher:                           4
      from: "robot_state_publisher.robot_state..."   6
      interfaces:                                    6
        - "tf": pub-> "robot_state_publisher::tf"    8
      parameters:                                    6
        - "frame_prefix": "robot_state_pub::..."     8
          value: ""                                 10
```

### 1.2 Line endings and final newline

On-disk, all 305 model files are CRLF. **This is an artefact, not authored style.** Both clones
have `core.autocrlf=true`:

```
git -C ros-model-examples config core.autocrlf   -> true
git -C CS_ros2model_TBs  config core.autocrlf   -> true
```

Inspecting the *stored blobs* instead of the working tree:

| | blobs containing CR | pure-LF blobs |
|---|---|---|
| Corpus A | 0 | 280 |
| Corpus B | 0 | 25 |

**305 / 305 files are LF in the repository.** Any byte-level comparison done against the working
tree rather than the blob will produce a spurious CRLF signal.

Final newline (measured on blobs):

| | ends with `\n` | no final newline |
|---|---|---|
| Corpus A | 19 / 280 (6.8 %) | 261 |
| Corpus B | **24 / 25 (96 %)** | 1 (`amcl.ros2`) |

The corpora disagree sharply. Corpus B wins per the weighting rule; a trailing newline is also
what every POSIX tool and diff expects, and it guarantees the indentation lexer sees a clean
end-of-input at which to flush pending `END` tokens.

### 1.3 Quoting

`EString: STRING | ID` (Basics.xtext:391). Xtext's `STRING` terminal accepts either quote
character, so single vs double is **semantically invisible** — it is a style choice, not a
correctness one. `ID` cannot contain `.`, `/`, `:` or `-`, so any name containing those
**must** be quoted.

Two grammar positions are *not* `EString` and therefore can **never** be quoted:

```
RosNames returns ecore::EString:
    ROS_CONVENTION_A | ID | 'node'          Basics.xtext:394-396
```

`RosNames` has no `STRING` alternative. It governs the package name
(`AmentPackage.name`, Ros2.xtext:15), the artifact name (`Artifact.name`, Ros.xtext:116) and the
node name (`Node.name`, Ros.xtext:122). Corpus agrees without exception:

| position | bare | quoted |
|---|---:|---:|
| `.ros2` package name (col 0) | **253 / 253** | 0 |
| `.ros2` `node:` name | **267 / 267** | 0 |

To separate *required* quoting from *stylistic* quoting, each token was classified as
`QUOTED_NEEDED` (contains a character illegal in `ID`), `QUOTED_BUT_ID` (quoted although a bare
`ID` would have parsed), or `BARE_OK`:

**`.rossystem`**

| position | Corpus A | Corpus B |
|---|---|---|
| arrow target (`pub-> …`) | 431 QUOTED_NEEDED, 0 other | 191 QUOTED_NEEDED, 0 other |
| `from:` | 264 QUOTED_NEEDED, 0 other | 32 QUOTED_NEEDED, 0 other |
| interface local name | 295 BARE_OK, 74 QUOTED_BUT_ID, 60 QUOTED_NEEDED | **191 quoted, 0 bare** |

Arrow targets are `artifact::interface`, so `::` forces quoting — 622/622 required, never
optional. `from:` is `package.node`, so `.` forces quoting — 296/296 required. Neither can ever be
bare; this is structural, not conventional. (The two use *different* levels of the `.ros2` — see
rules 29 and 30.)

Interface local names are where the corpora part company: Corpus A quotes only when forced,
Corpus B quotes unconditionally (191/191, of which 116 would have parsed bare). Unconditional
quoting is the safer generator rule — it removes a per-name decision that Corpus A gets
inconsistently right, and it is what the machine generator already does.

Corpus A also contains two malformed entries in `turtlesim/turtlesim_system.rossystem`:

```
- cmd_vel_sub : sub-> "turtlesim_node::cmd_vel"
- cmd_vel_pub : pub-> "turtle_teleop_key::cmd_vel"
```

The space before `:` is legal (whitespace is hidden) but is a formatting defect. Note for
accuracy: these are *not* syntax errors, contrary to what a naive ID-regex scan suggests.

**`.ros2` interface and parameter names**

| | Corpus A | Corpus B |
|---|---|---|
| QUOTED_NEEDED | 4 143 | 144 |
| QUOTED_BUT_ID | 2 725 | 193 |
| BARE_OK | 50 | 0 |
| **quoted share** | **99.3 %** | **100 %** |

**Quote character.** A consistent split emerges in Corpus B — identifiers and type references take
single quotes, string *data* takes double quotes:

| position | `'` | `"` |
|---|---:|---:|
| B `.ros2` interface/param name, `type:` msg ref | **184** | 1 |
| B `.ros2` string `value:` | 0 | **31** |
| A `.ros2` string `value:` | 4 | **1 076** |
| A `.ros2` `fromGitRepo:` | 0 | **63** |
| A `.ros2` `type:` msg ref | 287 | **2 072** |
| A + B `.rossystem`, all ref positions | 0 | **~2 000** |

Corpus A prefers double quotes for `.ros2` type refs (2 072 vs 287) — the one place the corpora
genuinely conflict on quote character. Corpus B's split is adopted per the weighting rule, and it
has an independent virtue: it visually distinguishes references from data. Because the choice is
semantically invisible, **a validator must never flag the other quote character as an error.**

**`type:` has two distinct contexts** and they quote differently:

| context | form | count |
|---|---|---|
| message/service/action ref | always quoted (`/` forces it) | A 2 359, B 185 — 0 bare |
| parameter type keyword | always bare — it is a grammar keyword | A 3 423, B 152 — 0 quoted |

`Boolean`, `Double`, `String`, `Integer`, `Array[…]`, `List[…]`, `Struct[…]`, `Base64` are literal
keywords in `ParameterType` (Basics.xtext:51-110). Quoting one turns it into a parse error.

`Array` bracket spacing: `Array [` 121, `Array[` 73 corpus-wide; Corpus B uses `Array[String]`
(6/6). Whitespace is hidden, so both parse. Low stakes.

### 1.4 Parameter values — two silent-corruption traps

**Booleans.**

```
terminal BOOLEAN: 'true'|'false';               Basics.xtext:173
boolean0 returns type::Boolean: BOOLEAN;        Basics.xtext:186
ParameterBoolean returns ParameterBoolean: value=boolean0;   Basics.xtext:139
```

Only lowercase is a `BOOLEAN`. Measured:

| | `True`/`False` | `true`/`false` |
|---|---:|---:|
| A `.ros2` | **910** | 133 |
| B `.ros2` | 0 | **48** |
| A `.rossystem` | 0 | 149 |
| B `.rossystem` | 0 | 16 |

The premise that "`.ros2` uses `True/False` while `.rossystem` uses `true/false`" is **half right
and needs restating.** It is true that uppercase appears *only* in `.ros2`, and there it is the
majority in Corpus A (910 vs 133). But it is not a legal dialect — it is a bug. `ParameterValue`
is an alternation (Basics.xtext:54-55); when `True` fails `ParameterBoolean` it silently succeeds
as `ParameterString` (via `EString → ID`). So `type: Boolean` + `value: True` parses without
error and yields a **string** under a boolean type. No validator in `RosValidator.xtend` checks
value-against-type, so nothing reports it. Corpus B, the machine generator, emits lowercase
exclusively. Emit lowercase only.

**Doubles.**

```
terminal DOUBLE: (DIGIT* | ('-' DIGIT*)) (('.' DECINT*) | (('.' DIGIT*)? ('E'|'e') ('-'|'+')? DIGIT*));
```

A `DOUBLE` requires a `.` or an exponent. A bare `10` matches `DECINT`, so `type: Double` +
`value: 10` silently becomes a `ParameterInteger` — the same class of corruption. Corpus-wide scan
for `type: Double` followed by an integer literal: **0 occurrences**. Both corpora already emit
`10.0`, `20.0`, `1e-10`. Preserve that invariant.

Value shapes in Corpus B `.ros2` (n=152): 51 double, 48 lowercase boolean, 24 quoted string,
15 integer, 7 empty `""`, 6 list, 1 exponent-form double.

### 1.5 Ordering

**Grammar-fixed (violating these is a parse error):**

| rule | mandatory order | cite |
|---|---|---|
| `AmentPackage` | `fromGitRepo:` → `artifacts:` → `dependencies:` | Ros2.xtext:13-24 |
| `RosNode` (`.rossystem`) | `from:` → `namespace:` → `interfaces:` → `parameters:` | RosSystem.xtext:60-75 |
| `Publisher`/`Subscriber`/`ServiceServer`/… | `type:` → `ns:` → `qos:` | Ros2.xtext:49-112 |
| `Parameter` (`.ros2`) | `type:` → `ns:` → `value:` → `qos:` | Ros2.xtext:114-124 |

**Grammar-free, convention only.** `Node` (Ros.xtext:121-159) and `RosSystem`
(RosSystem.xtext:13-45) both use a repeated alternation `( A | B | … )*` — any order, and blocks
may even repeat. Convention must supply the order.

Node-level block order:

| | Corpus A | Corpus B |
|---|---|---|
| publishers before subscribers | 50 | **20 / 20** |
| subscribers before publishers | **104** | 0 |
| serviceservers before actionservers | **54** | 0 |
| actionservers before serviceservers | 0 | **5** |
| parameters last | — | **10 / 10** |

The two corpora conflict on *both* axes, and split the difference: Corpus B leads with publishers
(agreeing with the grammar's declaration order) but puts action blocks before service blocks
(disagreeing with it). The tie-breaker is the grammar's own declaration order —
`publishers, subscribers, serviceservers, serviceclients, actionservers, actionclients,
parameters` — which matches Corpus B on publishers-first *and* Corpus A's 54:5 majority on
services-before-actions. It is the only order supported by both an independent authority and a
corpus majority on each axis. **Corpus B's action-before-service placement is deliberately not
adopted**; this is the one point where the profile departs from the weighted-decisive corpus, and
the departure is recorded here rather than hidden.

Entry order *within* a block, tested per-block (not across block boundaries, which would give a
false negative):

| | SORTED | UNSORTED | single-entry |
|---|---:|---:|---:|
| Corpus B | **48** | 3 | 20 |
| Corpus A | 469 | 138 | 195 |

All three Corpus B "unsorted" blocks are caused by the same degenerate artefact — an
empty-string interface name `'':` sorting after `'footprint':` in
`global_costmap__global_costmap.ros2`, `local_costmap__local_costmap.ros2` and
`kmriiwa__robot_description_publisher.ros2`. Excluding that extraction defect, Corpus B is
**51/51 alphabetically sorted**. The empty name is itself a defect the generator must never
reproduce.

Interfaces inside a `.rossystem` node follow the same kind-grouping, alphabetical within each kind
(`MT.rossystem`, `gazebo`): `clock, performance_metrics` (pub) → `sub_clock` (sub) →
`pause_physics, reset_simulation, reset_world, unpause_physics` (ss).

**Interface local names must be unique within a node.** Corpus B renames on collision: `gazebo`
both publishes and subscribes `clock`, so the subscriber's local name becomes `sub_clock`. The
same `sub_`-prefix disambiguation appears for `sub_bond`,
`sub_cascade_lifecycle_states`, `sub_cascade_lifecycle_activations`. Corpus-wide there are only
2 duplicate local names, both in Corpus A. Duplicates break cross-reference resolution, since
`RosSystemConnection` resolves `[RosInterface|EString]` by name.

### 1.6 Comments

`terminal SL_COMMENT: '#' !('\n'|'\r')*` (Basics.xtext:386) — `#` to end of line, hidden.
No block-comment syntax.

Files containing any comment: Corpus B `.ros2` 23/24; Corpus A `.ros2` 198/229;
Corpus A `.rossystem` 22/51.

Corpus B's comments are almost entirely one stock trio, emitted once per QoS block (57 blocks ×
3 lines = 171 lines):

```
          qos:
          # profile:
          # history: UNKNOWN
          # depth:
            reliability: reliable
            durability: volatile
```

Indentation of comment lines relative to the next content line: **171/171 SHALLOWER** in
Corpus B. The comments sit at the indent of the *parent* (`qos:`, col 10) while the content sits
at col 12. Whether this matters is unverified — `SL_COMMENT` is hidden, and Xtext's
`AbstractIndentationTokenSource` is expected to skip comment-only lines when computing
indent/dedent, but that class lives in the Xtext runtime and could not be executed here (§6). The
conservative course is to reproduce the proven placement rather than assume comment indentation
is free.

Corpus A additionally contains 288 trailing comments and ASCII banner comments
(`##### Behavior Tree Framework #####`) — noise, not convention.

### 1.7 Naming: file stem vs model name

The name on line 1 is a **model name**, not a filename. They are frequently different.

| | stem == model name | differ |
|---|---:|---:|
| `.ros2` (A + B) | 177 | **76** |
| `.rossystem` (A + B) | 38 | **14** |

For `.ros2` the model name is the **ROS package**, while the file is usually named after the
**node**: `amcl.ros2` declares `nav2_amcl:`; `bt_navigator.ros2` declares `nav2_bt_navigator:`;
`rviz.ros2` declares `rviz2:`. For `.rossystem`, `MT.rossystem` declares `manufacturing_tb:`.

This drives a hard cross-file rule. `from:` in a `.rossystem` is
`<packageName>.<nodeName>` — resolved through the model, **never** through the filename:

```
from: "nav2_bt_navigator.bt_navigator"     # file is bt_navigator.ros2, package is nav2_bt_navigator
from: "gazebo_sensor_b1_controller.gazebo_sensor_B1_controller"
```

The second line also shows the case asymmetry: the **package** is lowercase while the
**artifact** keeps its uppercase `B1`. That follows directly from the validators:

```
checkNameConventionsPackage   -> error(...)    "Capital letters are not allowed"
checkNameConventionsNode      -> warning(...)  "not recommended"
checkNameConventionsArtifact  -> warning(...)  "not recommended"
checkNameConventionsParameter -> warning(...)  , suppressed when the remainder contains '.'
```

Package name is the only **ERROR**. Corpus compliance: **0 / 253** `.ros2` files have an uppercase
package name. Node/artifact uppercase does occur and is tolerated as a warning.

### 1.8 QoS field availability

| field | Corpus A | Corpus B | in shipped LS JAR |
|---|---:|---:|---|
| `reliability` | 118 | 57 | yes |
| `durability` | 106 | 57 | yes |
| `depth` | 16 | 0 | yes |
| `history` | 15 | 0 | yes |
| `profile` | 5 | 0 | yes |
| `lease_duration` | **0** | **0** | **no** |
| `liveliness` | **0** | **0** | **no** |
| `lifespan` | **0** | **0** | **no** |
| `deadline` | **0** | **0** | **no** |

The corpus independently confirms the pinning decision. The four fields added to
`RosTooling` HEAD after the JAR was built (2024-08-01) also have **zero** corpus usage — so
excluding them costs nothing and is justified twice over, by tool support *and* by convention.

Observed values: `reliability: reliable` 160, `durability: volatile` 132,
`durability: transient_local` 31, `reliability: best_effort` 15.

---

## 2. EMISSION PROFILE (normative)

Numbered rules. **MUST** = violating produces a parse/validation error or silent semantic
corruption. **SHALL** = convention; deviating parses, but breaks house style.

### Bytes and layout

1. **MUST** indent with spaces only. Never emit a tab.
   *Corpus B 0/25 files contain tabs; Corpus A 26/229 `.ros2` and 26/51 `.rossystem` do, and are
   the files the profile exists to normalise.*

2. **MUST** use exactly 2 spaces per nesting level, with indent width `2 × depth`.
   *99.94 % (A) and 99.92 % (B) of indented lines are even multiples of 2; all exceptions are
   singleton typos.*

3. **MUST** terminate lines with `LF` (`\n`). Never `CRLF`.
   *305/305 stored blobs are pure LF. Working-tree CRLF is a `core.autocrlf=true` checkout
   artefact and MUST NOT be treated as evidence.*

4. **SHALL** end the file with exactly one trailing `LF`.
   *Corpus B 24/25. Corpus A disagrees (19/280) and is overruled. Also guarantees the
   indentation lexer sees a clean end-of-input for pending `END` tokens.*

5. **SHALL NOT** emit trailing whitespace, and **SHALL NOT** emit blank lines inside an indented
   block.
   *Corpus B contains neither; blank lines inside indentation-sensitive blocks are an
   unverified risk against `AbstractIndentationTokenSource`.*

6. **SHALL NOT** emit a space before the `:` of a name.
   *Corpus B 0 occurrences; the only 2 in Corpus A are the malformed `turtlesim_system.rossystem`
   lines. Legal but defective.*

### Names that must never be quoted

7. **MUST** emit the `.ros2` package name (column 0), the artifact name, and the `node:` name
   **bare**, never quoted.
   *`RosNames: ROS_CONVENTION_A | ID | 'node'` (Basics.xtext:394) has no `STRING` alternative.
   Corpus: 253/253 and 267/267 bare.*

8. **MUST** emit the `.ros2` package name in lowercase, with `_` as the only separator.
   *`checkNameConventionsPackage` raises **error** on any uppercase (RosValidator.xtend).
   Corpus 0/253 violations.*

9. **SHALL** emit node, artifact and parameter names in lowercase where the source permits.
   *Same validators, but **warning** level only — do not mangle an upstream name such as
   `gazebo_sensor_B1_controller` to satisfy this.*

### Quoting

10. **MUST** quote any `EString` that is not a bare `ID` — i.e. containing `.`, `/`, `::`, `-`,
    a space, or empty.
    *`EString: STRING | ID` (Basics.xtext:391); `ID` admits none of these.*

11. **MUST** quote every `.ros2` interface name and parameter name, unconditionally — including
    names that would parse bare.
    *Corpus B 337/337 quoted (193 of them unnecessarily); Corpus A 99.3 %. Removes a per-name
    decision that Corpus A gets inconsistently right.*

12. **MUST** quote every `.rossystem` interface local name, `from:` value, arrow target, and
    parameter reference, unconditionally.
    *Corpus B 191/191, 32/32, 191/191, 37/37. Arrow targets (622/622) and `from:` (296/296) are
    structurally forced by `::` and `.` respectively.*

13. **SHALL** use `'single quotes'` in `.ros2` for interface names, parameter names, and message/
    service/action type references, and in `.ros` for spec references in a field's Type position.
    *Corpus B 184/185. `.ros` spec references are the same kind of token as a `.ros2` `type:`
    reference, so they follow the same rule; the corpus uses both characters there.*

    > **Settled 2026-07-21, do not re-open.** This rule and rule 14 were audited against
    > `skills/ros-model/SKILL.md` (the quoting table under hard rule 1) and against
    > `scripts/rosmodel_lint.py`. All three already agree: single quotes for `.ros2`/`.ros`
    > *references and names*, double quotes for *string data* and for everything in
    > `.rossystem`. The linter has **no rule keyed on the quote character at all**, which is
    > rule 15 working as intended. `tests/regenerated/turtlesim/turtlesim.ros2` using
    > `'cmd_vel'` where the corpus original uses `"cmd_vel"` is therefore **correct output**,
    > not a defect — Corpus A's preference for `"` in that position is the dialect rule 15
    > exists to tolerate.

14. **SHALL** use `"double quotes"` for all string **data**: `.ros2` parameter `value:`,
    `fromGitRepo:`, `fromFile:`, and every quoted token in `.rossystem`.
    *Corpus B `.ros2` values 31/31; Corpus A 1 076/1 080; `fromGitRepo` 63/63;
    `.rossystem` ~2 000/2 000.*

15. **SHALL NOT** treat the opposite quote character as an error when reading.
    *Xtext's `STRING` accepts both; the difference vanishes at parse time. Corpus A prefers `"`
    for `.ros2` type refs 2 072:287 — a legitimate dialect, not a defect.*

16. **MUST** emit parameter type keywords bare: `Boolean`, `Integer`, `Double`, `String`,
    `Base64`, `Array[T]`, `List[…]`, `Struct[…]`.
    *Grammar keywords (Basics.xtext:51-110). Corpus: 3 575 bare, 0 quoted. Quoting one is a parse
    error.*

17. **SHALL** emit `Array[String]` without a space before `[`.
    *Corpus B 6/6. Corpus A splits 121:73 the other way; whitespace is hidden, so this is
    cosmetic only.*

### Parameter values

18. **MUST** emit booleans lowercase — `true` / `false` — in **both** `.ros2` and `.rossystem`.
    *`terminal BOOLEAN: 'true'|'false'` (Basics.xtext:173). Uppercase `True` does not fail: it
    falls through the `ParameterValue` alternation to `ParameterString`, silently producing a
    string under a `Boolean` type. No validator detects this. Corpus B 48/48 lowercase; Corpus A
    `.ros2` has 910 uppercase — all latently corrupt.*

19. **MUST** emit `Double` values with a decimal point or exponent — `10.0`, not `10`.
    *`terminal DOUBLE` requires `.` or `E`/`e`; a bare `10` matches `DECINT` and silently becomes
    a `ParameterInteger`. Corpus: 0 violations — the invariant already holds.*

20. **MUST NOT** emit an empty interface or parameter name (`'':`).
    *An extraction defect present in 3 Corpus B files; it is also the sole cause of every
    "unsorted" block in Corpus B.*

### Ordering

21. **MUST** order `AmentPackage` members `fromGitRepo:` → `artifacts:` → `dependencies:`.
    *Ros2.xtext:13-24 — fixed sequence, not an alternation.*

22. **MUST** order `.rossystem` node members `from:` → `namespace:` → `interfaces:` →
    `parameters:`.
    *RosSystem.xtext:60-75 — fixed.*

23. **MUST** order interface members `type:` → `ns:` → `qos:`, and `.ros2` parameter members
    `type:` → `default:` → `ns:` → `value:` → `qos:`.
    *Ros2.xtext:49-124 — fixed.*

    *`default:` correction (2026-07-21).* Earlier revisions of this profile omitted `default:`
    entirely, and the skill inferred from that omission that it was illegal on a scalar parameter
    and should be rewritten to `value:`. **Both were wrong.** `default:` is an optional tail of
    **`ParameterType`**, not of `Parameter`, and Basics.xtext:72-110 attaches it to *every* scalar
    type rule (`ParameterIntegerType ::= 'Integer' ('default:' default=ParameterInteger)?`, and
    likewise for `String`, `Double`, `Boolean`, `Base64`), as well as to `ParameterArrayType`.
    Because `'type:' type=ParameterType` carries no `BEGIN`/`END`, the `default:` token lands as a
    sibling of `type:` and binds immediately after it. `default:` (the type's declared default) and
    `value:` (this parameter's assigned value) are **distinct metamodel slots and never
    interchangeable** — rewriting one into the other is a silent semantic change that parses
    cleanly and that no validator or linter detects. Preserve whichever key the input uses.
    `rosmodel_lint.py` has modelled this correctly since it was written (`param_keys = ["type",
    "default", "ns", "value", "qos"]`); this profile and the skill were the documents out of step.

23a. **MUST** order `.rossystem` **system-level** parameter members `ns:` → `type:` → `default:` →
    `value:`, with **no `qos:` member**.
    *`RosSystem.xtext` extends `Basics`, not `Ros2`, so the system-level `parameters:` block uses
    the unoverridden `Parameter` rule of Basics.xtext:41-49 — where `ns:` precedes `type:` and no
    `qos:` exists. This is the reverse of rule 23's `.ros2` order, which comes from `Ros2.xtext`'s
    `@Override`. The two blocks look similar and are not.*

24. **SHALL** order node blocks: `publishers` → `subscribers` → `serviceservers` →
    `serviceclients` → `actionservers` → `actionclients` → `parameters`.
    *The grammar permits any order (`Node`, Ros.xtext:121-159, is a repeated alternation), so
    convention must decide. This is the grammar's declaration order. It matches Corpus B on
    publishers-first (20/20) and Corpus A's majority on services-before-actions (54:5). Note the
    deliberate departure: Corpus B places action blocks before service blocks in 5 files; that
    placement is **not** adopted, because it is contradicted by both the grammar's declaration
    order and a 54:5 corpus majority.*

25. **SHALL** order top-level `.rossystem` blocks `fromFile:` → `subSystems:` → `processes:` →
    `nodes:` → `parameters:` → `connections:`.
    *RosSystem.xtext:13-45 is an alternation; this is the observed corpus order.*

26. **SHALL** sort entries within a block alphabetically (byte order) by name.
    *Corpus B 51/51 once the empty-name defect of rule 20 is excluded; Corpus A 469:138.*

27. **SHALL** group `.rossystem` interfaces by kind in the rule-24 order, sorting alphabetically
    within each kind.
    *`MT.rossystem` follows this throughout.*

28. **MUST** ensure interface local names are unique within a node; on collision, prefix the
    subordinate one by kind (`sub_clock`, `sub_bond`).
    *Corpus B's disambiguation convention. `RosSystemConnection` resolves
    `[RosInterface|EString]` by name, so duplicates break cross-referencing. Only 2 duplicates
    exist corpus-wide, both in Corpus A.*

### Connections and references

29. **MUST** form `.rossystem` `from:` as `<packageName>.<nodeName>` — the **node**, not the
    artifact — taken from the target model's contents, **never** from the `.ros2` filename.
    *`RosQNP.xtend` returns `pkg.name + "." + node_name` for a `Node`, reading the package from
    `obj.eContainer.eContainer`; the artifact level is skipped. Corpus: 52 `from:` values resolve
    as node-only, **0** as artifact-only, 244 ambiguous (`artifact == node`). Also: 76/253 `.ros2`
    files have a stem that differs from the declared package; `bt_navigator.ros2` declares
    `nav2_bt_navigator`, referenced as `"nav2_bt_navigator.bt_navigator"`.*

30. **MUST** form arrow targets and node-level parameter targets as
    `<artifactName>::<interfaceName>` — the **artifact**, not the node.
    *`RosQNP.xtend` returns `art.name + "::" + interface.name` from
    `obj.eContainer.eContainer as Artifact` for all six interface kinds and for `Parameter`; the
    package level is skipped. Corpus: 201 arrow targets resolve as artifact-only, **0** as
    node-only, 499 ambiguous. 622/622 quoted; `::` is what forces rule 12's quoting.*

    > **Rules 29 and 30 use opposite levels of the same `.ros2` file.** `from:` skips the artifact;
    > the arrows skip the package. In most models `artifact == node` so the difference is
    > invisible — until it is not. See `skills/ros-model/references/rossystem-syntax.md` §3.

31. **MUST** respect connection direction — `from` is always the server/publisher — and use only
    the matched pairs `pub->`/`sub->`, `ss->`/`sc->`, `as->`/`ac->`.
    *`checkPortPatterns` / `MatchPortMsgs`, RosSystemValidator.xtend:127. `MatchPortMsgs`
    additionally requires both endpoints resolve to the **same** type object — not merely equal
    type strings.*

### QoS

32. **MAY** emit `lease_duration:`, `liveliness:`, `lifespan:` or `deadline:` — but prefer not to,
    and never without cause.
    *Revised 2026-07-21. This rule previously said MUST NOT, because our only executable validator
    was the LS JAR shipped in `vscode-RosTooling/resources/`, built 2024-08-01 — before these
    fields were added to the grammar (commit `3d9e5ebd`, 2025-10-16). That pin was lifted by
    rebuilding the server from `ipa-esa/RosTooling@esa/main` (3.1.0-SNAPSHOT). Verified by A/B on
    oracle case 04, same file, only the JAR differing: legacy →* `mismatched input
    'lease_duration'` *(REJECTED); current → ACCEPTED, 0 diagnostics.*

    *Two reasons to still be sparing. **Portability:** anyone on an older toolchain build cannot
    lex the keyword, and it fails as a syntax error that corrupts the whole enclosing publisher,
    not as a warning. **Zero corpus precedent:** still 0 occurrences in 253 `.ros2` files, so no
    real model exercises this path.*

32a. **If emitting a duration, it must fit in a signed 32-bit int, in NANOSECONDS** — or be the
    literal `infinite`. Max ≈ **2.147 seconds**.
    *`RosValidator.CheckDuration` uses `Integer.parseInt`. Confirmed against the real validator
    2026-07-21 (oracle case 14): `deadline: "5000000000"` (5 s) → ERROR; `"1000"` and `infinite`
    pass. This rule became* more *relevant when rule 32 was relaxed — these fields are only
    emittable at all since then, and any human-plausible timeout exceeds the limit.*

33. **SHALL** restrict emitted QoS to `reliability:` and `durability:`.
    *The only two fields Corpus B uses (57 each). `profile`/`history`/`depth` are JAR-supported
    but rare (5/15/16 in Corpus A, 0 in Corpus B) — emit only on explicit request.*

34. **MUST** emit QoS durations, if ever unpinned, as a **quoted** string of digits parseable by
    32-bit `Integer.parseInt`, or the literal `infinite`.
    *`CheckDuration`, RosValidator.xtend. Moot while rule 32 holds.*

### Comments

35. **SHALL NOT** emit comments by default.
    *Comment-line indentation inside indentation-sensitive blocks is unverified (§6), and
    comments carry no model semantics.*

36. **SHALL**, when a comment is unavoidable, emit it as a whole-line `#` comment indented to the
    **parent** level — strictly shallower than the content that follows.
    *Corpus B 171/171 comment lines are shallower than the next content line. Reproduces the only
    placement proven against this toolchain in the wild.*

37. **SHALL NOT** emit trailing (end-of-line) comments or ASCII banner comments.
    *288 trailing comments and several banner blocks exist in Corpus A only; Corpus B has none.*

---

## 3. Grammar constructs with zero or near-zero corpus support

| construct | grammar | occurrences | verdict |
|---|---|---|---|
| `dependencies:` | Ros2.xtext:23 | **0** files (of 253 `.ros2`) | **Avoid** |
| `namespace:` (`.rossystem` node) | RosSystem.xtext:65 | **0** files | **Avoid** |
| `ns:` (`Namespace` on interfaces/params) | Ros2.xtext:54 etc. | **0** occurrences | **Avoid** |
| `processes:` / `threads:` | RosSystem.xtext:23, 51-58 | **1** file | **Avoid** |
| `subSystems:` | RosSystem.xtext:18 | 19 files | **Emit with warning** |
| `fromFile:` | RosSystem.xtext:16 | 20 files | **Emit** (optional) |
| `fromGitRepo:` | Ros2.xtext:17 | 63 files | **Emit** (optional) |
| `connections:` | RosSystem.xtext:39 | 21 files | **Emit** |
| QoS `lease_duration`/`liveliness`/`lifespan`/`deadline` | Ros2.xtext:38-41 | **0** | **May emit, sparingly** (rule 32, revised 2026-07-21) |
| QoS `profile`/`history`/`depth` | Ros2.xtext:33-35 | 5 / 15 / 16 | **Emit with warning** |
| `RosTopic/Service/ActionConnection` | RosSystem.xtext:135-145 | 0 unambiguous | **Avoid** |
| `Struct` / `List` / `Base64` / `Array` param types | Basics.xtext:58-110 | `Array` 194; others ~0 | `Array` **emit**; rest **avoid** |
| `ParameterAny` / `ParameterDate` | Basics.xtext:102, 152 | 0 (`Date` commented out of `ParameterType`) | **Never emit** |

**Rationale for each verdict.**

- **Avoid (`dependencies`, `namespace`, `ns`, `processes`/`threads`).** Each is grammatically
  valid but has no working example to pattern-match against, and none can be tested (§6). A
  construct with zero corpus instances is one whose interaction with the indentation lexer has
  never been observed. `dependencies:` is additionally risky because it is an inline
  bracketed list *inside* an indented block (`'[' Dependency (',' Dependency)* ']'`), a shape the
  corpus never exercises in that position. The single `processes:` example
  (`image_system_example.rossystem`) is itself malformed — its sibling `nodes:` block is indented
  5 spaces, violating rule 2 — so it is a weak model, not a good one. Omitting all four costs no
  expressiveness for the target use case.

- **Emit with warning (`subSystems`).** 19 files is real support, but every example is
  low-quality — the sampled one indents its reference with a **tab** and leaves it bare
  (`\tcob_gazebo`). Emit only when composition is explicitly requested, normalised to rules 1-2,
  and flag that the output pattern is reconstructed rather than copied.

- **Emit with warning (QoS `profile`/`history`/`depth`).** Supported by the JAR and attested in
  Corpus A, but Corpus B deliberately *comments them out* (`# profile:`, `# history: UNKNOWN`,
  `# depth:` — 57 blocks each). The machine generator knows these fields and chose to suppress
  them, most plausibly because the extractor could not determine a trustworthy value. Emit only
  when the caller supplies a concrete value.

- **Avoid (`RosTopicConnection` and siblings).** `Connection: ( => RosSystemConnection) |
  RosConnection` (RosSystem.xtext:123-124). The syntactic predicate `=>` makes
  `RosSystemConnection` win every parse whose bracket contents resolve as `RosInterface`
  references. Reaching the `RosConnection` branch requires names that fail to resolve as
  interfaces — fragile, and the grammar's own comment says so: *"By default the grammar will
  parse RosSystemConnection … RosConnections are also implemented but not used for now."*

- **Avoid (`Struct`, `List`, `Base64`).** `RosValidator` emits `info`-level format hints for all
  three, implying they are under-exercised even by the tool authors. `Array` is different — 194
  corpus occurrences — and should be emitted.

- **Never emit (`ParameterAny`, `ParameterDate`).** `ParameterDate` is commented out of the
  `ParameterType` alternation (Basics.xtext:52) — the rule exists but is unreachable.
  `ParameterAny` is likewise absent from `ParameterType`.

---

## 4. Canonical reference output

`.ros2` — every rule above applied:

```
nav2_amcl:
  artifacts:
    amcl:
      node: amcl
      publishers:
        'amcl/transition_event':
          type: 'lifecycle_msgs/msg/TransitionEvent'
          qos:
            reliability: reliable
            durability: volatile
        'amcl_pose':
          type: 'geometry_msgs/msg/PoseWithCovarianceStamped'
          qos:
            reliability: reliable
            durability: transient_local
      subscribers:
        'initialpose':
          type: 'geometry_msgs/msg/PoseWithCovarianceStamped'
        'map':
          type: 'nav_msgs/msg/OccupancyGrid'
      serviceservers:
        'amcl/change_state':
          type: 'lifecycle_msgs/srv/ChangeState'
      parameters:
        'alpha1':
          type: Double
          value: 0.2
        'use_sim_time':
          type: Boolean
          value: true
```

`.rossystem`:

```
manufacturing_tb:
  nodes:
    "robot_state_publisher":
      from: "robot_state_publisher.robot_state_publisher"
      interfaces:
        - "robot_description": pub-> "robot_state_publisher::robot_description"
        - "tf": pub-> "robot_state_publisher::tf"
        - "clock": sub-> "robot_state_publisher::clock"
      parameters:
        - "publish_frequency": "robot_state_publisher::publish_frequency"
          value: 20.0
        - "use_sim_time": "robot_state_publisher::use_sim_time"
          value: true
```

Differences from the Corpus B originals, all intentional: `qos:` placeholder comments dropped
(rule 35); node blocks reordered to services-before-actions (rule 24); node name quoted
consistently (rule 12 — Corpus B leaves the first node bare and quotes the other 31).

---

## 5. Deliberate deviations from Corpus B

Corpus B is weighted decisive, so each departure is recorded rather than left implicit.

| # | Corpus B does | Profile requires | Why |
|---|---|---|---|
| 24 | action blocks before service blocks (5 files) | services before actions | grammar declaration order + Corpus A 54:5 |
| 35 | 3 stock `#` placeholders per QoS block (171 lines) | no comments | no model semantics; indentation interaction unverified |
| 12 | first node name bare, other 31 quoted | all quoted | internal inconsistency in a single file |
| 4 | `amcl.ros2` has no final newline | always final newline | 24/25 of Corpus B itself |
| 20 | 3 files contain an empty name `'':` | never emit | extraction defect |

---

## 6. Verification status

No rule has been executed against the shipped language server.

- `java -version` → `1.8.0_481`. The `*-ls.jar` files under
  `vscode-RosTooling/resources/` declare `JavaSE-19`, so they require a **JDK 19+ (use Java 21
  Temurin LTS)**. **Nothing was run against the JAR.**
- Rules citing grammar text (7, 8, 10, 16, 18, 19, 21, 22, 23, 31, 32, 34) are as reliable as
  reading the grammar — a static, checkable claim.
- Rules citing only corpus frequency (1-6, 9, 11-15, 17, 20, 24-30, 33, 35-37) are conventions.
  They are safe in the sense that the corpus is accepted by the toolchain, but "the corpus does
  X" does not prove "not-X is rejected."
- Two open questions need a **JDK 19+ (Java 21 Temurin)** runtime to settle:
  1. whether comment-line indentation affects `BEGIN`/`END` synthesis (rules 35-36 are
     conservative pending this);
  2. whether blank lines inside indented blocks are tolerated (rule 5, likewise).
- To verify once a JDK 19+ is available: install it, run the `ros2` and `rossystem` language
  servers headless over a directory of generated files, and diff the reported diagnostics against
  an expected-empty baseline. Round-trip semantically (parse → compare model objects), **not**
  byte-wise against corpus originals — per the project's standing finding that corpus formatting
  is too inconsistent for byte-diffing to mean anything.

---

## 7. Correction to a prior project assumption

The briefing stated: *".ros2 uses True/False while .rossystem uses true/false — verify this."*

**Verified, and it is not a dialect split — it is a latent bug.** Uppercase does appear only in
`.ros2` (910 occurrences, Corpus A), and never in `.rossystem` (0 of 165). But
`terminal BOOLEAN: 'true'|'false'` admits lowercase only. Uppercase `True` does not raise an
error; it falls through the `ParameterValue` alternation and is captured by `ParameterString`,
so a `type: Boolean` parameter silently receives a **string** value. `RosValidator.xtend`
contains no value-against-type check, so nothing reports it. Corpus B — the machine generator —
emits lowercase exclusively (48/48). Rule 18 therefore mandates lowercase in **both** file types,
and the generator should treat `True`/`False` in any *input* it reads as a defect to normalise
rather than a convention to preserve.

A second, structurally identical trap was found in the same sweep and is covered by rule 19:
`type: Double` with an integer literal silently yields a `ParameterInteger`, because
`terminal DOUBLE` requires a `.` or an exponent. The corpus happens to have 0 violations, so this
one is a trap to avoid introducing rather than an existing defect.

A third briefing assumption also needed correction: **line endings.** The working tree is 100 %
CRLF, but that is entirely a `core.autocrlf=true` checkout artefact — all 305 stored blobs are
pure LF. Any tooling that samples the working tree will draw the wrong conclusion (rule 3).
