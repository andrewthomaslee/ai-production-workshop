"""Deterministic test suite: verifies every boundary WITHOUT calling the LLM.

Run:  uv run python -m scripts.test_suite

Covers the mechanical guarantees that must hold no matter what the model does:
filesystem scoping, role-based tool filtering, audit logging, per-user isolation,
and the project tools (training divergence, deploy serving a live URL). The
model-dependent BEHAVIOR (does the agent actually do the right thing?) is tested
separately by the agent evals in agent/evals/ (which run the real LLM + a judge).

`run()` returns structured results so the API/UI can show the same board; `main()`
prints it for the terminal.
"""

from __future__ import annotations

import tempfile
import urllib.request
from pathlib import Path

from agent.core.audit import AuditLog
from agent.core.policy import Policy, ROLE_TOOLS
from agent.sandbox.runner import get_runner
from agent.tools.deploy import DeploySite, _HOST, _PORT
from agent.tools.fs import ListFiles, ReadFile, WriteFile
from agent.tools.python import RunPython
from agent.tools.registry import ToolRegistry
from agent.tools.training import StartTraining, TrainingStatus


class _Collector:
    """Records (group, name, passed) so results can be printed AND returned."""
    def __init__(self):
        self.group = ""
        self.rows: list[dict] = []

    def start(self, group: str):
        self.group = group

    def check(self, name: str, condition: bool):
        self.rows.append({"group": self.group, "name": name, "passed": bool(condition)})


def _ws() -> Path:
    d = Path(tempfile.mkdtemp()) / "ws"
    d.mkdir(parents=True)
    return d


def test_filesystem_scoping(c: _Collector):
    c.start("Filesystem scoping")
    ws = _ws()
    # Go through the registry's dispatch (the real path), which turns the scoping
    # exception into a readable error string the model would see.
    reg = ToolRegistry([ReadFile(ws), WriteFile(ws)])
    reg.dispatch("write_file", {"path": "a.txt", "content": "hello"})
    c.check("read returns content", reg.dispatch("read_file", {"path": "a.txt"}) == "hello")
    c.check("../ escape is blocked", "escapes" in reg.dispatch("read_file", {"path": "../secret"}))
    c.check("absolute escape is blocked", "escapes" in reg.dispatch("read_file", {"path": "/etc/passwd"}))


def test_role_filtering_and_audit(c: _Collector):
    c.start("Role filtering + audit")
    ws = _ws()
    audit = AuditLog(ws.parent / "audit.jsonl")
    tools = [ReadFile(ws), WriteFile(ws), ListFiles(ws), RunPython(get_runner("subprocess", ws))]

    viewer = ToolRegistry(tools, policy=Policy(), audit=audit, role="viewer", user_id="v")
    names = {s["function"]["name"] for s in viewer.schemas()}
    c.check("viewer cannot see write_file/run_python", "write_file" not in names and "run_python" not in names)
    c.check("viewer can see read_file/list_files", {"read_file", "list_files"} <= names)
    c.check("viewer run_python denied at dispatch", "permission denied" in viewer.dispatch("run_python", {"code": "print(1)"}))

    analyst = ToolRegistry(tools, policy=Policy(), audit=audit, role="analyst", user_id="a")
    c.check("analyst run_python allowed -> 42", analyst.dispatch("run_python", {"code": "print(6*7)"}).strip() == "42")

    rows = audit.entries()
    c.check("audit logged the denial", any(r["tool"] == "run_python" and not r["allowed"] for r in rows))
    c.check("audit logged the allow", any(r["tool"] == "run_python" and r["allowed"] for r in rows))


def test_tenant_isolation(c: _Collector):
    c.start("Tenant isolation (paths)")
    root = Path(tempfile.mkdtemp())
    a = root / "data" / "alice" / "workspace"
    b = root / "data" / "bob" / "workspace"
    a.mkdir(parents=True); b.mkdir(parents=True)
    WriteFile(a).run(path="secret.txt", content="ALICE")
    reg_b = ToolRegistry([ReadFile(b)])
    c.check("bob's workspace cannot reach alice's file",
            "escapes" in reg_b.dispatch("read_file", {"path": "../../alice/workspace/secret.txt"}))
    c.check("alice's file exists in her own space", ReadFile(a).run(path="secret.txt") == "ALICE")


def test_policy_shape(c: _Collector):
    c.start("Policy shape")
    c.check("viewer < analyst < admin (subsets)",
            ROLE_TOOLS["viewer"] < ROLE_TOOLS["analyst"] < ROLE_TOOLS["admin"])
    c.check("deploy_site is admin-only",
            "deploy_site" in ROLE_TOOLS["admin"] and "deploy_site" not in ROLE_TOOLS["analyst"])


def test_training_tool(c: _Collector):
    c.start("ML training tool")
    ws = _ws()
    good = StartTraining(ws).run(name="good", epochs=8, learning_rate=0.3)
    c.check("good run COMPLETED", "COMPLETED" in good)
    bad = StartTraining(ws).run(name="bad", epochs=8, learning_rate=5.0)
    c.check("high LR run FAILED with diagnosis", "FAILED" in bad and "too high" in bad)
    c.check("status reads back metrics", "metrics" in TrainingStatus(ws).run(job_id="bad").lower())


def test_deploy_tool(c: _Collector):
    c.start("Deploy tool (live URL)")
    ws = _ws()
    (ws / "site").mkdir()
    (ws / "site" / "index.html").write_text("<h1>SUITE_DEPLOY_OK</h1>")
    res = DeploySite(ws).run(site_dir="site", slug="suite-test")
    c.check("deploy returns a URL", "http://" in res)
    body = urllib.request.urlopen(f"http://{_HOST}:{_PORT}/suite-test/", timeout=5).read().decode()
    c.check("deployed URL serves the page", "SUITE_DEPLOY_OK" in body)
    c.check("deploy of missing dir errors", "Error" in DeploySite(ws).run(site_dir="nope", slug="x"))


_TESTS = [
    test_filesystem_scoping, test_role_filtering_and_audit, test_tenant_isolation,
    test_policy_shape, test_training_tool, test_deploy_tool,
]


def run() -> dict:
    """Run all boundary checks and return a structured summary (no printing)."""
    c = _Collector()
    for t in _TESTS:
        t(c)
    passed = sum(1 for r in c.rows if r["passed"])
    return {"total": len(c.rows), "passed": passed, "checks": c.rows}


def main() -> None:
    PASS, FAIL = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m"
    summary = run()
    print("\n=== Deterministic test suite (no LLM) ===\n")
    group = None
    for r in summary["checks"]:
        if r["group"] != group:
            group = r["group"]
            print(group)
        print(f"  [{PASS if r['passed'] else FAIL}] {r['name']}")
    print(f"\n=== {summary['passed']}/{summary['total']} checks passed ===")
    if summary["passed"] != summary["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
