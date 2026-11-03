#!/usr/bin/env python3
"""
Test suite for ros-node-developer workflow:
1. Model Contract Check
2. Deterministic Wrapper Generation (Headless via MCP)
3. Domain Logic Shield (Idempotency and Overwrite Protection)
4. Pure Business Logic Unit Testing (Zero ROS 2 runtime required)
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
def sample_workspace():
    tmp_dir = Path(tempfile.mkdtemp(prefix="ros_node_dev_test_"))
    model_file = tmp_dir / "sample_filter.ros2"
    model_content = """sample_filter:
  fromGitRepo: "https://github.com/example/sample_filter"
  artifacts:
    filter_node:
      node: filter_node
      publishers:
        filtered_scan:
          type: 'sensor_msgs/msg/LaserScan'
      subscribers:
        raw_scan:
          type: 'sensor_msgs/msg/LaserScan'
      parameters:
        threshold:
          type: Double
          default: 1.5
"""
    model_file.write_text(model_content, encoding="utf-8")
    yield tmp_dir, model_file
    shutil.rmtree(tmp_dir, ignore_errors=True)


def _call_mcp_generate(model_path: Path, workspace_dir: Path, language="python"):
    """Invokes generate_ros2_wrappers over stdio JSON-RPC via rostooling-mcp.js."""
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
      name: "generate_ros2_wrappers",
      arguments: {{
        model_path: "{model_path}",
        language: "{language}",
        ros_distro: "jazzy",
        workspace_dir: "{workspace_dir}"
      }}
    }}
  }}) + "\\n");
}}, 400);
setTimeout(() => {{ p.kill(); process.exit(1); }}, 25000);
"""
    runner_file = workspace_dir / "runner.js"
    runner_file.write_text(node_script, encoding="utf-8")
    res = subprocess.run(["node", str(runner_file)], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"MCP invocation failed: {res.stderr}"

    for line in res.stdout.splitlines():
        if line.startswith('{"content":'):
            data = json.loads(line)
            return json.loads(data["content"][0]["text"])

    pytest.fail(f"Could not parse MCP response from stdout: {res.stdout}")


def test_wrapper_generation_and_domain_logic_shield(sample_workspace):
    tmp_dir, model_file = sample_workspace

    # 1. Initial Generation
    gen1 = _call_mcp_generate(model_file, tmp_dir, language="python")
    assert gen1["status"] == "success"
    assert gen1["package"] == "sample_filter"
    assert "sample_filter/sample_filter/filter_node_logic.py" in gen1["writtenFiles"]
    assert "sample_filter/sample_filter/filter_node_wrapper.py" in gen1["writtenFiles"]

    logic_file = tmp_dir / "src-gen" / "sample_filter" / "sample_filter" / "filter_node_logic.py"
    assert logic_file.exists(), "Logic file was not created"

    # 2. Modify logic file (Simulate agent implementing business logic)
    custom_signature = "# AGENT CUSTOM DOMAIN LOGIC: v1.0.0"
    content = logic_file.read_text(encoding="utf-8")
    logic_file.write_text(content + "\n" + custom_signature + "\n", encoding="utf-8")

    # 3. Re-run generation (Simulate re-generating after interface or system changes)
    gen2 = _call_mcp_generate(model_file, tmp_dir, language="python")
    assert gen2["status"] == "success"
    # Ensure Domain Logic Shield protected the file:
    # It must NOT be re-written (either skipped by generator or skipped by post-processor)
    assert "sample_filter/sample_filter/filter_node_logic.py" not in gen2["writtenFiles"], (
        "Domain logic file was re-written by generator!"
    )

    # Verify content was strictly preserved
    updated_content = logic_file.read_text(encoding="utf-8")
    assert custom_signature in updated_content, "Custom domain logic was overwritten!"


def test_pure_logic_unit_testing_without_ros2(sample_workspace):
    """Verifies that the generated logic class can be executed and unit-tested
    purely in Python without any running ROS 2 daemon or middleware."""
    tmp_dir, model_file = sample_workspace

    _call_mcp_generate(model_file, tmp_dir, language="python")
    pkg_dir = tmp_dir / "src-gen" / "sample_filter"

    # Add pkg to sys.path
    import sys
    sys.path.insert(0, str(pkg_dir))

    try:
        from sample_filter.filter_node_logic import filter_nodeLogic

        logic = filter_nodeLogic()

        # Injected mock logger
        logs = []
        logic.set_logger(lambda level, msg: logs.append((level, msg)))

        # Injected mock publisher
        published_msgs = []
        logic.set_filtered_scan_publisher(lambda msg: published_msgs.append(msg))

        # Test parameter handling
        logic.set_parameter("threshold", 2.5)
        assert logic.get_parameter("threshold") == 2.5

        # Test logging
        logic.log_info("Node initialized successfully")
        assert len(logs) == 1
        assert logs[0][1] == "Node initialized successfully"

        # Mock an incoming LaserScan object
        class MockLaserScan:
            def __init__(self, ranges):
                self.ranges = ranges

        # Define custom implementation of on_raw_scan_received
        def custom_scan_handler(self_obj, scan):
            thresh = self_obj.get_parameter("threshold")
            filtered = [r if r >= thresh else float("inf") for r in scan.ranges]
            self_obj.publish_filtered_scan(MockLaserScan(filtered))

        # Dynamically attach handler for testing
        filter_nodeLogic.on_raw_scan_received = custom_scan_handler

        # Feed test scan
        test_scan = MockLaserScan([1.0, 2.0, 3.0, 0.5])
        logic.on_raw_scan_received(test_scan)

        # Assert output was published correctly
        assert len(published_msgs) == 1
        assert published_msgs[0].ranges == [float("inf"), float("inf"), 3.0, float("inf")]

    finally:
        if str(pkg_dir) in sys.path:
            sys.path.remove(str(pkg_dir))
