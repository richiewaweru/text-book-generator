import subprocess
from pathlib import Path

import pytest

from automation.scripts import validate_repo
from automation.scripts.commit_if_green import CommitGateError, commit_if_green


def run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ['git', *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )


def init_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / 'repo'
    repo_root.mkdir()
    run_git(repo_root, 'init', '-b', 'main')
    run_git(repo_root, 'config', 'user.name', 'Automation Test')
    run_git(repo_root, 'config', 'user.email', 'automation@example.com')
    (repo_root / 'README.md').write_text('initial\n', encoding='utf-8')
    run_git(repo_root, 'add', 'README.md')
    run_git(repo_root, 'commit', '-m', 'chore(repo): initial commit')
    return repo_root


def test_commit_if_green_refuses_on_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo_root = init_repo(tmp_path)
    (repo_root / 'README.md').write_text('changed\n', encoding='utf-8')
    run_git(repo_root, 'add', 'README.md')
    monkeypatch.setattr(validate_repo, 'validate_scope', lambda scope, repo_root=None: [])

    with pytest.raises(CommitGateError, match='protected branch'):
        commit_if_green('docs', 'docs', 'update readme', repo_root=repo_root)


def test_commit_if_green_fails_when_validation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    repo_root = init_repo(tmp_path)
    run_git(repo_root, 'checkout', '-b', 'feat/test-branch')
    (repo_root / 'README.md').write_text('changed\n', encoding='utf-8')
    run_git(repo_root, 'add', 'README.md')

    def _raise_validation(scope: str, repo_root: Path | None = None):
        raise validate_repo.ValidationError('boom')

    monkeypatch.setattr(validate_repo, 'validate_scope', _raise_validation)

    with pytest.raises(validate_repo.ValidationError):
        commit_if_green('feat', 'backend', 'add workflow automation', repo_root=repo_root)


def test_commit_if_green_fails_without_staged_changes(tmp_path: Path):
    repo_root = init_repo(tmp_path)
    run_git(repo_root, 'checkout', '-b', 'feat/test-branch')

    with pytest.raises(CommitGateError, match='No staged changes'):
        commit_if_green('feat', 'backend', 'add workflow automation', repo_root=repo_root)


def test_commit_if_green_succeeds_with_staged_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    repo_root = init_repo(tmp_path)
    run_git(repo_root, 'checkout', '-b', 'feat/test-branch')
    (repo_root / 'README.md').write_text('changed\n', encoding='utf-8')
    run_git(repo_root, 'add', 'README.md')
    monkeypatch.setattr(validate_repo, 'validate_scope', lambda scope, repo_root=None: [])

    message = commit_if_green(
        'feat',
        'backend',
        'add workflow automation',
        repo_root=repo_root,
    )

    latest_message = run_git(repo_root, 'log', '-1', '--pretty=%s').stdout.strip()
    assert message == 'feat(backend): add workflow automation'
    assert latest_message == message
