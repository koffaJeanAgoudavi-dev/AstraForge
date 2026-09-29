import subprocess

import pytest

from astraforge.integrations.deployment import CloudflarePagesDeployer


def test_cloudflare_deployer_builds_safe_command(tmp_path, monkeypatch):
    calls = {}

    class Result:
        returncode = 0
        stdout = "Published https://example.pages.dev"
        stderr = ""

    def fake_run(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return Result()

    monkeypatch.setattr("astraforge.integrations.deployment.subprocess.run", fake_run)
    result = CloudflarePagesDeployer("token", "account", "demo").deploy(tmp_path)

    assert result.url == "https://example.pages.dev"
    assert calls["command"][:4] == ["npx", "wrangler", "pages", "deploy"]
    assert "--project-name" in calls["command"]
    assert calls["kwargs"]["env"]["CLOUDFLARE_API_TOKEN"] == "token"
    assert calls["kwargs"]["env"]["CLOUDFLARE_ACCOUNT_ID"] == "account"


def test_deployer_rejects_output_outside_workspace(tmp_path):
    outside = tmp_path.parent / "outside"
    with pytest.raises(ValueError, match="inside the workspace"):
        CloudflarePagesDeployer("token", "account", "demo", "../outside").deploy(tmp_path)


def test_deployer_rejects_missing_output_directory(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        CloudflarePagesDeployer("token", "account", "demo", "dist").deploy(tmp_path)


def test_deployer_rejects_non_pages_url(tmp_path, monkeypatch):
    class Result:
        returncode = 0
        stdout = "Published https://example.pages.dev.attacker.test"
        stderr = ""

    monkeypatch.setattr(
        "astraforge.integrations.deployment.subprocess.run", lambda *args, **kwargs: Result()
    )
    with pytest.raises(RuntimeError, match="no valid Pages URL"):
        CloudflarePagesDeployer("token", "account", "demo").deploy(tmp_path)


def test_deployer_reports_wrangler_failure(tmp_path, monkeypatch):
    class Result:
        returncode = 1
        stdout = ""
        stderr = "authentication failed"

    monkeypatch.setattr(
        "astraforge.integrations.deployment.subprocess.run", lambda *args, **kwargs: Result()
    )
    with pytest.raises(RuntimeError, match="authentication failed"):
        CloudflarePagesDeployer("token", "account", "demo").deploy(tmp_path)


def test_deployer_reports_timeout(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired("wrangler", 1)

    monkeypatch.setattr("astraforge.integrations.deployment.subprocess.run", fail)
    with pytest.raises(RuntimeError, match="timed out"):
        CloudflarePagesDeployer("token", "account", "demo").deploy(tmp_path)


def test_deployer_requires_positive_timeout():
    with pytest.raises(ValueError, match="positive"):
        CloudflarePagesDeployer("token", "account", "demo", timeout=0)
