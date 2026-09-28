"""Structured shared context for multi-agent execution."""

from dataclasses import dataclass, field


@dataclass
class ExecutionContext:
    project_id: str
    architecture: str = ""
    requirements: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    test_results: list[dict] = field(default_factory=list)
    tester_findings: list[str] = field(default_factory=list)
    reviewer_findings: list[str] = field(default_factory=list)
    repairs: list[dict] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)

    def record_test(self, passed: bool, attempts: int, stdout: str = "", stderr: str = "") -> None:
        self.test_results.append({
            "passed": passed,
            "attempts": attempts,
            "stdout": stdout[-6000:],
            "stderr": stderr[-6000:],
        })

    def record_repair(self, source: str, details: str) -> None:
        self.repairs.append({"source": source, "details": details[-6000:]})

    def add_decision(self, decision: str) -> None:
        if decision and decision not in self.decisions:
            self.decisions.append(decision)

    def snapshot(self) -> dict:
        return {
            "project_id": self.project_id,
            "architecture": self.architecture,
            "requirements": self.requirements,
            "files": self.files,
            "test_results": self.test_results,
            "tester_findings": self.tester_findings,
            "reviewer_findings": self.reviewer_findings,
            "repairs": self.repairs,
            "decisions": self.decisions,
        }

    def prompt(self) -> str:
        import json
        return json.dumps(self.snapshot(), indent=2, ensure_ascii=False)
