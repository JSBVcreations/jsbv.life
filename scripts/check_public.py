#!/usr/bin/env python3
"""Check everything the public repo would publish for things that must never leave the Mac (rules: CLAUDE.md).

    python3 scripts/check_public.py           check every file git would commit; exit 1 on a problem
    python3 scripts/check_public.py FILE...   check only these (repo-relative paths)

Run by update.py after every build. Rules and known false positives: scripts/config/public-check.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.privacy import check_public, report  # noqa: E402

problems = check_public(sys.argv[1:] or None)
if problems:
    print(f'PRIVACY CHECK: {len(problems)} problem{"" if len(problems) == 1 else "s"} in public files. Nothing is wrong until you commit; fix or allow these first.')
    print(report(problems))
    sys.exit(1)
print('privacy check: clean')
