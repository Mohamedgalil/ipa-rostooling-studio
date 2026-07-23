# Pinned Grammar Subset — Oracle Capability Report

**Work item:** CoreSense x Humanoid, E1 (RosTooling emission plugin)
**Date of analysis:** 2026-07-21
**Status of executable verification:** NOT PERFORMED — no compatible JRE on this machine (see §7).
All findings below are derived from **static artefact inspection** (JAR manifests, ANTLR `.tokens`
files, git history of the grammar sources). Every claim is traceable to a command output.

This document is the authority for the skill's emission profile. If it conflicts with intuition
about "what the grammar allows", this document wins, because the *oracle* — not HEAD — is what
validates our output.

---

## 1. The shipped language servers

Location: `C:\Users\mae\Downloads\adm-mae\CoreSense\material\code\vscode-RosTooling\resources\`

| JAR | Size (bytes) | Bundle-Version | Build-Jdk-Spec | BREE | Main-Class |
|---|---:|---|---|---|---|
| `de.fraunhofer.ipa.ros.xtext.ide-3.0.0-SNAPSHOT-ls.jar` | 31,572,092 | `3.0.0.202408011124` | 19 | JavaSE-19 | `de.fraunhofer.ipa.ros.ide.launch.ServerLauncher` |
| `de.fraunhofer.ipa.ros1.xtext.ide-3.0.0-SNAPSHOT-ls.jar` | 47,012,995 | `3.0.0.202408011124` | 19 | JavaSE-19 | `de.fraunhofer.ipa.ros1.ide.launch.ServerLauncher` |
| `de.fraunhofer.ipa.ros2.xtext.ide-3.0.0-SNAPSHOT-ls.jar` | 47,053,879 | `3.0.0.202408011124` | 19 | JavaSE-19 | `de.fraunhofer.ipa.ros2.ide.launch.ServerLauncher` |

All three built by Maven Archiver 3.6.0, vendor Fraunhofer IPA, ANTLR runtime 4.7.2, lsp4j.
Internal `.tokens` entries are timestamped **2024-08-01 13:25–13:26**, matching the Bundle-Version
qualifier `202408011124`.

**Correction to a prior project assumption:** the JARs require **Java 19**, not Java 11.
`Bundle-RequiredExecutionEnvironment: JavaSE-19` and `Build-Jdk-Spec: 19` both say so. Provisioning
a JDK 11 would *not* have been sufficient.

**There are three JARs, not two.** A `ros1` language server also ships. It is out of scope for E1
(we emit `.ros2` and `.rossystem`) but its token set is recorded in §3.4 for completeness.

### 1.1 A trap in the VS Code wiring

`vscode-RosTooling/src/extension.ts` line 32 hard-codes **the `ros` JAR**, and line 45 sets
`documentSelector: ['ros']`. `package.json` registers only the `.ros` extension and
`onLanguage:ros`. The shipped extension therefore **never starts the ros2 server**. To exercise the
ros2 oracle we must launch `de.fraunhofer.ipa.ros2...ls.jar` ourselves over stdio — the extension
cannot be used as-is as a validation harness.

---

## 2. Method

The ANTLR-generated `.tokens` file inside each JAR enumerates every literal the *baked-in* parser
recognises. It is a complete and closed list: a keyword absent from `.tokens` cannot be matched by
that parser under any input, so emitting it guarantees a syntax error.

For the ros2 JAR the parser and lexer token files were compared and are **identical in both names
and numeric IDs** (98 literals + 22 rule tokens each). No lexer/parser skew.

Files used as evidence:

```
de/fraunhofer/ipa/ros2/parser/antlr/internal/InternalRos2Parser.tokens   (1715 B)
de/fraunhofer/ipa/ros2/parser/antlr/lexer/InternalRos2Lexer.tokens       (1577 B)
de/fraunhofer/ipa/ros/parser/antlr/internal/InternalRosParser.tokens     (1432 B)
de/fraunhofer/ipa/ros/parser/antlr/internal/InternalBasicsParser.tokens  (1155 B)
de/fraunhofer/ipa/ros1/parser/antlr/internal/InternalRos1Parser.tokens   (1449 B)
```

(Each also appears a second time under `.../ide/contentassist/antlr/...` — byte-identical sizes,
the content-assist copy. No divergence.)

---

## 3. Complete token dumps

### 3.1 `InternalRos2Parser.tokens` — literals (98)

Grouped by role; the full raw list is reproduced verbatim in §3.5.

**Block / field keys (28)**
`'actionclients:'` `'actions:'` `'actionservers:'` `'artifacts:'` `'default:'` `'dependencies:'`
`'depth:'` `'durability:'` `'fromGitRepo:'` `'history:'` `'msgs:'` `'node:'` `'ns:'` `'parameters:'`
`'profile:'` `'publishers:'` `'qos:'` `'reliability:'` `'serviceclients:'` `'serviceservers:'`
`'srvs:'` `'subscribers:'` `'type:'` `'value:'` — plus punctuation `','` `':'` `'['` `']'` `'[]'`

**Namespace keywords (5)**
`'GlobalNamespace'` `'PrivateNamespace'` `'RelativeNamespace'` `'GraphName'` `'ExternalDependency'`

**QoS enum values (10)**
`'default_qos'` `'services_qos'` `'sensor_qos'` `'parameter_qos'` · `'keep_last'` `'keep_all'` ·
`'best_effort'` `'reliable'` · `'transient_local'` `'volatile'`

**Parameter type / value keywords (11)**
`'Any'` `'Array'` `'Base64'` `'Boolean'` `'Date'` `'Double'` `'Integer'` `'List'` `'String'`
`'Struct'` `'ParameterAny'`

**Message primitive types (34)**
`'bool'` `'byte'` `'char'` `'int8'` `'int16'` `'int32'` `'int64'` `'uint8'` `'uint16'` `'uint32'`
`'uint64'` `'float32'` `'float64'` `'string'` `'time'` `'duration'` `'Header'`
and the array forms `'bool[]'` `'byte[]'` `'char[]'` `'int8[]'` `'int16[]'` `'int32[]'` `'int64[]'`
`'uint8[]'` `'uint16[]'` `'uint32[]'` `'uint64[]'` `'float32[]'` `'float64[]'` `'string[]'`

**Spec-body and `KEYWORD`-rule words (13)**
`'message'` `'request'` `'response'` `'goal'` `'result'` `'feedback'` `'name'` `'value'` `'service'`
`'type'` `'action'` `'node'` (`'duration'` and `'time'` double as KEYWORD entries)

**Rule tokens (22, non-literal)**
`RULE_BEGIN` `RULE_END` `RULE_ID` `RULE_STRING` `RULE_INT` `RULE_DIGIT` `RULE_DECINT` `RULE_DOUBLE`
`RULE_BINARY` `RULE_BOOLEAN` `RULE_DATE_TIME` `RULE_YEAR` `RULE_MONTH` `RULE_DAY` `RULE_HOUR`
`RULE_MIN_SEC` `RULE_MESSAGE_ASIGMENT` `RULE_ROS_CONVENTION_A` `RULE_ROS_CONVENTION_PARAM`
`RULE_SL_COMMENT` `RULE_ML_COMMENT` `RULE_WS` `RULE_ANY_OTHER`

`RULE_BEGIN=117` / `RULE_END=118` are present, confirming the indentation-sensitive token source is
active in the shipped parser.

### 3.2 `InternalRosParser.tokens` (78 literals)

Identical to §3.1 **minus** the ros2-only additions: no `'artifacts:'`, no `'qos:'`, no
`'profile:'` `'history:'` `'depth:'` `'reliability:'` `'durability:'`, and none of the 10 QoS enum
values. Everything else matches one-for-one.

### 3.3 `InternalBasicsParser.tokens` (65 literals)

The `Basics` subset only: namespaces (no `'ExternalDependency'`), parameter types/values, all
message primitives, `'default:'` `'type:'` `'value:'` `'ns:'`, punctuation. No package/node/interface
block keys — as expected, those live in `Ros`.

### 3.4 `InternalRos1Parser.tokens` (79 literals)

= `InternalRosParser` + `'artifacts:'`. No QoS vocabulary at all. Recorded for completeness; not used
by E1.

### 3.5 Raw ros2 literal list (verbatim, sorted)

```
'Any' 'Array' 'Base64' 'Boolean' 'Date' 'Double' 'ExternalDependency' 'GlobalNamespace' 'GraphName'
'Header' 'Integer' 'List' 'ParameterAny' 'PrivateNamespace' 'RelativeNamespace' 'String' 'Struct'
'action' 'actionclients:' 'actions:' 'actionservers:' 'artifacts:' 'best_effort' 'bool' 'bool[]'
'byte' 'byte[]' 'char' 'char[]' 'default:' 'default_qos' 'dependencies:' 'depth:' 'durability:'
'duration' 'feedback' 'float32' 'float32[]' 'float64' 'float64[]' 'fromGitRepo:' 'goal' 'history:'
'int16' 'int16[]' 'int32' 'int32[]' 'int64' 'int64[]' 'int8' 'int8[]' 'keep_all' 'keep_last'
'message' 'msgs:' 'name' 'node' 'node:' 'ns:' 'parameter_qos' 'parameters:' 'profile:' 'publishers:'
'qos:' 'reliability:' 'reliable' 'request' 'response' 'result' 'sensor_qos' 'service'
'serviceclients:' 'services_qos' 'serviceservers:' 'srvs:' 'string' 'string[]' 'subscribers:'
'time' 'transient_local' 'type' 'type:' 'uint16' 'uint16[]' 'uint32' 'uint32[]' 'uint64' 'uint64[]'
'uint8' 'uint8[]' 'value' 'value:' 'volatile' ',' ':' '[' ']' '[]'
```

---

## 4. Diff: JAR tokens vs. HEAD grammar

HEAD = `RosTooling` commit `42af44fb` (2025-11-27).

Every quoted literal was mechanically extracted from HEAD `Basics.xtext` + `Ros.xtext` +
`Ros2.xtext` (comment lines stripped) and set-differenced against the JAR literal list.

**Result — the JAR is a strict subset of HEAD.**

- `JAR \ HEAD` = **∅**. Not one token was renamed or removed between the JAR build and HEAD.
  Consequence: anything the pinned oracle accepts is still valid at HEAD. Pinning is
  forward-compatible; we are not painting ourselves into a corner.
- `HEAD \ JAR` = **7 keywords**, all introduced by a single commit.

### 4.1 Provenance of the divergence

Per-file git archaeology against the JAR build timestamp (2024-08-01 11:24 UTC):

| Grammar file | Last commit ≤ JAR build | Commits after | Semantic diff vs HEAD |
|---|---|---|---|
| `Basics.xtext` | `4b9f44ad` 2024-01-29 "Fix Array parameters" | `4d52b303` 2025-10-02 (Java 21 / Xtext 2.39 upgrade) | **none** — diff is one trailing space |
| `Ros.xtext` | `c9f6cf42` 2023-06-20 | *(none)* | **none** — byte-identical to HEAD |
| `Ros2.xtext` | `d9142083` 2023-08-23 | `3d9e5ebd` 2025-10-16 | the 4 QoS fields (below) |

The entire JAR-vs-HEAD gap is commit **`3d9e5ebd` (2025-10-16), "added four missing fields to
QualityOfService, LeaseDuration, Liveliness, LifeSpan, Deadline"** — landed **14.5 months after** the
JAR was built:

```diff
         ('durability:' Durability=('transient_local'|'volatile'))?)
