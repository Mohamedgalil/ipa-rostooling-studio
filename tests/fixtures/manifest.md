# Round-trip fixture manifest

**Work item E1 — CoreSense x Humanoid, Fraunhofer IPA**
**Date:** 2026-07-21
**Harness:** `../roundtrip.py`

Ten corpus models selected as the semantic regression set for the RosTooling emitter.
Every number below was measured, not estimated; the commands that produced them are recorded
in §5.

The fixtures are **read-only references** under
`C:\Users\mae\Downloads\adm-mae\CoreSense\material\code\`. Nothing in this directory copies
or modifies them — the manifest records paths, and `roundtrip.py` reads them in place.

---

## 1. Selection principle

The corpus is not a style guide. It is a *test load*. Fixtures were therefore chosen to
maximise coverage of the things that can break a reader or an emitter — tabs, absent optional
blocks, rare grammar constructs, and known authoring defects — rather than to showcase
well-formed files.

Two consequences worth stating up front:

- **Six of the ten contain a known defect.** That is deliberate. A fixture set of only clean
  files would not have caught the two modelling errors that these fixtures did catch during
  construction (§4).
- **Byte-diffing these files against emitter output is meaningless** and the harness does not
  offer it. All ten are CRLF in the working tree (a `core.autocrlf=true` checkout artefact —
  every stored blob is LF, per `emission-profile.md` §1.2), four lack a final newline, and
  three use indent widths that are not multiples of two. Comparison is semantic only.

---

## 2. The ten fixtures

Paths are relative to `material\code\`.

### F1 — `CS_ros2model_TBs\eu.coresense.testbeds\MT\MT.rossystem`

| | |
|---|---|
| Corpus | B (machine-extracted) |
| Size | 462 lines, 28 987 bytes, **487 canonical facts** |
| Selected for | **large model**; services **and** actions; `fromFile` **absent**; clean formatting |

The largest model in either corpus and the primary stress case. Exercises every interface kind:
69 `pub->`, 60 `sub->`, 80 `ss->`, 7 `as->`, 10 `ac->`. No `connections:`, `subSystems:` or
`processes:` block. Tab-free, LF blob, final newline present.

> **Note on the brief.** The task description states "MT.rossystem at 463 lines". The file is
> **462** newline-terminated lines (`wc -l` = 462, last byte is `0x0a`). The 463 figure counts
> the empty string after the final newline. Recorded so the discrepancy is not mistaken for a
> truncated fixture.

**Known defects:**

1. **Duplicate node keys — silently lossy under any dict-based reader.**
   `bt_navigator` is declared at lines 45 and 215; `robot_state_publisher` at lines 3 and 242.
   The file has **32 textual node keys but `yaml.safe_load` returns 30**. This is the single
   most important defect in the fixture set: a naive harness would compare a model missing two
   nodes and report success. `roundtrip.py` installs a duplicate-detecting loader and emits
   `DUPLICATE KEY ... earlier definition discarded`.
2. **Truncated interface target.** Line 251:
   `- "clock": pub-> "robot_state_publisher::c"` — the target is `::c`, not `::clock`. Every
   other `clock` interface in the file (lines 9, 24, 62, 64, 80, 85, 94, 100) uses the full
   name. An emitter must not reproduce this.
3. Node names are inconsistently quoted — `robot_state_publisher:` bare on line 3,
   `"robot_description_publisher":` quoted on line 247 (`emission-profile.md` §5, deviation 12).

### F2 — `ros-model-examples\image_system_example\image_system_example.rossystem`

| | |
|---|---|
| Corpus | A (hand-authored) |
| Size | 16 lines, 424 bytes, 14 canonical facts |
| Selected for | **the only model in either corpus using `processes:`** |

Mandatory by uniqueness. Contains `processes:` with a nested `nodes: [ ... ]` flow sequence and
`threads: 1` (`RosSystem.xtext`:23, 51-58). Also the only fixture exercising
`RosSystemValidator.checkIfNodeInSystem` (S1), which requires every name in a process's
`nodes:` list to be declared in the system's `nodes:` block.

**Known defects:**

1. **`-[` connection syntax with no space after the dash** (line 15: `    -[ image_output, image_input]`).
   Legal DSL — whitespace is hidden by the grammar — but YAML reads it as a plain *scalar*,
   not a sequence, so the connection would silently vanish. Motivates pre-normalisation rule 5.
2. Node bodies indented **5 spaces**, violating the 2-space ladder (`emission-profile.md` rule 2).
   `emission-profile.md` §3 already flags this file as "a weak model, not a good one".
3. No final newline.

### F3 — `ros-model-examples\manipulation\MANI02_common\subsystem\ur5e_cell_moveit.rossystem`

| | |
|---|---|
| Corpus | A |
| Size | 74 lines, 3 952 bytes, 82 canonical facts |
| Selected for | **`fromFile` PRESENT**; services **and** actions; system-level `parameters:` |

The `fromFile`-present counterpart to F1/F2/F4/F5/F6. Arrows: 9 `pub->`, 4 `sub->`, 19 `ss->`,
1 `sc->`, 3 `as->` — the densest service block in the corpus. Tab-free, final newline present.

This fixture **found a bug in the harness** (§4.1): its system-level `parameters:` block uses
the *declared* `Parameter` shape (a mapping `name: {type: String}`, per `RosSystem.xtext`:34-38),
not the *assigned* `RosParameter` list shape (`- name: ref` + `value:`) used inside nodes. The
canonicaliser originally handled only the list shape.

**Known defect:** the `connections:` block at line 61 is **empty** — both entries are commented
out. An indented block with no content is a questionable shape against
`AbstractIndentationTokenSource` (`'connections:' BEGIN connections+=Connection* END`), and is
unverifiable without the oracle. The emitter should omit an empty block rather than emit one.

### F4 — `ros-model-examples\manipulation\MANI02_common\pickQrCode.rossystem`

| | |
|---|---|
| Corpus | A |
| Size | 89 lines, 5 366 bytes, 97 canonical facts, 11 connections |
| Selected for | **`subSystems:` PRESENT**; **tabs**; all six arrow kinds |

Carries two coverage requirements at once. `subSystems:` appears in only 19 corpus files and is
rated *"emit with warning"* by `emission-profile.md` §3. This is also the only fixture using
**every** interface kind: 10 `pub->`, 3 `sub->`, 4 `ss->`, 1 `sc->`, 8 `as->`, 9 `ac->` — so it
exercises all three legal connection pairings of `checkPortPatterns` (S4).

**Known defects:**

1. **Trailing tabs** at end of line 32 (after the closing quote). These break the YAML scanner
   with `found character '\t' that cannot start any token` even though no *indentation* is
   affected. Motivates pre-normalisation rule 6.
2. **Duplicate interface local names within one node.** In `realsense_camera_driver`,
   `"/camera_info"` appears at lines 17 and 20 and `"/metadata"` at lines 19 and 22, with
   different targets (`color/...` vs `depth/...`). This violates `emission-profile.md` rule 28
   and breaks `RosSystemConnection`'s name-based cross-referencing. It **found the second
   harness bug** (§4.2).
3. No final newline.

### F5 — `ros-model-examples\cob\MOBI01_SIM\mininum_teleop.rossystem`

| | |
|---|---|
| Corpus | A |
| Size | 31 lines, 1 121 bytes, 29 canonical facts |
| Selected for | **leading-tab indentation** (the classic messy case), small |

The clean demonstration of the tab path: two interface lines are indented `6 spaces + TAB`
under a `interfaces:` key at 6 spaces. Raw `yaml.safe_load` fails; de-tabbing recovers it.
Small enough that the whole model can be eyeballed against the harness output.

**Known defects:** leading tabs (2 lines); space before `:` in parameter names
(`- "scale_linear.x" : "..."`); trailing whitespace on value lines; no final newline.
Note the filename itself is misspelled (`mininum`) while the model declares `minimum_teleop:` —
a live example of `emission-profile.md` rule 29: **`from:` must be built from the declared model
name, never the filename.**

### F6 — `ros-model-examples\turtlesim\turtlesim_system.rossystem`

| | |
|---|---|
| Corpus | A |
| Size | 12 lines, 345 bytes, **10 canonical facts** |
| Selected for | **trivial model** (the floor case) |

The smallest non-degenerate model in the corpus: two nodes, one interface each, one connection.
Its value is as a floor case — if the harness reports anything at all on a 10-fact model, the
report is easy to verify by hand.

**Known defects:** the two malformed interface lines called out by name in
`emission-profile.md` §1.3 — `- cmd_vel_sub : sub-> "..."` with a space before the colon (legal,
since whitespace is hidden, but a formatting defect); 7-space indentation on interface lines;
`-[cmd_vel_pub, cmd_vel_sub]` with no space after the dash (same as F2); no final newline.

### F7 — `CS_ros2model_TBs\eu.coresense.testbeds\MT\components\bt_navigator.ros2`

| | |
|---|---|
| Corpus | B |
| Size | 115 lines, 4 697 bytes, 100 canonical facts |
| Selected for | **the only Corpus B `.ros2` with services *and* actions**; QoS |

The richest clean `.ros2` file: `publishers`, `subscribers`, `serviceservers`, `actionservers`,
`actionclients` and `parameters` all present, plus QoS blocks. **Zero notes** from the
canonicaliser — this is the reference for what defect-free input looks like, and the control
against which the six defective fixtures are read.

### F8 — `CS_ros2model_TBs\eu.coresense.testbeds\MT\components\global_costmap__global_costmap.ros2`

| | |
|---|---|
| Corpus | B |
| Size | 250 lines, 7 752 bytes, **225 canonical facts** |
| Selected for | **largest `.ros2`**; QoS-heavy; the empty-name extraction defect |

The `.ros2` scale case (F1 is the `.rossystem` scale case). Five QoS blocks; a parameter block
large enough to exercise the `Array[...]` / `Double` / `Boolean` typing paths.

**Known defect:** an **empty interface name** `'':` in the `subscribers` block — the extraction
artefact named in `emission-profile.md` rule 20, which is also the sole cause of every
"unsorted" block in Corpus B. The harness reports
`EMPTY interface name in subscribers of artifact global_costmap`. The emitter must never
reproduce it.

### F9 — `CS_ros2model_TBs\eu.coresense.testbeds\MT\components\amcl.ros2`

| | |
|---|---|
| Corpus | B |
| Size | 71 lines, 2 222 bytes, 47 canonical facts |
| Selected for | **QoS-heavy** (5 QoS blocks); the no-final-newline case |

Small enough to use as the worked `compare` example (§5.3) while still carrying five QoS blocks
covering `reliability: reliable`, `reliability: best_effort`, `durability: volatile` and
`durability: transient_local` — the four values that account for essentially all QoS usage
corpus-wide (`emission-profile.md` §1.8).

**Known defect:** the **only file in Corpus B without a final newline** — the explicit exception
recorded in `emission-profile.md` §5, deviation 4. Fixes the rule-4 boundary case in place.

### F10 — `ros-model-examples\manipulation\MANI02_common\nav2_lifecycle_manager.ros2`

| | |
|---|---|
| Corpus | A |
| Size | 90 lines, 3 366 bytes, 84 canonical facts |
| Selected for | **messy Corpus A `.ros2`**; the missing-space-after-colon case |

The `.ros2` counterpart to the messy `.rossystem` fixtures, and the witness for
pre-normalisation rule 4.

**Known defects:**

1. **`type:Array [String]` — no space after the colon** (line 74). The grammar treats `type:`
   as a keyword *token* with hidden whitespace, so this is **legal DSL**; YAML rejects it with
   `mapping values are not allowed here`. This is the clearest single demonstration that the
   YAML reader is an *approximation* of the Xtext grammar. Ten `.ros2` files share this defect.
2. `subscribers:` before `publishers:` — the Corpus A block ordering, contradicting
   `emission-profile.md` rule 24. Legal (the `Node` rule is a repeated alternation) but not
   house style, so it exercises the harness's order-insensitivity for name-keyed blocks.
3. No final newline.

---

## 3. Coverage matrix

Every requirement from the task brief, mapped to the fixture that satisfies it.

| Requirement | Fixtures | Evidence |
|---|---|---|
| tab-indented files | **F5** (leading tabs), **F4** (trailing tabs) | raw `yaml.safe_load` fails on both |
| clean files | **F1, F7, F8, F9** | Corpus B, 0 tabs |
| `fromFile` present | **F3** | `fromFile:` line 2 |
| `fromFile` absent | **F1, F2, F4, F5, F6** | harness emits the `fromFileHelper` null-deref note |
| `subSystems:` present | **F4** | 1 of only 19 corpus files |
| the single `processes:` model | **F2** | unique in both corpora |
| QoS-heavy | **F7, F8, F9** | 2 / 5 / 5 QoS blocks |
| services **and** actions | **F1, F3, F4, F7** | `ss->`+`as->` co-occurrence |
| trivial model | **F6** | 12 lines, 10 facts |
| large model | **F1** (462 lines / 487 facts), **F8** (250 / 225) | |

**Secondary coverage** — every pre-normalisation rule in `roundtrip.py` has a witness, so no
rule is speculative:

| Pre-normalisation rule | Witness |
|---|---|
| 2 — CRLF → LF | all ten (working tree is 100 % CRLF) |
| 3 — tabs in indent → spaces | F5 |
| 4 — space after key colon | F10 |
| 5 — `-[` → `- [` | F2, F6 |
| 6 — strip trailing whitespace | F4 |
| duplicate mapping-key detection | F1 |
| duplicate canonical-path retention | F4 |

Both corpora are represented: **B** = F1, F7, F8, F9; **A** = F2, F3, F4, F5, F6, F10.
Both file types are represented: **`.rossystem`** = F1–F6; **`.ros2`** = F7–F10.

---

## 4. Defects the fixtures found in the harness itself

Recorded because they are the evidence that the fixture set does real work.

### 4.1 Second parameter shape (found by F3)

`_canon_params` assumed the node-level `RosParameter` list shape (`- name: ref` + `value:`).
F3's **system-level** `parameters:` block uses the declared `Parameter` mapping shape
(`name: {type: String}`, `RosSystem.xtext`:34-38). The harness reported
`unrecognised parameter entry {...} under system` — i.e. it was **discarding an entire
parameter block**. Fixed by splitting into `_canon_declared_params` (mapping) and
`_canon_params` (list), with each dispatching on the shape actually present.

### 4.2 Lossy canonicalisation on duplicate names (found by F4)

`Canon.put` overwrote on key collision. F4's duplicate `/camera_info` and `/metadata` interface
names therefore **lost the first of each pair**, exactly reproducing the YAML duplicate-key
failure mode the harness was built to expose. Fixed: `put` now suffixes colliding paths
`#2`, `#3`, … and notes the collision, so canonicalisation is lossless and a duplicate surfaces
as a real difference.

Neither bug is detectable with clean fixtures. Both were found on the first verbose run.

---

## 5. Verified harness runs

Interpreter: `C:\Users\mae\AppData\Local\Programs\Python\Python312\python.exe` (CPython 3.12.6),
PyYAML 6.0.3 (installed during this work; `python -m pip install pyyaml`).

> **Not verified against the real oracle.** No language server was executed. The shipped `.ros2`
> LS jar requires **Java 19** (`grammar-subset.md` §1 — note this corrects the earlier project
> assumption of Java 11) and this machine has `1.8.0_481`; and there is **no `.rossystem`
> language server at all** (`validator-rules.md` §0.2), so `.rossystem` can never be checked
> against shipped artefacts. Everything below tests the harness's own consistency.

### 5.1 Self-test on all ten fixtures

A file compared to itself would pass even if `compare()` were `return []`. The self-test
therefore runs four checks per fixture, two of which must return *equal* and one of which must
return *different*:

- **IDENTITY** — file vs. itself. Must be equal. (The check the brief asks for.)
- **TEXT-PERTURB** — vs. a semantically neutral reformat: 2→4-space ladder, indentation converted
  to **tabs**, single quotes flipped to double, CRLF line endings, final newline removed. Must be
  equal. This is the check that proves byte-level noise is ignored.
- **ORDER-PERTURB** — vs. a copy with every mapping reordered. Must be equal. Proves
  order-insensitivity where the grammar keys by name.
- **NEG-CONTROL** — vs. a copy with a node/artifact deleted. Must be **different**; the count of
  detected differences is shown in parentheses. This is what proves the comparator is not vacuous.

```
> python tests\roundtrip.py selftest -v <10 fixtures>

FIXTURE                              IDENTITY   TEXT-PERTURB   ORDER-PERTURB  NEG-CONTROL
-------------------------------------------------------------------------------------------
MT.rossystem                         PASS       PASS           PASS           PASS(36)
      NOTE DUPLICATE KEY 'bt_navigator' at line 215 -- earlier definition discarded by the YAML reader; the DSL would have kept both
      NOTE DUPLICATE KEY 'robot_state_publisher' at line 242 -- earlier definition discarded by the YAML reader; the DSL would have kept both
      NOTE no fromFile: -- corpus-normal (32/52) but trips the unguarded null dereference in RosSystemValidator.fromFileHelper
image_system_example.rossystem       PASS       PASS           PASS           PASS(4)
      NOTE no fromFile: -- corpus-normal (32/52) but trips the unguarded null dereference in RosSystemValidator.fromFileHelper
ur5e_cell_moveit.rossystem           PASS       PASS           PASS           PASS(14)
pickQrCode.rossystem                 PASS       PASS           PASS           PASS(8)
      NOTE no fromFile: -- corpus-normal (32/52) but trips the unguarded null dereference in RosSystemValidator.fromFileHelper
      NOTE DUPLICATE interface local name '/camera_info' under node[realsense_camera_driver]
      NOTE duplicate canonical path node[realsense_camera_driver].interface[/camera_info].kind -- kept as ...#2
      NOTE duplicate canonical path node[realsense_camera_driver].interface[/camera_info].target -- kept as ...#2
      NOTE DUPLICATE interface local name '/metadata' under node[realsense_camera_driver]
      NOTE duplicate canonical path node[realsense_camera_driver].interface[/metadata].kind -- kept as ...#2
      NOTE duplicate canonical path node[realsense_camera_driver].interface[/metadata].target -- kept as ...#2
mininum_teleop.rossystem             PASS       PASS           PASS           PASS(12)
      NOTE no fromFile: -- corpus-normal (32/52) but trips the unguarded null dereference in RosSystemValidator.fromFileHelper
turtlesim_system.rossystem           PASS       PASS           PASS           PASS(4)
      NOTE no fromFile: -- corpus-normal (32/52) but trips the unguarded null dereference in RosSystemValidator.fromFileHelper
bt_navigator.ros2                    PASS       PASS           PASS           PASS(99)
global_costmap__global_costmap.ros2  PASS       PASS           PASS           PASS(224)
      NOTE EMPTY interface name in subscribers of artifact global_costmap (emission-profile rule 20)
amcl.ros2                            PASS       PASS           PASS           PASS(46)
nav2_lifecycle_manager.ros2          PASS       PASS           PASS           PASS(82)

10 fixture(s), 0 failure(s)
EXITCODE=0
```

Every note above is a **true statement about the fixture**, cross-checked against the file in §2.

### 5.2 Order check — grammar-fixed member sequences

Violating the four fixed sequences (`emission-profile.md` rules 21-23) is a *parse error*, not
a model difference, so it is reported separately.

```
> python tests\roundtrip.py order amcl.ros2 MT.rossystem nav2_lifecycle_manager.ros2
amcl.ros2: OK
MT.rossystem: OK
nav2_lifecycle_manager.ros2: OK
EXITCODE=0
```

F10 passes despite its `subscribers:`-before-`publishers:` ordering — correctly, because `Node`
is a repeated alternation and that ordering is a house-style deviation, not a parse error.

Negative control on a hand-built file that violates all three `.ros2` sequences:

```
> python tests\roundtrip.py order badorder.ros2
badorder.ros2: 3 problem(s)
    nav2_amcl: ament_package order is artifacts -> fromGitRepo, grammar requires fromGitRepo -> artifacts
    amcl/publishers/amcl_pose: interface order is qos -> type, grammar requires type -> qos
    amcl/parameters/alpha1: ros2_parameter order is value -> type, grammar requires type -> value
EXITCODE=1
```

### 5.3 Worked `compare` — the actual use case

F9 against a "regenerated" copy that is **reformatted neutrally** (2→4-space ladder, single
quotes flipped to double) **and semantically damaged** in three specific ways: one QoS value
changed, one message type changed, one publisher renamed.

```
> python tests\roundtrip.py compare amcl.ros2 amcl_regen.ros2

facts: 47 original / 47 regenerated

RESULT: 10 SEMANTIC DIFFERENCE(S)

  category     missing   extra  changed
  --------------------------------------
  interface          1       1        0
  qos                2       2        1
  type               1       1        1

  [interface]
    - MISSING  artifact[amcl].pub[amcl_pose] = True
    + EXTRA    artifact[amcl].pub[amcl_pose_renamed] = True

  [qos]
    - MISSING  artifact[amcl].pub[amcl_pose].qos.durability = 'transient_local'
    - MISSING  artifact[amcl].pub[amcl_pose].qos.reliability = 'reliable'
    + EXTRA    artifact[amcl].pub[amcl_pose_renamed].qos.durability = 'transient_local'
    + EXTRA    artifact[amcl].pub[amcl_pose_renamed].qos.reliability = 'reliable'
    ~ CHANGED  artifact[amcl].pub[amcl/transition_event].qos.reliability
        original    'reliable'
        regenerated 'best_effort'

  [type]
    - MISSING  artifact[amcl].pub[amcl_pose].type = 'geometry_msgs/msg/PoseWithCovarianceStamped'
    + EXTRA    artifact[amcl].pub[amcl_pose_renamed].type = 'geometry_msgs/msg/PoseWithCovarianceStamped'
    ~ CHANGED  artifact[amcl].sub[map].type
        original    'nav_msgs/msg/OccupancyGrid'
        regenerated 'nav_msgs/msg/GridCells'

EXITCODE=1
```

The reformatting produced **zero false positives**; all three real changes were detected and
correctly categorised. A byte diff of these two files would have reported every line as changed.

### 5.4 Read-error path

```
> python tests\roundtrip.py compare cob_navi_robot.rossystem cob_navi_robot.rossystem
READ ERROR: ...\cob_navi_robot.rossystem: unreadable at line 40: expected <block end>, but found '-'
EXITCODE=2
```

Unreadable input is an **error**, never a silent pass. Exit codes: `0` equal / `1` semantic
difference / `2` read error / `3` usage.

---

## 6. Corpus files deliberately excluded

13 of 52 `.rossystem` and 15 of 253 `.ros2` files remain unreadable after pre-normalisation.
They are excluded from the fixture set because they are **genuinely malformed** — not because
the reader is weak — and none of their defects is a shape an emitter would ever produce:

| Defect class | Files | Example |
|---|---|---|
| `parameters:` list dedented below its parent key | 6 `.rossystem` | `cob_navi_robot.rossystem` line 40 |
| `value:` over-indented under its list item | 6 `.rossystem` | `cob_combi_sim.rossystem` line 33 |
| C-style `/* … */` comment | 1 `.rossystem` | `MANI02_PILZ\pickQrCode.rossystem` line 162 |
| assorted broken indentation | 15 `.ros2` | `man2_bt_operator.ros2` |

The DSL's only comment syntax is `terminal SL_COMMENT: '#' !('\n'|'\r')*` (`Basics.xtext`:386),
so the `/* … */` case is invalid DSL, not merely invalid YAML.

**Readable after pre-normalisation: 39/52 `.rossystem` (75 %), 238/253 `.ros2` (94 %).**
Baseline with raw `yaml.safe_load`: 26/52 and 228/253.

---

## 7. Reproducing

```bash
PY="C:\Users\mae\AppData\Local\Programs\Python\Python312\python.exe"
C="C:\Users\mae\Downloads\adm-mae\CoreSense\material\code"

"$PY" -m pip install pyyaml

"$PY" tests\roundtrip.py selftest -v \
  "$C\CS_ros2model_TBs\eu.coresense.testbeds\MT\MT.rossystem" \
  "$C\ros-model-examples\image_system_example\image_system_example.rossystem" \
  "$C\ros-model-examples\manipulation\MANI02_common\subsystem\ur5e_cell_moveit.rossystem" \
  "$C\ros-model-examples\manipulation\MANI02_common\pickQrCode.rossystem" \
  "$C\ros-model-examples\cob\MOBI01_SIM\mininum_teleop.rossystem" \
  "$C\ros-model-examples\turtlesim\turtlesim_system.rossystem" \
  "$C\CS_ros2model_TBs\eu.coresense.testbeds\MT\components\bt_navigator.ros2" \
  "$C\CS_ros2model_TBs\eu.coresense.testbeds\MT\components\global_costmap__global_costmap.ros2" \
  "$C\CS_ros2model_TBs\eu.coresense.testbeds\MT\components\amcl.ros2" \
  "$C\ros-model-examples\manipulation\MANI02_common\nav2_lifecycle_manager.ros2"

# once the emitter exists:
"$PY" tests\roundtrip.py compare <original> <regenerated>
```

---

## 8. Open items

1. **Oracle verification is blocked.** Provision a **JDK 19** (not 11 — see `grammar-subset.md`
   §1) and run the `.ros2` language server over stdio per `grammar-subset.md` §7. Until then
   every fixture is *unverified-pending-Java*: the harness proves emitter output is
   *self-consistent*, not that the real parser accepts it.
2. **`.rossystem` has no oracle and never will** from shipped artefacts. Validating F1–F6
   against a real parser requires building `de.fraunhofer.ipa.rossystem.xtext` from source.
3. **Validator rules are not yet enforced** by this harness. It compares models; it does not
   check `checkPortPatterns` (S4), `MatchPortMsgs` (S5) or the naming rules (R1–R4). Those
   belong in a separate linter — `validator-rules.md` §5 has the prioritised list. F4 (all six
   arrow kinds) and F2 (`processes:`) are the fixtures that will exercise it.
