"""Shared test fixtures and helpers for sam-os MCP server tests."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
PYTHON = sys.executable


def make_fresh_db() -> Path:
    """Create a temp directory with a fresh SQLite DB and apply migrations."""
    tmpdir = Path(tempfile.mkdtemp(prefix="samos-test-"))
    db_path = tmpdir / "schedule.db"

    # Import after clearing env so we don't pick up the user's real DB
    env = os.environ.copy()
    env["SAMOS_DB_PATH"] = str(db_path)
    env["PYTHONIOENCODING"] = "utf-8"
    env["SAMOS_CALENDAR_OFFLINE"] = "1"

    # Run init via the package
    subprocess.run(
        [PYTHON, "-c", "from samos.db import init_db; init_db()"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
    )
    return db_path


def seed_test_data(db_path: Path):
    """Populate the fresh DB with categories and template tasks."""
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "INSERT INTO categories (name, color) VALUES ('gym', 'red'), ('work', 'blue')"
    )
    cats = {r["name"]: r["id"] for r in conn.execute("SELECT * FROM categories").fetchall()}
    conn.execute(
        """
        INSERT INTO tasks (category_id, name, day_of_week, time_start, duration_min, fixed)
        VALUES (?, 'morning gym', 0, '07:00', 60, 1)
        """,
        (cats["gym"],),
    )
    conn.execute(
        """
        INSERT INTO tasks (category_id, name, day_of_week, time_start, duration_min, fixed)
        VALUES (?, 'team meeting', 0, '09:00', 60, 1)
        """,
        (cats["work"],),
    )
    conn.commit()
    conn.close()


class MCPServerProcess:
    """Launch samos.server as a subprocess and speak JSON-RPC over stdio."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.proc = None
        self._msg_id = 0

    def __enter__(self):
        env = os.environ.copy()
        env["SAMOS_DB_PATH"] = str(self.db_path)
        env["PYTHONIOENCODING"] = "utf-8"
        env["SAMOS_CALENDAR_OFFLINE"] = "1"

        self.proc = subprocess.Popen(
            [PYTHON, "-u", "-m", "samos.server"],
            cwd=REPO_ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding="utf-8",
        )
        # Wait for server to be ready by reading initialize response
        self.call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}})
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.proc:
            try:
                self.proc.stdin.close()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        return False

    def call(self, method: str, params: dict | None = None) -> dict:
        self._msg_id += 1
        msg = {
            "jsonrpc": "2.0",
            "id": self._msg_id,
            "method": method,
            "params": params or {},
        }
        line = json.dumps(msg) + "\n"
        self.proc.stdin.write(line)
        self.proc.stdin.flush()

        # Read until we get a response with matching id
        while True:
            out_line = self.proc.stdout.readline()
            if not out_line:
                raise RuntimeError("server closed stdout before responding")
            try:
                resp = json.loads(out_line)
            except json.JSONDecodeError:
                continue
            if resp.get("id") == self._msg_id:
                return resp

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        resp = self.call("tools/call", {"name": name, "arguments": arguments or {}})
        return _extract_tool_result(resp)


def _extract_tool_result(resp: dict) -> dict:
    """Parse the result of tools/call into a plain dict."""
    result = resp.get("result", {})
    if result.get("isError"):
        raise ToolError(result.get("content", [{}])[0].get("text", "unknown error"))
    text = result.get("content", [{}])[0].get("text", "{}")
    return json.loads(text)


class ToolError(Exception):
    pass


@pytest.fixture
def fresh_db():
    db_path = make_fresh_db()
    seed_test_data(db_path)
    yield db_path
    # Cleanup temp directory after the test
    shutil.rmtree(db_path.parent, ignore_errors=True)


@pytest.fixture
def server(fresh_db):
    with MCPServerProcess(fresh_db) as s:
        yield s