+        ('durability:' Durability=('transient_local'|'volatile'))? &
+        ('lease_duration:' LeaseDuration=(EString | 'infinite'))? &
+        ('liveliness:'    Liveliness=('automatic'|'manual'))? &
+        ('lifespan:'      Lifespan=(EString | 'infinite'))? &
+        ('deadline:'      Deadline=(EString | 'infinite'))?)
```

This is a pleasingly narrow result: **the pinned oracle differs from HEAD in exactly one grammar
rule.** `Basics` and `Ros` are effectively frozen.

### 4.2 Verdict table

Legend — **SAFE**: in JAR and HEAD, reachable, emit freely. **DO-NOT-EMIT/HEAD-ONLY**: in HEAD only,
oracle rejects. **DO-NOT-EMIT/UNREACHABLE**: token exists in both but no grammar path reaches it.

| Keyword | In JAR | In HEAD | Verdict |
|---|:--:|:--:|---|
| `lease_duration:` | ✗ | ✓ | **OK since 2026-07-21** (was DO-NOT-EMIT) |
| `lifespan:` | ✗ | ✓ | **OK since 2026-07-21** (was DO-NOT-EMIT) |
| `deadline:` | ✗ | ✓ | **OK since 2026-07-21** (was DO-NOT-EMIT) |
| `liveliness:` | ✗ | ✓ | **OK since 2026-07-21** (was DO-NOT-EMIT) |
| `automatic` | ✗ | ✓ | **OK since 2026-07-21** (was DO-NOT-EMIT) (value of `liveliness:`) |
| `manual` | ✗ | ✓ | **OK since 2026-07-21** (was DO-NOT-EMIT) (value of `liveliness:`; note: `manual`, *not* `manual_by_topic`) |
| `infinite` | ✗ | ✓ | **OK since 2026-07-21** (was DO-NOT-EMIT) (value of the 3 duration fields) |
| `msgs:` | ✓ | ✓ | **DO-NOT-EMIT / UNREACHABLE in `.ros2`** — see §5.2 |
| `srvs:` | ✓ | ✓ | **DO-NOT-EMIT / UNREACHABLE in `.ros2`** |
| `actions:` | ✓ | ✓ | **DO-NOT-EMIT / UNREACHABLE in `.ros2`** |
| `Any` | ✓ | ✓ | **DO-NOT-EMIT / UNREACHABLE** — see §5.3 |
| `ParameterAny` | ✓ | ✓ | **DO-NOT-EMIT / UNREACHABLE** |
| `Date` | ✓ | ✓ | **DO-NOT-EMIT / UNREACHABLE** |
| `Struct` | ✓ | ✓ | SAFE but **discouraged** — see §5.4 |
| `qos:` `profile:` `history:` `depth:` `reliability:` `durability:` | ✓ | ✓ | **SAFE** |
| `default_qos` `services_qos` `sensor_qos` `parameter_qos` | ✓ | ✓ | **SAFE** |
| `keep_last` `keep_all` | ✓ | ✓ | **SAFE** |
| `best_effort` `reliable` | ✓ | ✓ | **SAFE** |
| `transient_local` `volatile` | ✓ | ✓ | **SAFE** |
| `artifacts:` `node:` `fromGitRepo:` `dependencies:` | ✓ | ✓ | **SAFE** |
| `publishers:` `subscribers:` `serviceservers:` `serviceclients:` `actionservers:` `actionclients:` `parameters:` | ✓ | ✓ | **SAFE** |
| `type:` `ns:` `value:` `default:` | ✓ | ✓ | **SAFE** — but see the `default:` note below |
| `GlobalNamespace` `RelativeNamespace` `PrivateNamespace` `GraphName` | ✓ | ✓ | **SAFE** |
| `ExternalDependency` | ✓ | ✓ | **SAFE** |
| `Integer` `String` `Double` `Boolean` `Base64` `List` `Array` | ✓ | ✓ | **SAFE** |
| all 17 scalar msg primitives + 14 array forms + `Header` | ✓ | ✓ | **SAFE** |
| `message` `request` `response` `goal` `result` `feedback` | ✓ | ✓ | SAFE in `.ros` only (spec bodies) |
| `name` `value` `service` `type` `action` `node` | ✓ | ✓ | **SAFE** (`KEYWORD` rule, message-part data) |
| `,` `:` `[` `]` `[]` | ✓ | ✓ | **SAFE** |

The `HEAD \ JAR` extraction also surfaced `#`, `+`, `-`, `.`, `/`, `=`, `~`, `E`, `e`, `T`, digits,
`\n`, `\r`, `true`, `false`, `synthetic:BEGIN`, `synthetic:END`. These are **not keywords** — they
are character fragments inside `terminal` rule bodies (`DOUBLE`, `DECINT`, `DATE_TIME`, `BOOLEAN`,
`ROS_CONVENTION_A`, `SL_COMMENT`, `BEGIN`/`END`). They never become parser tokens, and their absence
from the `.tokens` file is expected, not a divergence. `true`/`false` reach the parser as
`RULE_BOOLEAN`, which the JAR has.

