"""update_pre_commit_add_deps: Update pre-commit config additional dependencies."""

from pathlib import Path
from typing import Any

import yaml


class DependencyUpdater:
    """Update pre-commit config additional dependencies."""

    def __init__(self) -> None:
        self.pre_commit_file = Path(__file__).parent.parent / ".pre-commit-config.yaml"
        self.pre_commit_text = self.pre_commit_file.read_text()
        self.dev_requirements_file = Path(__file__).parent.parent / "requirements-dev.txt"
        self.config = self.load_config()
        # dynamic vars
        self.pre_commit_deps: dict[str, str] = {}
        self.dev_deps: dict[str, str] = {}
        self.deps_to_update: dict[str, str] = {}

    def main(self) -> None:
        """Run main function."""
        print("Updating pre-commit config additional dependencies...")
        self.get_pre_commit_additional_dependencies()
        self.get_dev_requirements()
        self.get_deps_needing_update()
        self.update_pre_commit_config()

    def load_config(self) -> dict[str, Any]:
        """Load pre-commit config."""
        with self.pre_commit_file.open() as file_:
            return yaml.safe_load(file_)

    def get_pre_commit_additional_dependencies(self) -> None:
        """Get additional dependencies from pre-commit config."""
        dependencies: list[str] = []
        for repo in self.config["repos"]:
            for hook in repo["hooks"]:
                if "additional_dependencies" in hook:
                    dependencies.extend(hook["additional_dependencies"])
        dependencies_filtered = (dep.split("==") for dep in dependencies if "==" in dep)
        self.pre_commit_deps = {
            name.strip(): version.strip() for name, version in dependencies_filtered
        }

    def get_dev_requirements(self) -> None:
        """Get dev requirements from dev-requirements.txt."""
        lines = self.dev_requirements_file.read_text().split("\n")

        for line in lines:
            if "==" in line:
                name, version = line.strip().split("==")
                self.dev_deps[name.strip()] = version.strip(" \\")

    def get_deps_needing_update(self) -> None:
        """Get dependencies that need to be updated."""
        for name, version in self.pre_commit_deps.items():
            if name in self.dev_deps and self.dev_deps[name] != version:
                self.deps_to_update[name] = version

    def update_pre_commit_config(self) -> None:
        """Update pre-commit config."""
        for name, version in self.deps_to_update.items():
            self.pre_commit_text = self.pre_commit_text.replace(
                f"{name}=={version}", f"{name}=={self.dev_deps[name]}"
            )
        self.pre_commit_file.write_text(self.pre_commit_text)


if __name__ == "__main__":
    updater = DependencyUpdater()
    updater.main()
