from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / 'backend' / 'src' / 'textbook_agent'
PACKAGE_NAME = 'textbook_agent'

FORBIDDEN_DEPENDENCIES = {
    'domain': {'application', 'infrastructure', 'interface'},
    'application': {'infrastructure', 'interface'},
    'infrastructure': {'application', 'interface'},
    'interface': set(),
}


@dataclass(frozen=True)
class ArchitectureViolation:
    file_path: str
    line: int
    source_layer: str
    target_layer: str
    import_path: str
    reason: str


def module_name_for_file(file_path: Path, package_root: Path) -> str:
    relative = file_path.relative_to(package_root).with_suffix('')
    parts = [PACKAGE_NAME, *relative.parts]
    if parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(parts)


def layer_for_module(module_name: str) -> str | None:
    parts = module_name.split('.')
    if len(parts) < 2 or parts[0] != PACKAGE_NAME:
        return None
    return parts[1]


def resolve_import(current_module: str, module_name: str | None, level: int) -> str | None:
    if level == 0:
        return module_name

    current_package_parts = current_module.split('.')[:-1]
    trim = level - 1
    if trim > len(current_package_parts):
        return None

    base_parts = current_package_parts[: len(current_package_parts) - trim]
    if module_name:
        return '.'.join([*base_parts, *module_name.split('.')])
    return '.'.join(base_parts)


def extract_internal_imports(file_path: Path, package_root: Path) -> list[tuple[int, str]]:
    tree = ast.parse(file_path.read_text(encoding='utf-8'), filename=str(file_path))
    current_module = module_name_for_file(file_path, package_root)
    imports: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(f'{PACKAGE_NAME}.'):
                    imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            resolved = resolve_import(current_module, node.module, node.level)
            if resolved and (resolved == PACKAGE_NAME or resolved.startswith(f'{PACKAGE_NAME}.')):
                imports.append((node.lineno, resolved))

    return imports


def find_violations(repo_root: Path = REPO_ROOT) -> list[ArchitectureViolation]:
    package_root = repo_root / 'backend' / 'src' / PACKAGE_NAME
    violations: list[ArchitectureViolation] = []

    for file_path in sorted(package_root.rglob('*.py')):
        source_layer = layer_for_module(module_name_for_file(file_path, package_root))
        if source_layer not in FORBIDDEN_DEPENDENCIES:
            continue

        for line, import_path in extract_internal_imports(file_path, package_root):
            target_layer = layer_for_module(import_path)
            if target_layer in FORBIDDEN_DEPENDENCIES[source_layer]:
                reason = (
                    f'{source_layer} layer must not import {target_layer} layer '
                    f'modules directly.'
                )
                violations.append(
                    ArchitectureViolation(
                        file_path=str(file_path.relative_to(repo_root)).replace('\\', '/'),
                        line=line,
                        source_layer=source_layer,
                        target_layer=target_layer,
                        import_path=import_path,
                        reason=reason,
                    )
                )

    return violations


def render_text(violations: list[ArchitectureViolation]) -> str:
    if not violations:
        return 'No architecture violations found.'

    lines = ['Architecture violations detected:']
    for violation in violations:
        lines.append(
            (
                f'- {violation.file_path}:{violation.line} '
                f'[{violation.source_layer}->{violation.target_layer}] '
                f'{violation.import_path}: {violation.reason}'
            )
        )
    return '\n'.join(lines)


def render_markdown(violations: list[ArchitectureViolation]) -> str:
    lines = ['## Architecture Guard']
    if not violations:
        lines.append('')
        lines.append('No architecture violations found.')
        return '\n'.join(lines)

    lines.extend(['', '| File | Line | Violation |', '| --- | ---: | --- |'])
    for violation in violations:
        message = (
            f'`{violation.source_layer}` imported `{violation.target_layer}` via '
            f'`{violation.import_path}`'
        )
        lines.append(f"| `{violation.file_path}` | {violation.line} | {message} |")
    return '\n'.join(lines)


def render_sarif(violations: list[ArchitectureViolation]) -> str:
    results = []
    for violation in violations:
        results.append(
            {
                'level': 'error',
                'message': {'text': violation.reason},
                'locations': [
                    {
                        'physicalLocation': {
                            'artifactLocation': {'uri': violation.file_path},
                            'region': {'startLine': violation.line},
                        }
                    }
                ],
                'properties': asdict(violation),
            }
        )

    payload = {
        'version': '2.1.0',
        'runs': [
            {
                'tool': {
                    'driver': {
                        'name': 'textbook-agent-architecture-guard',
                        'informationUri': 'https://github.com/',
                        'rules': [
                            {
                                'id': 'ddd-layer-boundary',
                                'name': 'DDD layer boundary',
                                'shortDescription': {
                                    'text': 'Enforce repository layer import rules.'
                                },
                            }
                        ],
                    }
                },
                'results': results,
            }
        ],
    }
    return json.dumps(payload, indent=2)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Validate DDD layer boundaries for the backend package.',
    )
    parser.add_argument(
        '--format',
        choices=['text', 'markdown', 'sarif'],
        default='text',
        help='Output format.',
    )
    parser.add_argument(
        '--root',
        default=str(REPO_ROOT),
        help='Repository root to scan.',
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(args.root).resolve()
    violations = find_violations(repo_root=repo_root)

    if args.format == 'markdown':
        print(render_markdown(violations))
    elif args.format == 'sarif':
        print(render_sarif(violations))
    else:
        print(render_text(violations))

    return 1 if violations else 0


if __name__ == '__main__':
    raise SystemExit(main())
