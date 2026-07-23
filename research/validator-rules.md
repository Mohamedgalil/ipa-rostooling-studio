# RosTooling validator rules — complete constraint enumeration

Sources read in full (read-only reference clones):

- `C:\Users\mae\Downloads\adm-mae\CoreSense\material\code\RosTooling\plugins\de.fraunhofer.ipa.ros.xtext\src\de\fraunhofer\ipa\ros\validation\RosValidator.xtend` (166 lines, Xtext 2.25.0)
- `C:\Users\mae\Downloads\adm-mae\CoreSense\material\code\RosTooling\plugins\de.fraunhofer.ipa.rossystem.xtext\src\de\fraunhofer\ipa\rossystem\validation\RosSystemValidator.xtend` (381 lines, Xtext 2.30.0)

Supporting files read to resolve semantics (metamodel / grammar / shipped binaries):

- `...\de.fraunhofer.ipa.ros.xtext\src\de\fraunhofer\ipa\ros\validation\BasicsValidator.xtend`
- `...\de.fraunhofer.ipa.ros2.xtext\src\de\fraunhofer\ipa\ros2\validation\Ros2Validator.xtend`
- `...\de.fraunhofer.ipa.ros2.xtext\src\de\fraunhofer\ipa\ros2\Ros2.xtext`
- `...\de.fraunhofer.ipa.rossystem.xtext\src\de\fraunhofer\ipa\rossystem\RosSystem.xtext`
- `...\de.fraunhofer.ipa.ros\model\ros.ecore`
- `...\de.fraunhofer.ipa.rossystem\src\system\impl\SystemImpl.java`
- `...\vscode-RosTooling\resources\de.fraunhofer.ipa.{ros,ros1,ros2}.xtext.ide-3.0.0-SNAPSHOT-ls.jar`

---

## 0. Findings that change the project's assumptions — read first

### 0.1 `Ros2Validator` and `BasicsValidator` are EMPTY

Both classes contain nothing but a commented-out example. Verbatim, the entire body of
`Ros2Validator.xtend`:

```xtend
class Ros2Validator extends AbstractRos2Validator {

//  public static val INVALID_NAME = 'invalidName'
//
//  @Check
//  def checkGreetingStartsWithCapital(Greeting greeting) {
//      if (!Character.isUpperCase(greeting.name.charAt(0))) {
//          warning('Name should start with a capital',
//                  Ros2Package.Literals.GREETING__NAME,
//                  INVALID_NAME)
//      }
//  }

}
```

`BasicsValidator.xtend` is identical modulo the package name. Confirmed in the shipped jars:
`Ros2Validator.class` is 371 bytes and `BasicsValidator.class` is 376 bytes — i.e. a bare
constructor, no methods.

**Consequence:** 100% of semantic validation applied to a `.ros2` file comes from
`RosValidator`. There is no ROS2-specific validator to satisfy. Confidence: **certain**.

### 0.2 There is NO shipped language server for `.rossystem`

`vscode-RosTooling/resources/` contains exactly three jars:

```
de.fraunhofer.ipa.ros.xtext.ide-3.0.0-SNAPSHOT-ls.jar
de.fraunhofer.ipa.ros1.xtext.ide-3.0.0-SNAPSHOT-ls.jar
de.fraunhofer.ipa.ros2.xtext.ide-3.0.0-SNAPSHOT-ls.jar
```

There is no `de.fraunhofer.ipa.rossystem.xtext.ide-*-ls.jar`. **The entire `RosSystemValidator`
is unreachable from the shipped oracle.** Every `.rossystem` rule in this document is
source-derived only and can never be confirmed against the prebuilt tooling, even once a JDK 19+
is installed. Confidence: **certain** (directory listing is exhaustive).

### 0.3 The oracle staleness is worse than recorded — `CheckQoS` is absent from the jar

Established fact 7 said the JAR predates the QoS duration grammar. Verified at the bytecode level.
The shipped `RosValidator.class` (extracted from the ros2 LS jar, `major=55` → Java 11, dated
2024-08-01) has exactly these check-related identifiers in its constant pool:

```
INVALID_NAME / invalidName
PARAMETER_HELP / paramInfo
INVALID_SPEC / invalidSpecRef
checkNameConventionsNode
checkNameConventionsArtifact
checkNameConventionsPackage
checkNameConventionsParameters
CheckMsgsRefPublisher
CheckMsgsRefSubscriber
CheckMsgsRefActionClient
CheckMsgsRefActionServer
CheckMsgsRefServiceServer
CheckMsgsRefServiceClient
BinaryHelp / ListHelp / StructHelp
```

