"""The terminal UI holds no game rules (Constitution III, spec 005 FR-001): from the core it may
import only the facade (`manager_core.api`) and the localisation layer."""

import ast
from pathlib import Path

ALLOWED = {"manager_core.api", "manager_core.i18n"}
SRC = Path(__file__).resolve().parents[1] / "src" / "manager_tui"


def test_ui_imports_only_the_facade() -> None:
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text("utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "manager_core":
                names = [f"manager_core.{a.name}" for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            else:
                continue
            for name in names:
                if name.startswith("manager_core") and name not in ALLOWED:
                    raise AssertionError(f"{path.name} imports {name}")
