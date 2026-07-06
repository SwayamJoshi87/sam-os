"""End-to-end tests for setup/orchestration tools."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from conftest import MCPServerProcess


def test_setup_check(server: MCPServerProcess):
    resp = server.call_tool("setup_check_tool", {})
    assert resp["ok"]
    assert resp["data"]["venv_present"] is True
    assert resp["data"]["deps_importable"] is True
    assert resp["data"]["db_dir_writable"] is True
    assert resp["data"]["ready_to_run"] is True


def test_setup_seed_template(server: MCPServerProcess):
    resp = server.call_tool("setup_seed_template", {})
    assert resp["ok"]
    # The conftest seeds test data, so this should be skipped.
    assert resp["data"]["seeded"] is False


def test_setup_verify_calendar_offline(server: MCPServerProcess):
    resp = server.call_tool("setup_verify_calendar", {})
    assert resp["ok"]
    assert resp["data"]["offline"] is True


def test_setup_write_hermes_config(server: MCPServerProcess, tmp_path: Path):
    output = tmp_path / "mcp.json"
    resp = server.call_tool(
        "setup_write_hermes_config",
        {"output_path": str(output), "calendar_offline": True},
    )
    assert resp["ok"]
    assert Path(resp["data"]["written_to"]) == output
    assert output.exists()
    config = json.loads(output.read_text())
    assert "sam-os" in config["mcpServers"]
    assert resp["data"]["deployment"] == "venv"


def test_setup_write_hermes_config_docker(server: MCPServerProcess, tmp_path: Path):
    output = tmp_path / "mcp-docker.json"
    resp = server.call_tool(
        "setup_write_hermes_config",
        {"output_path": str(output), "calendar_offline": True, "use_docker": True},
    )
    assert resp["ok"]
    assert resp["data"]["deployment"] == "docker"
    config = json.loads(output.read_text())
    assert config["mcpServers"]["sam-os"]["command"] == "docker"
