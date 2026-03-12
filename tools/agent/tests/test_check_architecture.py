from pathlib import Path

import yaml

from tools.agent.check_architecture import find_violations


def write_context(repo_root: Path) -> Path:
    docs_root = repo_root / 'docs' / 'project'
    docs_root.mkdir(parents=True)
    context_path = docs_root / 'context-summary.yaml'
    payload = {
        'repo': {
            'name': 'Test Repo',
            'default_branch': 'main',
            'protected_branches': ['main'],
        },
        'stack': {
            'python': {'working_directory': 'backend', 'install_command': 'uv sync --all-extras'},
            'frontend': {'working_directory': 'frontend', 'install_command': 'npm ci'},
        },
        'validation': {'scopes': {'all': {'include_scopes': []}}},
        'architecture': {
            'strategy': {
                'type': 'import-layer',
                'name': 'layers',
                'report_name': 'test-guard',
                'package_root': 'backend/src/textbook_agent',
                'module_prefix': 'textbook_agent',
                'layers': {
                    'domain': {'forbidden': ['application', 'infrastructure', 'interface']},
                    'application': {'forbidden': ['infrastructure', 'interface']},
                    'infrastructure': {'forbidden': ['application', 'interface']},
                    'interface': {'forbidden': []},
                },
            }
        },
        'github': {'required_checks': ['agent-governance'], 'pr_required_sections': ['Summary']},
        'release': {
            'current_version': '0.1.0',
            'tag_pattern': 'v*',
            'changelog_path': 'CHANGELOG.md',
        },
        'agent_policy': {
            'allowed_commit_types': ['feat'],
            'stage_packs': ['bootstrap'],
        },
        'docs': {'live_root': 'docs/project', 'run_root': 'docs/project/runs', 'local_context_docs': []},
        'process_packs': {
            'bootstrap-setup': {
                'template': 'setup-runbook',
                'variant': 'full',
                'steps': [{'id': 'one', 'title': 'One'}],
            }
        },
    }
    context_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding='utf-8')
    return context_path


def test_architecture_guard_passes_current_repo():
    repo_root = Path(__file__).resolve().parents[3]
    context_path = repo_root / 'docs' / 'project' / 'context-summary.yaml'

    violations = find_violations(context_path=context_path, repo_root=repo_root)

    assert violations == []


def test_architecture_guard_detects_forbidden_domain_import(tmp_path: Path):
    context_path = write_context(tmp_path)
    package_root = tmp_path / 'backend' / 'src' / 'textbook_agent'
    (package_root / 'domain' / 'services').mkdir(parents=True)
    (package_root / 'infrastructure' / 'config').mkdir(parents=True)

    (package_root / 'domain' / 'services' / 'bad.py').write_text(
        'from textbook_agent.infrastructure.config.settings import Settings\n',
        encoding='utf-8',
    )
    (package_root / 'infrastructure' / 'config' / 'settings.py').write_text(
        'class Settings:\n    pass\n',
        encoding='utf-8',
    )

    violations = find_violations(context_path=context_path, repo_root=tmp_path)

    assert len(violations) == 1
    violation = violations[0]
    assert violation.source_layer == 'domain'
    assert violation.target_layer == 'infrastructure'
    assert violation.line == 1
