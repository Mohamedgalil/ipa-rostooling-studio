#!/usr/bin/env python3
"""
Test suite for ros-system-builder workflow:
1. System Decomposition & Node Resolution (.rossystem -> .ros2 nodes)
2. Multi-node Wrapper Generation
3. System Composition & Launch Code Generation (generate_rossystem_code)
4. Domain Logic Shield across Multi-node Packages
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import pytest

STUDIO_ROOT = Path(__file__).resolve().parent.parent
EXT_ROOT = STUDIO_ROOT.parent / "RosTooling_Extension"
MCP_BIN = EXT_ROOT / "rostooling-languages" / "bin" / "rostooling-mcp.js"


@pytest.fixture
def multi_node_system():
    tmp_dir = Path(tempfile.mkdtemp(prefix="ros_sys_test_"))

    # 1. Package .ros2 model: contains 2 nodes (producer and consumer)
    ros2_content = """pipeline_nodes:
  fromGitRepo: "https://github.com/example/pipeline_nodes"
  artifacts:
    producer_artifact:
      node: producer_node
      publishers:
        data_out:
          type: 'std_msgs/msg/String'
    consumer_artifact:
      node: consumer_node
      subscribers:
        data_in:
          type: 'std_msgs/msg/String'
"""
    ros2_file = tmp_dir / "pipeline_nodes.ros2"
    ros2_file.write_text(ros2_content, encoding="utf-8")

    # 2. System .rossystem model: composes producer and consumer and wires them
    rossystem_content = """pipeline_system:
  fromFile: "pipeline_system/launch/pipeline.launch.py"
  nodes:
    "producer":
      from: "pipeline_nodes.producer_node"
      interfaces:
        - "out": pub-> "producer_artifact::data_out"
    "consumer":
      from: "pipeline_nodes.consumer_node"
      interfaces:
        - "in": sub-> "consumer_artifact::data_in"
  connections:
    - ["out" , "in"]
"""
    rossystem_file = tmp_dir / "pipeline_system.rossystem"
    rossystem_file.write_text(rossystem_content, encoding="utf-8")

    yield tmp_dir, ros2_file, rossystem_file
    shutil.rmtree(tmp_dir, ignore_errors=True)


def _call_mcp_tool(tool_name: str, arguments: dict, workspace_dir: Path):
    """Invokes an MCP tool via rostooling-mcp.js over stdio JSON-RPC."""
    node_script = f"""
const {{ spawn }} = require("child_process");
const p = spawn("node", ["{MCP_BIN}"], {{ stdio: ["pipe", "pipe", "inherit"] }});
let buf = "";
p.stdout.on("data", (d) => {{
  buf += d.toString();
  const lines = buf.split("\\n");
  buf = lines.pop();
  for (const l of lines) {{
    if (!l.trim()) continue;
    try {{
      const msg = JSON.parse(l);
      if (msg.id === 2) {{
        console.log(JSON.stringify(msg.result));
        p.kill();
        process.exit(0);
      }}
    }} catch(e) {{}}
  }}
}});

p.stdin.write(JSON.stringify({{ jsonrpc: "2.0", id: 1, method: "initialize", params: {{ protocolVersion: "2024-11-05", capabilities: {{}}, clientInfo: {{ name: "test", version: "1.0" }} }} }}) + "\\n");
setTimeout(() => {{
  p.stdin.write(JSON.stringify({{
    jsonrpc: "2.0",
    id: 2,
    method: "tools/call",
    params: {{
      name: "{tool_name}",
      arguments: {json.dumps(arguments)}
    }}
  }}) + "\\n");
}}, 400);
setTimeout(() => {{ p.kill(); process.exit(1); }}, 25000);
"""
    runner = workspace_dir / f"run_{tool_name}.js"
    runner.write_text(node_script, encoding="utf-8")
    res = subprocess.run(["node", str(runner)], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"MCP {tool_name} failed: {res.stderr}"

    for line in res.stdout.splitlines():
        if line.startswith('{"content":'):
            data = json.loads(line)
            return json.loads(data["content"][0]["text"])

    pytest.fail(f"Could not parse MCP {tool_name} response from stdout: {res.stdout}")


def test_system_builder_workflow(multi_node_system):
    tmp_dir, ros2_file, rossystem_file = multi_node_system

    # Step 1: Generate wrappers for custom nodes in the system
    gen_nodes = _call_mcp_tool(
        "generate_ros2_wrappers",
        {
            "model_path": str(ros2_file),
            "language": "python",
            "ros_distro": "jazzy",
            "workspace_dir": str(tmp_dir),
        },
        tmp_dir,
    )
    assert gen_nodes["status"] == "success"
    pkg_dir = tmp_dir / "src-gen" / "pipeline_nodes" / "pipeline_nodes"

    # Both nodes should have their independent logic and wrapper files
    producer_logic = pkg_dir / "producer_node_logic.py"
    consumer_logic = pkg_dir / "consumer_node_logic.py"
    producer_wrapper = pkg_dir / "producer_node_wrapper.py"
    consumer_wrapper = pkg_dir / "consumer_node_wrapper.py"

    assert producer_logic.exists(), "producer_node_logic.py not generated"
    assert consumer_logic.exists(), "consumer_node_logic.py not generated"
    assert producer_wrapper.exists(), "producer_node_wrapper.py not generated"
    assert consumer_wrapper.exists(), "consumer_node_wrapper.py not generated"

    # Step 2: Simulate subagents implementing domain logic for both nodes
    producer_code = producer_logic.read_text(encoding="utf-8")
    producer_logic.write_text(producer_code + "\n# PRODUCER LOGIC IMPLEMENTED BY SUBAGENT 1\n", encoding="utf-8")

    consumer_code = consumer_logic.read_text(encoding="utf-8")
    consumer_logic.write_text(consumer_code + "\n# CONSUMER LOGIC IMPLEMENTED BY SUBAGENT 2\n", encoding="utf-8")

    # Step 3: Trigger System Code Generation (generate_rossystem_code)
    gen_sys = _call_mcp_tool(
        "generate_rossystem_code",
        {
            "model_path": str(rossystem_file),
            "workspace_dir": str(tmp_dir),
        },
        tmp_dir,
    )
    assert gen_sys["status"] == "success"
    sys_dir = tmp_dir / "src-gen" / "pipeline_system"
    assert sys_dir.exists(), "pipeline_system output directory was not created"

    # Step 4: Re-run node generator to verify Domain Logic Shield across multi-node package
    gen_nodes_2 = _call_mcp_tool(
        "generate_ros2_wrappers",
        {
            "model_path": str(ros2_file),
            "language": "python",
            "ros_distro": "jazzy",
            "workspace_dir": str(tmp_dir),
        },
        tmp_dir,
    )
    assert gen_nodes_2["status"] == "success"
    assert "pipeline_nodes/pipeline_nodes/producer_node_logic.py" not in gen_nodes_2["writtenFiles"]
    assert "pipeline_nodes/pipeline_nodes/consumer_node_logic.py" not in gen_nodes_2["writtenFiles"]

    # Verify custom code in both files remained intact
    assert "PRODUCER LOGIC IMPLEMENTED BY SUBAGENT 1" in producer_logic.read_text(encoding="utf-8")
    assert "CONSUMER LOGIC IMPLEMENTED BY SUBAGENT 2" in consumer_logic.read_text(encoding="utf-8")