`CheckQoS`, `CheckDuration`, `INVALID_VALUE` and `invalidValue` are **not present**. So the jar has
13 `@Check` methods; HEAD has 14. The QoS duration rule (R14 below) is a HEAD-only rule that the
pinned oracle will neither enforce nor reward. Emit conformant durations anyway — the rule is real
in the source of record — but do not expect the jar to catch violations. Confidence: **certain**.

### 0.4 `AmentPackage` is a subtype of `Package`

`ros.ecore` line 213: `<eClassifiers xsi:type="ecore:EClass" name="AmentPackage" eSuperTypes="#//Package"/>`

Therefore `checkNameConventionsPackage` — the only ERROR-severity naming rule — **does** fire on the
root element of every `.ros2` file. This is the single hardest naming constraint in the toolchain.

---

## 1. `RosValidator` — applies to `.ros` / `.ros1` / `.ros2`

Severity mapping: `error(...)` → ERROR, `warning(...)` → WARNING, `info(...)` → INFO.

| # | Method | Severity | Enforces | Verbatim condition | Static-checkable? |
|---|---|---|---|---|---|
| R1 | `checkNameConventionsNode` | **WARNING** | No uppercase letter anywhere in a `Node` name | `for (char c : node.name.toCharArray){ if (Character.isUpperCase(c)){` | **YES** |
| R2 | `checkNameConventionsArtifact` | **WARNING** | No uppercase letter anywhere in an `Artifact` name | `for (char c : artifact.name.toCharArray){ if (Character.isUpperCase(c)){` | **YES** |
| R3 | `checkNameConventionsPackage` | **ERROR** | No uppercase letter anywhere in a `Package` (incl. `AmentPackage`) name | `for (char c : rospackage.name.toCharArray){ if (Character.isUpperCase(c)){` | **YES** |
| R4 | `checkNameConventionsParameters` | **WARNING** | Uppercase in a `Parameter` name allowed only if a `.` occurs at or after that character | see §1.2 | **YES** |
| R5 | `CheckMsgsRefPublisher` | **WARNING** | `pub.message` must resolve to a contained `TopicSpec` | `if(pub.message.eContainer === null){` | **NO** |
| R6 | `CheckMsgsRefSubscriber` | **WARNING** | `sub.message` must resolve | `if(sub.message.eContainer === null){` | **NO** |
| R7 | `CheckMsgsRefActionClient` | **WARNING** | `act.action` must resolve | `if(act.action.eContainer === null){` | **NO** |
| R8 | `CheckMsgsRefActionServer` | **WARNING** | `act.action` must resolve | `if(act.action.eContainer === null){` | **NO** |
| R9 | `CheckMsgsRefServiceServer` | **WARNING** | `ser.service` must resolve | `if(ser.service.eContainer === null){` | **NO** |
| R10 | `CheckMsgsRefServiceClient` | **WARNING** | `ser.service` must resolve | `if(ser.service.eContainer === null){` | **NO** |
| R11 | `BinaryHelp` | INFO | Hint for Base64 params | `if(param.type.toString.contains("Base64") && !(param.toString.contains('0b') \|\|param.toString.contains('0B'))){` | PARTIAL |
| R12 | `ListHelp` | INFO | Hint for List params | `if(param.type.toString.contains("List")){` | **YES** |
| R13 | `StructHelp` | INFO | Hint for Struct params | `if(param.type.toString.contains("Struct")){` | **YES** |
| R14 | `CheckQoS` → `CheckDuration` | **ERROR** | `lease_duration` / `lifespan` / `deadline` must be `infinite` or `Integer.parseInt`-able | see §1.3 | **YES** |

### 1.1 The ERROR / WARNING asymmetry (R1–R4)

Four structurally identical loops, three different consequences. Verbatim:

```xtend
  /* CAPITAL LETTERS */
  @Check
  def void checkNameConventionsNode (Node node) {
      for (char c : node.name.toCharArray){
          if (Character.isUpperCase(c)){
              warning("The name of a node should follow the ROS naming conventions: Capital letters are not recommended", null, INVALID_NAME);
          }
      }}
  @Check
  def void checkNameConventionsArtifact (Artifact artifact) {
      for (char c : artifact.name.toCharArray){
          if (Character.isUpperCase(c)){
              warning("The name of a artifact should follow the ROS naming conventions: Capital letters are not recommended", null, INVALID_NAME);
          }
      }}
  @Check
  def void checkNameConventionsPackage (Package rospackage) {
      for (char c : rospackage.name.toCharArray){
          if (Character.isUpperCase(c)){
              error("The name of a package has to follow the ROS naming conventions: Capital letters are not allowed", null, INVALID_NAME);
          }
      }
  }
```

