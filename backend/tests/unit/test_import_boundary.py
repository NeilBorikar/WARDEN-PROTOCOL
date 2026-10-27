"""Automated Import Boundary Test.

WHY:
- Principle P1: "AI proposes, deterministic code decides. The packages mandate/,
  policy/ and audit/ must never import LLM or agent code. Enforce with an
  automated import-boundary test."
- This test inspects the AST of all source files in mandate/, policy/, and audit/
  to guarantee zero prohibited imports at compile/test time.
"""

from __future__ import annotations

import ast
from pathlib import Path

PROHIBITED_MODULE_PREFIXES = (
    "app.llm",
    "app.agents",
    "llm",
    "agents",
    "openai",
    "anthropic",
    "google.generativeai",
    "langchain",
)

PROTECTED_PACKAGES = ("mandate", "policy", "audit")


def test_import_boundary_enforced() -> None:
    """Enforce Principle P1: mandate/, policy/, and audit/ never import LLM or agent code."""
    backend_app_dir = Path(__file__).resolve().parents[2] / "app"

    violations: list[str] = []

    for pkg_name in PROTECTED_PACKAGES:
        pkg_dir = backend_app_dir / pkg_name
        assert pkg_dir.exists(), f"Protected package directory {pkg_dir} must exist."

        for py_file in pkg_dir.rglob("*.py"):
            with open(py_file, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))

            for node in ast.walk(tree):
                # Check 'import foo'
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for prohibited in PROHIBITED_MODULE_PREFIXES:
                            if alias.name == prohibited or alias.name.startswith(prohibited + "."):
                                violations.append(
                                    f"{py_file.name}:{node.lineno}: Prohibited import '{alias.name}'"
                                )

                # Check 'from foo import bar'
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for prohibited in PROHIBITED_MODULE_PREFIXES:
                            if node.module == prohibited or node.module.startswith(
                                prohibited + "."
                            ):
                                violations.append(
                                    f"{py_file.name}:{node.lineno}: Prohibited from-import '{node.module}'"
                                )

    assert not violations, (
        "VIOLATION OF PRINCIPLE P1: Protected packages imported prohibited modules:\n"
        + "\n".join(violations)
    )
