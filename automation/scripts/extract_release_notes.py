from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG_PATH = REPO_ROOT / 'CHANGELOG.md'


def extract_release_notes(version: str, changelog_path: Path = CHANGELOG_PATH) -> str:
    target_heading = f'## [{version.removeprefix("v")}]'
    lines = changelog_path.read_text(encoding='utf-8').splitlines()

    collecting = False
    collected: list[str] = []
    for line in lines:
        if line.startswith('## ['):
            if line.startswith(target_heading):
                collecting = True
                collected.append(line)
                continue
            if collecting:
                break
        elif collecting:
            collected.append(line)

    if not collected:
        raise ValueError(f'No changelog section found for version {version}')

    return '\n'.join(collected).strip() + '\n'


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Extract a version section from CHANGELOG.md.')
    parser.add_argument('--version', required=True, help='Release tag, e.g. v0.1.0')
    parser.add_argument('--output', help='Optional output file path.')
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        notes = extract_release_notes(args.version)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.output:
        Path(args.output).write_text(notes, encoding='utf-8')
    else:
        print(notes)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