Note the wording tracks the severity precisely: node/artifact say *"should follow"* / *"are not
recommended"*; package says *"has to follow"* / *"are not allowed"*. Package is the only ERROR.

**Emission rule:** package names MUST be `[a-z0-9_]`-only. Node and artifact names SHOULD be. Since
one marker per uppercase character is emitted (the loop does not `return`), a name like `MyNode`
produces two warnings, not one.

### 1.2 `checkNameConventionsParameters` — the dot-suffix carve-out (R4)

```xtend
   @Check
  def void checkNameConventionsParameters (Parameter parameter) {
      for (i : 0 ..< parameter.name.length) {
          val c = parameter.name.charAt(i)
          if (Character.isUpperCase(c)) {
              val remaining = parameter.name.substring(i)
              if (!remaining.contains(".")) {
                warning("The name of a parameter has to follow the ROS naming conventions: Capital letters are not recommended", null, INVALID_NAME);
              }
          }
      }
  }
```

Semantics: an uppercase character at index `i` is forgiven iff `name.substring(i)` still contains a
`.`. Equivalently — **uppercase letters are tolerated in every dot-segment except the last one.**
`Foo.bar` is clean; `foo.Bar` warns; `Foo.Bar` warns once (for the `B`, not the `F`).

Note the message says *"has to follow"* but the call is `warning(...)`. The message wording is
inconsistent with the severity here; trust the call, not the prose.

### 1.3 `CheckQoS` / `CheckDuration` — the 32-bit nanosecond trap (R14)

```xtend
  public static val INVALID_VALUE = 'invalidValue'
  @Check
  def void CheckQoS (QualityOfService qos){
    CheckDuration(qos.leaseDuration)
    CheckDuration(qos.lifespan)
    CheckDuration(qos.deadline)
  }

  def void CheckDuration(String duration)
  {
    if(duration != 'infinite' && duration !== null){
        try{
            Integer.parseInt(duration)
        }
        catch (NumberFormatException e){
            error("Durations of lease_duration, lifespan, deadline should be specified as a string of nanoseconds which can convert to int, or as infinite", null, INVALID_VALUE)
        }
    }
  }
```

Machine-implementable constraints derived from `Integer.parseInt` semantics:

- Value must be `infinite`, or match `[+-]?[0-9]+`.
- **Range is 32-bit signed: −2147483648 … 2147483647.** The message says *"a string of
  nanoseconds"* — so the maximum expressible duration is **2147483647 ns ≈ 2.147 seconds**. Any
  human-plausible deadline such as `"5000000000"` (5 s) throws `NumberFormatException` and is an
  ERROR. This is the single most likely accidental violation.
- No decimal point, no underscores, no exponent, no whitespace (`parseInt` does not trim).
- Empty string `""` fails.
- Per grammar `Ros2.xtext:38,40,41`, the assignment is `LeaseDuration=(EString | 'infinite')`, and
  `EString = STRING | ID`. A bare digit sequence is neither a valid `ID` nor a `STRING`, so the
  value **must be double-quoted**: `deadline: "1000000"`. `infinite` is an unquoted keyword.
- `duration != 'infinite'` is Xtend's null-safe equality (compiles to an `Objects.equal`-style
  comparison), so the null check being second is harmless. **No NPE here.**

**Emission profile note:** per §0.3 this rule does not exist in the pinned jar, and per established
fact 7 the four keys `lease_duration` / `liveliness` / `lifespan` / `deadline` are not in the jar's
token set at all. They must be excluded from emitted output regardless of this rule.

### 1.4 Cross-file rules R5–R10

All six are the same shape — `X.<ref>.eContainer === null` — and all six are **WARNING**. Xtext
returns an unresolved cross-reference as a proxy whose `eContainer()` is `null`, so this is a
"reference did not resolve" test in disguise. It cannot be evaluated without a linking environment
(the `.ros` file declaring the msg/srv/action spec plus the `dependency` list). A static
single-file linter can only do a name-shape sanity check; mark as **NO**.

The shared warning text is worth quoting because it names the two remedies a generator must
satisfy:

