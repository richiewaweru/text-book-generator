from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]


class ValidationError(RuntimeError):
    """Raised when one or more validation steps fail."""


@dataclass(frozen=True)
class ValidationStep:
    name: str
    cwd: Path
    command: tuple[str, ...]


@dataclass(frozen=True)
class ValidationResult:
    step: ValidationStep
    returncode: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


def build_steps(scope: str, repo_root: Path = REPO_ROOT) -> list[ValidationStep]:
    normalized_scope = scope.lower()
    backend_steps = [
        ValidationStep(
            name='backend-ruff',
            cwd=repo_root / 'backend',
            command=('uv', 'run', 'ruff', 'check', 'src/', 'tests/'),
        ),
        ValidationStep(
            name='backend-pytest',
            cwd=repo_root / 'backend',
            command=('uv', 'run', 'pytest'),
        ),
    ]
    frontend_steps = [
        ValidationStep(
            name='frontend-check',
            cwd=repo_root / 'frontend',
            command=('npm', 'run', 'check'),
        ),
        ValidationStep(
            name='frontend-build',
            cwd=repo_root / 'frontend',
            command=('npm', 'run', 'build'),
        ),
    ]

    if normalized_scope == 'backend':
        return backend_steps
    if normalized_scope == 'frontend':
        return frontend_steps
    if normalized_scope == 'all':
        return backend_steps + frontend_steps
    raise ValueError(f'Unsupported scope: {scope}')


def run_step(step: ValidationStep) -> ValidationResult:
    executable = step.command[0]
    resolved = shutil.which(executable)
    if resolved is None and sys.platform == "win32":
        for suffix in (".cmd", ".exe", ".bat"):
            resolved = shutil.which(f"{executable}{suffix}")
            if resolved:
                break

    completed = subprocess.run(
        [resolved or executable, *step.command[1:]],
        cwd=step.cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    return ValidationResult(
        step=step,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def format_result(result: ValidationResult) -> str:
    lines = [f"[{result.step.name}] {'PASS' if result.succeeded else 'FAIL'}"]
    if result.stdout.strip():
        lines.append(result.stdout.strip())
    if result.stderr.strip():
        lines.append(result.stderr.strip())
    return '\n'.join(lines)


def validate_scope(scope: str, repo_root: Path = REPO_ROOT) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    failures: list[ValidationResult] = []

    for step in build_steps(scope=scope, repo_root=repo_root):
        print(f"==> Running {step.name}: {' '.join(step.command)}", flush=True)
        result = run_step(step)
        print(format_result(result), flush=True)
        results.append(result)
        if not result.succeeded:
            failures.append(result)

    if failures:
        failure_names = ', '.join(result.step.name for result in failures)
        raise ValidationError(f'Validation failed for: {failure_names}')

    return results


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Run the repository validation suite for backend, frontend, or the full repo.',
    )
    parser.add_argument(
        '--scope',
        choices=['backend', 'frontend', 'all'],
        default='all',
        help='Validation scope to run.',
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_scope(scope=args.scope)
    except (ValidationError, FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
