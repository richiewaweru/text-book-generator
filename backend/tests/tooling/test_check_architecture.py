from pathlib import Path

from automation.scripts.check_architecture import find_violations


def test_architecture_guard_passes_current_repo():
    repo_root = Path(__file__).resolve().parents[3]
    violations = find_violations(repo_root=repo_root)
    assert violations == []


def test_architecture_guard_detects_forbidden_domain_import(tmp_path: Path):
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

    violations = find_violations(repo_root=tmp_path)

    assert len(violations) == 1
    violation = violations[0]
    assert violation.source_layer == 'domain'
    assert violation.target_layer == 'infrastructure'
    assert violation.line == 1