```xtend
   public static String SpecWarning = "## Quick Fixes available ##-
    - Add the dependency to the specifications project
    - Generate the .ros model for the specifications
      ->https://github.com/ipa320/ros-model/blob/master/docu/NewCommunicationObjects.md"
```

---

## 2. `RosSystemValidator` — applies to `.rossystem`

| # | Method | Severity | Enforces | Verbatim condition | Static-checkable? |
|---|---|---|---|---|---|
| S1 | `checkIfNodeInSystem` | **ERROR** (+INFO) | Every node referenced by a `Process` must be a component of the enclosing `System` | `if (!system.components.contains(node)){` | PARTIAL |
| S2 | `fromFileHelper` | INFO + **ERROR** | `fromFile` must contain `/` — but see §2.2, the method is broken | `if (!system.fromFile.toString.contains("/")){` | PARTIAL |
| S3 | `checkIfInterfaceInSystem` | **ERROR** (+INFO) | Both connection endpoints must be interfaces of nodes in the system | `if (!AllInterfaces.contains(from_connection)){` … `if (!AllInterfaces.toArray.contains(to_connection)){` | PARTIAL |
| S4 | `checkPortPatterns` | **ERROR** | Connection direction: `from` = server/publisher, `to` = client/subscriber | see §2.3 | **YES** |
| S5 | `MatchPortMsgs` | **ERROR** | Both endpoints must resolve to the **same type object** | `if (from_type !== to_type){` | **NO** |
| S6 | `CheckParameter` → `CheckParameterValue` | **ERROR** / INFO | Assigned value must structurally match the declared parameter type | see §2.6 | **NO** |
| S7 | `BinaryHelp` | INFO | Base64 hint | `if(param.type.toString.contains("Base64") && !(param.toString.contains('0b') \|\|param.toString.contains('0B'))){` | PARTIAL |
| S8 | `ArrayHelp` | INFO | Array hint | `if(param.type.toString.contains("Array")){` | **YES** |
| S9 | `ListHelp` | INFO | List hint | `if(param.type.toString.contains("List")){` | **YES** |
| S10 | `StructHelp` | INFO | Struct hint (note: `"Struc"`, not `"Struct"`) | `if(param.type.toString.contains("Struc")){` | **YES** |

S7–S10 take a `ros.Parameter`, which reaches a `.rossystem` file through the grammar's
system-level `('parameters:' BEGIN parameter+=Parameter* END)` block (`RosSystem.xtext:34-38`).

### 2.1 `checkIfNodeInSystem` (S1)

```xtend
  @Check
  def checkIfNodeInSystem(Process process) {
      for (Component node : process.components) {
          //var nodeImpl = node as RosNodeImpl
          var system = process.eContainer as System
          if (!system.components.contains(node)){
              error('The node '+node+' is not part of the system '+system.name
                  ,null,NOT_IN_THE_SYSTEM
              )
              info('Valid components for this process are '+system.components
                  ,null,NOT_IN_THE_SYSTEM)
          }
      }
  }
```

`Process.components` is `components+=[RosNode|EString]` (cross-reference), `System.components` is
`components+=RosNode*` (containment). The test is EMF list `contains`, i.e. **object identity**
after linking. Practically: every name listed under a process's `nodes: [...]` must be declared in
the same file's `nodes:` block. Within one file this is name-resolvable, hence PARTIAL — a linter
can compare the `nodes: [a, b]` identifiers against declared node names and be right in the common
case.

`process.eContainer as System` is an unconditional cast, but the grammar only ever nests `Process`
directly under `RosSystem`, so it is safe in practice.

### 2.2 `fromFileHelper` (S2) — **CONFIRMED LIVE BUG**

Verbatim, the whole method:

```xtend
  @Check
  def fromFileHelper(System system ) {
      if (!system.fromFile.empty){
              info('The format for the FromFile attribute is: "NameOfThePackage/Path/to/ExecutableLaunchFile.launch.py"'
                  ,null,NOT_IN_THE_SYSTEM)
      }
      if (!system.fromFile.toString.contains("/")){
              error('Path not valid, the format for the FromFile attribute is: "NameOfThePackage/Path/to/ExecutableLaunchFile.launch.py"'
                  ,null,NOT_IN_THE_SYSTEM)
      }
  }
```

**Finding: the `/` check is NOT guarded against an absent `fromFile`. Neither is the line above it.**

Chain of evidence:

