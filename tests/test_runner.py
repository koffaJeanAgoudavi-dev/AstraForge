import pytest

from astraforge.workspace.runner import DockerCommandRunner


def test_docker_runner_rejects_non_allowlisted_command(tmp_path):
    runner = DockerCommandRunner()
    with pytest.raises(ValueError):
        runner.run(tmp_path, ["bash", "-lc", "id"])


def test_docker_runner_builds_sandbox_flags(tmp_path, monkeypatch):
    calls = {}

    class Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, **kwargs):
        calls["command"] = command
        return Result()

    monkeypatch.setattr("astraforge.workspace.runner.subprocess.run", fake_run)
    result = DockerCommandRunner().run(tmp_path, ["python", "-c", "print('ok')"])

    assert result.return_code == 0
    command = calls["command"]
    assert "--network" in command and "none" in command
    assert "--read-only" in command
    assert "--cap-drop" in command and "ALL" in command
    assert "--pids-limit" in command
    assert "--memory" in command
    assert "--cpus" in command
