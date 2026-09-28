from astraforge.integrations.deployment import CloudflarePagesDeployer


def test_cloudflare_deployer_builds_safe_command(tmp_path, monkeypatch):
    calls = {}

    class Result:
        returncode = 0
        stdout = "Published https://example.pages.dev"
        stderr = ""

    def fake_run(command, **kwargs):
        calls["command"] = command
        return Result()

    monkeypatch.setattr("astraforge.integrations.deployment.subprocess.run", fake_run)
    result = CloudflarePagesDeployer("token", "account", "demo").deploy(tmp_path)

    assert result.url == "https://example.pages.dev"
    assert calls["command"][:4] == ["npx", "wrangler", "pages", "deploy"]
    assert "--project-name" in calls["command"]