1. `fromFile` is grammatically optional — `RosSystem.xtext:16`: `('fromFile:' fromFile=EString)?`
2. When omitted, the value is `null`, not `""`. `SystemImpl.java:70`:
   `protected static final String FROM_FILE_EDEFAULT = null;` and `:80`
   `protected String fromFile = FROM_FILE_EDEFAULT;`
3. Xtend's property shorthand `system.fromFile.empty` desugars to `getFromFile().isEmpty()`, an
   instance call on `java.lang.String`. Xtend performs null-safe navigation **only** for the `?.`
   operator, which is not used here. (Xtend's null-tolerant helper is `isNullOrEmpty`, a different
   name, not bound by `.empty`.)

So for a model that omits `fromFile`, **line 76 throws `NullPointerException` before line 80 is
ever reached.** The failure mode is therefore *not* a spurious "Path not valid" ERROR — it is an
exception escaping the `@Check`, which Xtext surfaces as an "Error executing EValidator"-class
diagnostic rather than a normal marker. Both remaining branches of the method are dead in that case.

Confidence:

- `fromFile` optional, default `null`: **certain** (read from grammar and generated `SystemImpl`).
- `.empty` compiles to a non-null-safe `isEmpty()`: **high (~90%)**. This is standard Xtend property
  desugaring, but I could not compile it to confirm — see §4.
- Net conclusion that `fromFileHelper` misbehaves on the 32/52 corpus models omitting `fromFile`:
  **high**. The *form* of the misbehaviour (NPE at line 76 vs. ERROR at line 80) rests on the ~90%
  item; the *existence* of a defect does not, since neither line has a guard.

Not directly observable in this environment either way: per §0.2 there is no `.rossystem` language
server shipped, so no runtime confirmation is possible even after installing a JDK 19+.

Two further defects in the same six lines:

- **Inverted intent.** The `info` fires when `fromFile` is *non-empty*. A "helper" hint explaining
  the expected format is useful when the value is missing or wrong; here it nags on every model that
  got it right.
- **Spurious error on empty string.** If a model writes `fromFile: ""`, no NPE occurs, the `info`
  is skipped, and `"".contains("/")` is `false` → unconditional ERROR.

**Routing decision:** always emit `fromFile` when emitting `.rossystem`, and always with at least
one `/`, quoted (it contains `/` and `.`, so `EString` requires quotes):
`fromFile: "my_pkg/launch/bringup.launch.py"`. This is the only input that traverses the method
without an NPE and without an error. Never emit `fromFile: ""`. Omitting it is *corpus-normal* but
trips the bug.

### 2.3 `checkPortPatterns` (S4) — connection direction

```xtend
  @Check
  def checkPortPatterns(Connection connection) {
      var List<String> validFromType = newArrayList('RosPublisherReference','RosServiceServerReference','RosActionServerReference')
      var List<String> validToType = newArrayList('RosSubscriberReference','RosServiceClientReference','RosActionClientReference')
      var connection_def = connection as RosSystemConnectionImpl
      var from_connection = connection_def.from
      var to_connection = connection_def.to
      if(!validFromType.contains(from_connection.reference.eClass.name)){
              error('The type of the interface '+from_connection+' is not valid, the output port can have only one of the following types '+validFromType
                  ,null,NOT_VALID_PATTERN)
      } else {
          if (from_connection.reference.eClass.name=='RosPublisherReference'){
              if(!(to_connection.reference.eClass.name=='RosSubscriberReference')){
                error('The input port (to) must be a Subscriber'
                  ,null,NOT_VALID_PATTERN)
          }}
          if (from_connection.reference.eClass.name=='RosServiceServerReference'){
              if(!(to_connection.reference.eClass.name=='RosServiceClientReference')){
                  error('The input port (to) must be a Service Client'
                      ,null,NOT_VALID_PATTERN)
          }}
          if (from_connection.reference.eClass.name=='RosActionServerReference'){
              if(!(to_connection.reference.eClass.name=='RosActionClientReference')){
                  error('The input port (to) must be an Action Client'
                      ,null,NOT_VALID_PATTERN)
          }}
      }
  }
```

Exactly three legal pairings, keyed to the grammar's arrow prefixes (`RosSystem.xtext:90-112`):

| `from` (server side) | prefix | `to` (client side) | prefix |
|---|---|---|---|
| `RosPublisherReference` | `pub->` | `RosSubscriberReference` | `sub->` |
| `RosServiceServerReference` | `ss->` | `RosServiceClientReference` | `sc->` |
| `RosActionServerReference` | `as->` | `RosActionClientReference` | `ac->` |