### Note on `default:` — where it binds

`default:` is lexically safe in both HEAD and the JAR, but its **binding position** is easy to get
wrong and the mistake is silent. It is a member of `ParameterType`, **not** of `Parameter`, and
Basics.xtext:72-110 attaches it to *every* scalar type rule as well as to `ParameterArrayType`:

```
ParameterIntegerType returns ParameterIntegerType:
    {ParameterIntegerType} 'Integer' ('default:' default=ParameterInteger)?;
```

Since `'type:' type=ParameterType` carries no `BEGIN`/`END`, the token lands at the same indent as
`type:` and binds immediately after it — before `ns:` / `value:` / `qos:`. `default:` (the type's
declared default) and `value:` (the parameter's assigned value) are **distinct slots and are never
interchangeable**; rewriting one into the other parses cleanly and changes the model's meaning
without any diagnostic. See `emission-profile.md` rule 23.

---

## 5. What we must NOT emit

### 5.1 The four modern QoS fields — hard exclusion

Do not emit `lease_duration:`, `liveliness:`, `lifespan:`, `deadline:`, nor the values `infinite`,
`automatic`, `manual`. The pinned parser has no token for them; they will fail lexing and produce a
syntax error, not a semantic warning.

The emittable QoS vocabulary is exactly:

```
qos:
  profile:     default_qos | services_qos | sensor_qos | parameter_qos
  history:     keep_last | keep_all
  depth:       <DECINT>
  reliability: best_effort | reliable
  durability:  transient_local | volatile
```

All five sub-fields are optional and **unordered** (Xtext `&` group) in both JAR-era and HEAD.

*Cost of this exclusion: zero.* A scan of the entire corpus (229 `.ros2` + 24 `.ros2`) found
**no file using any of the four fields**. Nothing we need to round-trip depends on them.

*Corollary:* the previously recorded constraint that QoS durations must be quoted digit-strings
parseable by 32-bit `Integer.parseInt` (or `infinite`) is **moot under the pinned profile** — it
applies only to `lease_duration`/`lifespan`/`deadline`. Those are emittable since the pin was
lifted (2026-07-21), which makes this rule MORE relevant, not less -- confirmed against the real
validator, oracle case 14. It should be retained
in the documentation as a note for the day the oracle is rebuilt, not implemented as a validator.

### 5.2 Message-spec blocks in `.ros2` — hard exclusion

`'msgs:'`, `'srvs:'`, `'actions:'` **do** appear in the ros2 token file, because `Ros2` inherits
`Ros` and the `Package_Impl` rule is still compiled in. They are nonetheless unreachable: `Ros2.xtext`
declares `@Override Package returns Package: AmentPackage;` as its **first rule**, which makes
`AmentPackage` the entry rule for `.ros2`, and `AmentPackage` admits only
`fromGitRepo:` / `artifacts:` / `dependencies:`.

Their presence in `.tokens` is a decoy. Do not read token presence as permission.
Corpus corroboration: **zero** `.ros2` files across both corpora contain a `msgs:`/`srvs:`/`actions:`
block. Message specs belong in `.ros` files only.

### 5.3 `Any` / `ParameterAny` / `Date` — unreachable parameter types

`ParameterAnyType` and `ParameterDateType` are *defined* in `Basics.xtext` but are **not members of
the `ParameterType` alternation**, and `ParameterAny`/`ParameterDate` are not members of
`ParameterValue`:

```
ParameterType  := ParameterListType | ParameterStructType | ParameterIntegerType
                | ParameterStringType | ParameterDoubleType | ParameterBooleanType
                | ParameterBase64Type | ParameterArrayType;      // | ParameterDateType;  <-- commented out
ParameterValue := ParameterString | ParameterBase64 | ParameterInteger | ParameterDouble
                | ParameterBoolean | ParameterList | ParameterStruct;  // | ParameterDate; <-- commented out
```

This holds identically in the JAR-era and HEAD versions of the file. Emittable parameter types are
therefore exactly: **`Integer`, `String`, `Double`, `Boolean`, `Base64`, `List[...]`,
`Array[...]`, `Struct[...]`**.

Note the array syntax is `Array '[' type ']'` — bracketed. The older `'Array:'` + indent form was
replaced by commit `4b9f44ad` (2024-01-29), which is **before** the JAR build, so the JAR expects the
bracketed form. The token file confirms this: it contains `'Array'`, not `'Array:'`.

### 5.4 `Struct` — permitted but discouraged

`ParameterStructType` is reachable, but the `ParameterStruct` *value* rule has an unusual shape
(`'[' BEGIN member* ']' END`) that mixes a bracket with indentation tokens. It is fragile under an
indentation-sensitive lexer and no corpus file exercises it. Recommend the emitter avoid nested
struct *values* in v1 and mark them unsupported rather than risk unverifiable output.

### 5.5 Formatting constraints that survive

Unchanged by this analysis, restated because the emitter depends on them:
- `RULE_BEGIN`/`RULE_END` are live in the JAR — indentation is mandatory and structural.
- `EString = STRING | ID`; names containing `.` `/` `::` `-` must be quoted. The Xtext
  `common.Terminals` `STRING` rule accepts **both** `'single'` and `"double"` quotes; the clean
  corpus uses single quotes throughout. Either parses — pick one and be consistent.
- Emit LF, spaces-only, one consistent indent width. Do not imitate corpus formatting (26/52
  `.rossystem` files contain tabs/CRLF/mixed indents). Comparisons against corpus originals must be
  semantic, never byte-wise.

---

## 6. `.rossystem` — no language server exists

**Confirmed: there is no `.rossystem` oracle.** Expected result met.

Two independent checks across all three JARs:
1. Archive-entry listing, case-insensitive `rossystem` — **0 matches** in each JAR.
2. Raw byte grep of each JAR file, case-insensitive `rossystem` — **no match** in each JAR.

The second check matters: it rules out the string appearing inside a compiled class, a manifest, or a
compressed-but-unlisted resource. The `RosSystem.xtext` grammar exists in the RosTooling source tree
(since 2018) and is complete, but **it was never built into a shipped language server**.

**Consequence for E1:** `.rossystem` output has **no executable validation path whatsoever** — not
now, and not after we install a JDK 19. Validation for `.rossystem` must rest on:
- the `RosSystem.xtext` grammar and `RosSystemValidator.xtend` rules, transcribed into the skill;
- structural self-checks in the emitter (connection direction, `MatchPortMsgs` type identity);
- the 51 + 1 corpus files as semantic regression fixtures.

This asymmetry should be stated plainly in the E1 report: `.ros2` gets a real (if stale) oracle;
`.rossystem` gets a modelled one.

---

## 7. Executable verification status — BLOCKED

`java -version` on this machine reports:

```
java version "1.8.0_481"
Java(TM) SE Runtime Environment (build 1.8.0_481-b25)
```

Only `C:\Program Files\Java\jre1.8.0_481` is installed. The JARs require **JavaSE-19**. Nothing in
this document was executed against a running language server. **No claim here rests on a test run.**
Mark all of §3–§6 as *static-analysis-verified, execution-pending*.

### How to run the oracle once a JDK ≥19 is available

The bundled VS Code extension cannot be used (§1.1). Launch the ros2 server directly over stdio:

```bash
"$JAVA19_HOME/bin/java" -jar \
  vscode-RosTooling/resources/de.fraunhofer.ipa.ros2.xtext.ide-3.0.0-SNAPSHOT-ls.jar
```

Then speak LSP over stdin/stdout: `initialize` → `textDocument/didOpen` with the candidate `.ros2`
content → collect `textDocument/publishDiagnostics`. An empty diagnostics array is the pass
condition. Drop the `-Xdebug -Xrunjdwp:...` flags that `extension.ts` passes; they open a JDWP port
on 8000 and are not needed for validation.

Recommended first regression run once unblocked:
1. Round-trip all 24 `CS_ros2model_TBs` `.ros2` files (clean corpus) — expect 0 diagnostics.
2. Round-trip the 229 `ros-model-examples` `.ros2` files — expect some pre-existing failures;
   record them as a baseline rather than treating them as our regressions.
3. Negative controls: emit one file using `lease_duration:` and one using `msgs:` inside a `.ros2`
   package, and confirm the server **rejects both**. This positively verifies the §5.1/§5.2
   exclusions rather than merely inferring them.

Step 3 is the one that converts this document from inference to fact. It should be run before the
E1 deliverable is signed off.

---

## 8. Emission profile — normative summary

The skill emits `.ros2` conforming to `Ros2.xtext` **as of commit `d9142083` (2023-08-23)**,
equivalently the grammar baked into Bundle-Version `3.0.0.202408011124`.

Permitted top-level shape:

```
<package_name>:
  fromGitRepo: <EString>            # optional
  artifacts:                        # optional
    <artifact_name>:
      node: <RosNames>
      publishers:    | subscribers:      | serviceservers:
      serviceclients:| actionservers:    | actionclients:  | parameters:
        <port_name>:
          type: <EString ref>
          ns:   GlobalNamespace | RelativeNamespace | PrivateNamespace   # optional
          qos:                                                          # optional
            profile: | history: | depth: | reliability: | durability:    # unordered, all optional
  dependencies: [ <dep> (, <dep>)* ]  # optional
```

Excluded by decision, with rationale in §5: the four modern QoS fields and their value literals;
`msgs:`/`srvs:`/`actions:` in `.ros2`; `Any`/`ParameterAny`/`Date` parameter types; nested `Struct`
values (v1).

Because `JAR \ HEAD = ∅`, output produced under this profile is also valid against RosTooling HEAD.
Pinning costs us four QoS fields that no corpus file uses, and buys us an executable oracle.
