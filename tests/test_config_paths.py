"""Evaluate the actual dotenv setting for both repository and Docker layouts."""
import ast
from pathlib import Path, PurePosixPath

import pytest
import config


class ResolvedPosixPath(PurePosixPath):
    def resolve(self):
        return self


@pytest.mark.parametrize("filename, expected", [
    ("/app/config.py", (".env",)),
    ("/config.py", (".env",)),
    ("/repo/apps/api/config.py", ("/repo/.env", ".env")),
])
def test_dotenv_setting_handles_container_and_monorepo(filename, expected):
    tree = ast.parse(Path(config.__file__).read_text(encoding="utf-8"))
    settings = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Settings")
    call = next(node.value for node in settings.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "model_config" for target in node.targets))
    expression = next(keyword.value for keyword in call.keywords if keyword.arg == "env_file")
    namespace = {**vars(config), "Path": ResolvedPosixPath, "__file__": filename}
    result = eval(compile(ast.Expression(expression), "<dotenv setting>", "eval"), namespace)
    assert result == expected