This is **statically checkable within one file**: a connection is written
`- [from_name , to_name]` where both names are local `RosInterface` labels declared as
`- name: pub->...` etc. in the same file. A linter resolves each label to its arrow prefix and
applies the table. No cross-file resolution needed. Note `validToType` is declared but only ever
used inside an error *message* — the actual `to` checking is done by the three literal comparisons.

Grammar quirk worth knowing: the rule named `RosServerClientReference` (`RosSystem.xtext:102`)
`returns RosServiceClientReference`. The rule name and the eClass name differ; `eClass.name` yields
`RosServiceClientReference`, so the validator is correct.

### 2.4 `checkIfInterfaceInSystem` (S3)

```xtend
      for (Component component : system.components){
          if(component.class.toString.contains("RosNode")){
              var rosnode = component as RosNode
              for(RosInterface interface : rosnode.rosinterfaces){
                AllInterfaces.add(interface)
              }
          }
          if (component.class.toString.contains("SubSystem")) {
              var subsystem = component as SubSystem
              for(subcomponent: (subsystem.system as System).components){
                 var rosnode = subcomponent as RosNode
                  for(RosInterface interface : rosnode.rosinterfaces){
                    AllInterfaces.add(interface)
                  }
              }
          }
      }
```

then

```xtend
      if (!AllInterfaces.contains(from_connection)){
              info('Valid interfaces for this process are '+AllInterfaces
                  ,null,NOT_IN_THE_SYSTEM)
              error('The interface '+from_connection+' is not part of the system '+system.name
                  ,null,NOT_IN_THE_SYSTEM)
      } else {
          if (!AllInterfaces.toArray.contains(to_connection)){
                  info('Valid interfaces for this process are '+AllInterfaces
                      ,null,NOT_IN_THE_SYSTEM)
                  error('The interface '+to_connection+' is not part of the system '+system.name
                      ,null,NOT_IN_THE_SYSTEM)
      }
    }
  }
```

Constraint: both endpoints of every connection must be a `RosInterface` owned by a node that is a
direct component of this system, or by a node one level inside a referenced subsystem.

Defects — see §3 for the consolidated list. The `to` check sits in the `else`, so a connection with
a bad `from` never gets its `to` validated; expect to fix errors one at a time.

### 2.5 `MatchPortMsgs` (S5) — identity, not name equality

```xtend
      if (from_connection.reference.eClass.name=='RosPublisherReference'){
          var from_top = from_connection.reference as RosPublisherReference
          from_type = from_top.from.message
      }
      ...
      if (to_connection.reference.eClass.name=='RosActionClientReference'){
          var to_top = to_connection.reference as RosActionClientReference
          to_type = to_top.from.action
      }

      if (from_type !== to_type){
          error("A connection can only be formed by interfaces with the same type, "+from_connection.name+" and "+to_connection.name+" have different types.", null, TYPE_NOT_MATCH)
      }
```

`!==` is Xtend **identity** comparison — reference inequality on the `EObject`, not `.equals`, not
name comparison. The two endpoints must resolve to the *same* `TopicSpec` / `ServiceSpec` /
`ActionSpec` instance. Within a single Xtext `ResourceSet` the same spec URI resolves to one shared
instance, so matching type names normally suffice — but this makes the rule inherently
**NOT statically checkable**: it needs full cross-file linking, and it will produce a false ERROR
whenever the two `.ros2` files pull the same logical spec through resources that load into distinct
instances.

Combined with S4, the emission rule is: connect `pub->`/`sub->` pairs whose `type:` strings are
byte-identical, and let the linker do the rest.

`from_type` and `to_type` are **instance fields**, not locals — see §3.

### 2.6 `CheckParameter` / `CheckParameterValue` (S6)

```xtend
    @Check
    def void CheckParameter (RosParameter rosparam){
        CheckParameterValue(rosparam.from, rosparam.value);
    }
```

`CheckParameterValue` (lines 213–325) is a ~110-line recursive structural type-checker over
parameter values. Constraints it attempts to enforce, by declared type:

- **List / Sequence** (`expected_type.contains("ParameterListType") || expected_type.contains("ParameterSequence")`):
  value must be a `ParameterSequence`, else `error("Expect a list of elements; format { , ,...}")`;
  element count must equal the declared count, else
  `error("Expect a list of "+expected_sub_types.length+" elements")`; each element's type must
  satisfy `check_matched_type`.
