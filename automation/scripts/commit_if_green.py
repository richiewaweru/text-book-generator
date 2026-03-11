from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from automation.scripts import validate_repo

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_TYPES = {'feat', 'fix', 'refactor', 'docs', 'test', 'chore', 'ci', 'build'}
PROTECTED_BRANCHES = {'main', 'master'}
SCOPE_PATTERN = re.compile(r'^[a-z0-9][a-z0-9_-]*$')


class CommitGateError(RuntimeError):
    """Raised when the guarded commit command refuses to proceed."""


def run_git(args: Sequence[str], repo_root: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ['git', *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )


def git_output(args: Sequence[str], repo_root: Path = REPO_ROOT) -> str:
    completed = run_git(args=args, repo_root=repo_root)
    if completed.returncode != 0:
        raise CommitGateError(completed.stderr.strip() or completed.stdout.strip() or 'git failed')
    return completed.stdout.strip()


def current_branch(repo_root: Path = REPO_ROOT) -> str:
    return git_output(['rev-parse', '--abbrev-ref', 'HEAD'], repo_root=repo_root)


def staged_files(repo_root: Path = REPO_ROOT) -> list[str]:
    output = git_output(['diff', '--cached', '--name-only', '--diff-filter=ACMR'], repo_root=repo_root)
    return [line for line in output.splitlines() if line.strip()]


def unexpected_worktree_entries(repo_root: Path = REPO_ROOT) -> list[str]:
    output = git_output(['status', '--porcelain'], repo_root=repo_root)
    dirty_entries: list[str] = []
    for line in output.splitlines():
        if not line:
            continue
        if line.startswith('??'):
            dirty_entries.append(line)
            continue
        if len(line) >= 2 and line[1] != ' ':
            dirty_entries.append(line)
    return dirty_entries


def build_commit_message(commit_type: str, scope: str, summary: str) -> str:
    normalized_type = commit_type.lower()
    normalized_scope = scope.lower()
    cleaned_summary = ' '.join(summary.strip().split())

    if normalized_type not in ALLOWED_TYPES:
        raise CommitGateError(f'Unsupported commit type: {commit_type}')
    if not cleaned_summary:
        raise CommitGateError('Commit summary must not be empty.')
    if not SCOPE_PATTERN.fullmatch(normalized_scope):
        raise CommitGateError(
            'Scope must match ^[a-z0-9][a-z0-9_-]*$ to stay automation-friendly.'
        )

    return f'{normalized_type}({normalized_scope}): {cleaned_summary}'


def commit_if_green(
    commit_type: str,
    scope: str,
    summary: str,
    repo_root: Path = REPO_ROOT,
) -> str:
    branch = current_branch(repo_root=repo_root)
    if branch in PROTECTED_BRANCHES:
        raise CommitGateError(f"Refusing to commit directly on protected branch '{branch}'.")
    if branch == 'HEAD':
        raise CommitGateError('Detached HEAD is not allowed for guarded commits.')

    files = staged_files(repo_root=repo_root)
    if not files:
        raise CommitGateError('No staged changes found. Stage files before running commit_if_green.')

    dirty_entries = unexpected_worktree_entries(repo_root=repo_root)
    if dirty_entries:
        formatted = ', '.join(dirty_entries)
        raise CommitGateError(
            'Working tree has unstaged or untracked changes. '
            f'Commit gate requires a clean tree aside from staged files: {formatted}'
        )

    validate_repo.validate_scope(scope='all', repo_root=repo_root)
    message = build_commit_message(commit_type=commit_type, scope=scope, summary=summary)

    completed = run_git(['commit', '-m', message], repo_root=repo_root)
    if completed.returncode != 0:
        raise CommitGateError(completed.stderr.strip() or completed.stdout.strip() or 'git commit failed')

    print(completed.stdout.strip())
    return message


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Commit staged changes only after full-repo validation passes.',
    )
    parser.add_argument('--type', required=True, dest='commit_type', choices=sorted(ALLOWED_TYPES))
    parser.add_argument('--scope', required=True, help='Commit scope, e.g. backend, frontend, docs.')
    parser.add_argument('--summary', required=True, help='Commit summary without the type/scope prefix.')
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        commit_if_green(
            commit_type=args.commit_type,
            scope=args.scope,
            summary=args.summary,
        )
    except (CommitGateError, validate_repo.ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
