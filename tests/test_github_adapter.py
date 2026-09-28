from astraforge.integrations.github import GitHubAdapter


def test_github_adapter_requires_token():
    try:
        GitHubAdapter("", "owner/repo")
    except ValueError as exc:
        assert "token" in str(exc).lower()
    else:
        raise AssertionError("Expected missing token to fail")