- **Array** (`expected_type.contains("ParameterArrayType")`): value must be a `ParameterSequence`;
  every element must match the single declared element type. Length is *not* checked.
- **Struct** (`expected_type.contains("ParameterStruct")`): each supplied member name must appear in
  the declared member-name list, else
  `error("Element expected names: "+expected_sub_names+ "  instead of: "+name_given_element)`;
  matched members are recursively type-checked.
- **Scalar** (else branch): `if(!check_matched_type(expected_type,value_type)){ error("Mismatched input "+value_type+ " expecting "+ expected_type, null, INVALID_TYPE) }`

Requires resolving `rosparam.from` into the `.ros2` file's `Parameter` declaration →
**NOT statically checkable**. Given the defect density documented in §3, the safe strategy is to
emit only scalar parameter values (Integer / Boolean / Double / String) and avoid List, Array and
Struct assignments entirely.

---

## 3. Buggy / fragile code to route around

Ordered by how likely it is to bite a generator.

1. **`fromFileHelper` — unguarded null dereference, twice.** §2.2. Both `system.fromFile.empty` and
   `system.fromFile.toString` are unguarded against `fromFile == null`, which is the state for
   32/52 corpus models. **Mitigation: always emit a quoted `fromFile` containing a `/`.**

2. **`from_type` / `to_type` are shared mutable validator state.** Declared at class scope:
   ```xtend
   Object from_type
   Object to_type
   ```
   Xtext validators are injected singletons. `MatchPortMsgs` assigns these only inside the six
   `if` branches — if a reference fails to match any branch (unresolved proxy, or a `RosConnection`
   endpoint), the field **retains the value from the previously validated connection**, and the
   `from_type !== to_type` test compares stale data. Also not thread-safe across concurrent
   validation jobs. *Mitigation: never rely on a "no error" result for a connection whose endpoints
   might not resolve; validate connections one per file when debugging.*

3. **`CheckParameterValue` recurses while using instance fields as loop counters.** `int i; int j;`
   are class-level fields, and the method recurses (lines 239, 264, 302) from *inside*
   `for (i=0;i<value_sub_type.length;i++)` loops. The recursive call resets `i`, corrupting the
   caller's iteration on return. `expected_type`, `value_type`, `expected_sub_types`,
   `value_sub_type`, `sub_element` and `expected_sub_type` are all likewise shared across recursion
   depths. Nested container parameters will produce arbitrary, non-deterministic diagnostics.
   *Mitigation: emit scalar parameter values only.*

4. **Three unconditional casts to `RosSystemConnectionImpl`.** `checkIfInterfaceInSystem`,
   `checkPortPatterns` and `MatchPortMsgs` each open with
   `var connection_def = connection as RosSystemConnectionImpl`. But the grammar allows the other
   branch (`RosSystem.xtext:123-124`):
   ```
   Connection returns Connection:
       ( => RosSystemConnection) | RosConnection
   ;
   ```
   Any `RosTopicConnection` / `RosServiceConnection` / `RosActionConnection` throws
   `ClassCastException` in all three checks. The grammar comment concedes the situation —
   *"RosConnections are also implemented but not used for now."* Note the cast targets the `*Impl`
   class rather than the interface, which is a further smell. **Mitigation: only ever emit the
   `RosSystemConnection` form `- [from_iface , to_iface]` referencing named `RosInterface` labels.**

5. **`checkIfInterfaceInSystem` recurses exactly one level and casts unconditionally.** Inside the
   `SubSystem` branch, `var rosnode = subcomponent as RosNode` — if a subsystem contains a nested
   `SubSystem`, this throws `ClassCastException`. There is also no recursion beyond depth 1, so
   interfaces two levels down are silently absent from `AllInterfaces`, yielding false
   "not part of the system" errors. *Mitigation: keep subsystem nesting flat, or avoid `subSystems:`
   altogether.*

6. **Java-class substring type tests.** `component.class.toString.contains("RosNode")` and
   `component.class.toString.contains("SubSystem")` test the *Java* class name, not `eClass`.
   Brittle against renames, proxies and dynamic EMF. Note the same file uses the more correct
   `eClass.name` elsewhere — the codebase is inconsistent with itself.

7. **`check_matched_type` uses containment, not equality.**
   ```xtend
   else if (expected_type.contains(given_type)){
       return true;
   }
   ```
   Any given type name that is a *substring* of the expected type name is accepted. This will
   silently admit mismatches wherever the metamodel's type names share prefixes.

