"""Regression alias for the repaired financial/deletion/component boundaries.

The original failure observations are preserved in the 2026-10-23 audit report.
Run from the bench sites directory; fixtures are restricted to local QA.
"""
from pathlib import Path
import runpy
import sys

if __name__ == '__main__':
    sys.argv=[sys.argv[0],'qa.localhost','--components']
    runpy.run_path(str(Path(__file__).with_name('audit-workflows.py')),run_name='__main__')
