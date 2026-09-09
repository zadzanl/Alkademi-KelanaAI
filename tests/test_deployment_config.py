"""Regression checks for root-level hosting metadata.

This intentionally does not import the database-backed application. Provider
deployment smoke tests remain a separate, credentialed step.
"""

from pathlib import Path
import re
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeploymentConfigTests(unittest.TestCase):
    def test_fastapi_cloud_entrypoint_and_python_range(self) -> None:
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(config["project"]["requires-python"], ">=3.12,<3.14")
        self.assertEqual(config["tool"]["fastapi"]["entrypoint"], "backend.main:app")

    def test_cloud_dependencies_match_pinned_backend_requirements(self) -> None:
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        cloud_dependencies = set(config["project"]["dependencies"])
        backend_dependencies = {
            line.strip()
            for line in (ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        normalized_cloud = {
            re.sub(r"^fastapi\[standard\]", "fastapi", dependency, flags=re.IGNORECASE)
            for dependency in cloud_dependencies
        }

        self.assertEqual(normalized_cloud, backend_dependencies)
        self.assertIn("fastapi[standard]==0.141.1", cloud_dependencies)

    def test_readme_documents_split_provider_environment_contract(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for variable in (
            "API_URL",
            "AUTH_SESSION_COOKIE",
            "DATABASE_URL",
            "ENVIRONMENT",
            "AUTH_SESSION_TTL_SECONDS",
            "OPENROUTER_API_KEY",
            "OPENROUTER_MODEL",
        ):
            self.assertIn(variable, readme)


if __name__ == "__main__":
    unittest.main()