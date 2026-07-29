"""domain.py must never import infrastructure.py - modeled on atomicguard's
own architecture test (Bounded-Indeterminacy-Theory.md's G10 example:
domain_never_imports_infrastructure), not invented for this fixture.
"""

import ast
from pathlib import Path

DOMAIN_PATH = Path(__file__).parent.parent.parent / "src" / "example_pkg" / "domain.py"


def test_domain_never_imports_infrastructure():
    tree = ast.parse(DOMAIN_PATH.read_text())

    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    violations = [m for m in imported_modules if "infrastructure" in m]
    assert not violations, f"domain.py imports infrastructure: {violations}"
