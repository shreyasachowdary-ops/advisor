"""Test isolation (DECISIONS.md DEC-034).

AUDIT_DIR is set before any app module is imported, so both this process's settings
and every MCP server subprocess (which inherits the environment) write feedback and
safeguarding test events to a temp folder, never to backend/data/audit.
"""

import os
import shutil
import tempfile

_AUDIT_TMP = tempfile.mkdtemp(prefix="advisor-test-audit-")
os.environ["AUDIT_DIR"] = _AUDIT_TMP


def pytest_unconfigure(config):
    shutil.rmtree(_AUDIT_TMP, ignore_errors=True)