8. **`getName` can fall off the end and return `null`.**
   ```xtend
   def String getName(String Element){
       if (Element.length()>0 && Element.contains("name:") && Element.contains(")")){
           return Element.substring(Element.indexOf("name:")+5,Element.indexOf(")"))
       }
   }
   ```
   No `else`. Xtend returns `null` when the guard fails. The result is fed straight into
   `expected_sub_names.contains(...)` and `==` comparisons in the struct branch. It also parses
   `EObject.toString()` output with `indexOf` — reliance on EMF's debug string format is fragile by
   construction. `getValue` (line 345) has no guard at all and will throw on any string lacking
   `value:` or `)`; it appears to be dead code.

9. **`ArrayHelp` vs `StructHelp` inconsistency in `RosSystemValidator`.** `StructHelp` tests
   `contains("Struc")` (truncated), while `RosValidator.StructHelp` tests `contains("Struct")`.
   Harmless — both are INFO — but indicative of the general care level.

10. **Naming-convention loops do not short-circuit.** R1–R4 emit one diagnostic per offending
    character. A 6-uppercase-character package name yields 6 ERRORs. Cosmetic, but relevant if the
    plugin counts diagnostics to judge success.

11. **`AllInterfaces.toArray.contains(...)`** (line 118) where the sibling branch uses
    `AllInterfaces.contains(...)` (line 112). Semantically equivalent after Xtend's implicit
    array→list conversion, just gratuitously different. Flagged only as an inconsistency signal.

---

## 4. Verification status

- All rule extraction is by **source reading**, complete and line-accurate against the two files
  named at the top.
- **Nothing was executed.** Established fact 8 holds and was independently reconfirmed: the shipped
  classes are class-file **major version 55 (Java 11)**, and the JRE on this machine is 1.8.0_481.
  No validator was run, and no diagnostic in this document was observed empirically.
- The `RosValidator` method inventory in §0.3 **was** verified against the shipped bytecode by
  parsing the constant pool of the extracted `RosValidator.class` — that is a static read of the
  binary, not an execution.
- The one inference that is not a direct read is the Xtend `.empty` → `isEmpty()` desugaring
  underpinning §2.2, stated there at ~90% confidence. Confirming it requires either a JDK 19+
  (`javap -c` on the Xtend-compiled class) or the `.RosSystemValidator.xtendbin` — note that the
  jars ship `.xtendbin` files for the ros/ros1/ros2 validators but, per §0.2, no rossystem jar
  exists to hold one.
- **Open item, pending a JDK 19+ (Java 21 Temurin):** for `.ros`/`.ros1`/`.ros2` only, R1–R13 can be exercised against
  the shipped LS jars. R14 cannot (absent from the jar). **S1–S10 can never be exercised against
  shipped artifacts** and would require building `de.fraunhofer.ipa.rossystem.xtext` from source.

---

## 5. Condensed emission checklist

Rules a generator must satisfy, in priority order.

**ERROR-severity, must never violate:**

1. Package name (`.ros2` root): `[a-z0-9_]` only — no uppercase. (R3)
2. Connection direction: `pub->`→`sub->`, `ss->`→`sc->`, `as->`→`ac->`, `from` is always the
   server/publisher. (S4)
3. Connection endpoint types must be identical spec objects — emit byte-identical `type:` strings on
   both ends. (S5)
4. Both connection endpoints must be interfaces of nodes declared in the same system. (S3)
5. Every node in a `Process`'s `nodes: [...]` must be declared in the system's `nodes:` block. (S1)
6. QoS durations: quoted `[+-]?[0-9]+` within **32-bit signed range** (≤ 2147483647 ns ≈ 2.1 s) or
   bare `infinite`. (R14) — *and per fact 7, excluded from the pinned emission profile anyway.*
7. `fromFile`: always emit, quoted, containing `/`. (S2 — bug avoidance, not a real rule.)

**WARNING-severity, should not violate:**

8. Node and artifact names: no uppercase. (R1, R2)
9. Parameter names: no uppercase in the final dot-segment. (R4)
10. All message/service/action references must resolve — declare the `.ros` spec and list the
    dependency. (R5–R10)

**Avoid entirely (defective validator paths):**

11. `RosConnection` syntax (`- [publisher , subscriber]` referencing `ros::Publisher` directly) —
    triggers `ClassCastException`. Use `RosSystemConnection` referencing `RosInterface` labels.
12. Nested subsystems more than one level deep.
13. List / Array / Struct parameter values.
