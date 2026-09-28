"""GitHub operations used by AstraForge."""

from dataclasses import dataclass

from github import Github
from github.GithubException import UnknownObjectException


@dataclass(frozen=True)
class PullRequestInfo:
    number: int
    url: str
    branch: str


class GitHubAdapter:
    def __init__(self, token: str, repository: str) -> None:
        if not token:
            raise ValueError("GitHub token is required")
        if not repository:
            raise ValueError("GitHub repository is required")
        self.client = Github(token)
        self.repository = self.client.get_repo(repository)

    def create_branch(self, branch: str, base_branch: str = "main") -> None:
        base = self.repository.get_branch(base_branch)
        self.repository.create_git_ref(ref=f"refs/heads/{branch}", sha=base.commit.sha)

    def commit_file(self, branch: str, path: str, content: str, message: str) -> None:
        try:
            existing = self.repository.get_contents(path, ref=branch)
        except UnknownObjectException:
            self.repository.create_file(path, message, content, branch=branch)
            return
        if isinstance(existing, list):
            raise ValueError(f"Expected a file, got a directory: {path}")
        self.repository.update_file(path, message, content, existing.sha, branch=branch)

    def open_pull_request(
        self,
        branch: str,
        base_branch: str = "main",
        title: str = "AstraForge generated changes",
        body: str = "Generated and reviewed by AstraForge.",
    ) -> PullRequestInfo:
        pr = self.repository.create_pull(title=title, body=body, head=branch, base=base_branch)
        return PullRequestInfo(pr.number, pr.html_url, branch)
