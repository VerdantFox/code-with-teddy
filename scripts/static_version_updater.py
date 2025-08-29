"""static_version_updater: Updates the static version numbers in the HTML templates."""

import hashlib
import sys
from pathlib import Path


def get_file_hash(file_path: Path) -> str:
    """Get SHA256 hash of a file's contents."""
    with file_path.open("rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def get_combined_hash(file_paths: list[Path]) -> str:
    """Get combined hash of multiple files."""
    combined_content = b""
    for file_path in sorted(file_paths):  # Sort for consistent ordering
        if file_path.exists():
            with file_path.open("rb") as f:
                combined_content += f.read()
        else:
            msg = f"Required file not found: {file_path}"
            raise FileNotFoundError(msg)

    return hashlib.sha256(combined_content).hexdigest()[:8]  # Short hash


def discover_files(
    base_dir: Path,
    extensions: list[str],
    exclude_dirs: list[str] | None = None,
    exclude_files: list[str] | None = None,
) -> list[Path]:
    """Discover files with given extensions in a directory, excluding specified dirs/files."""
    if exclude_dirs is None:
        exclude_dirs = []
    if exclude_files is None:
        exclude_files = []

    files = []
    for ext in extensions:
        for file_path in base_dir.rglob(f"*.{ext}"):
            # Check if file is in an excluded directory
            if any(exclude_dir in file_path.parts for exclude_dir in exclude_dirs):
                continue
            # Check if file is in the excluded files list
            if file_path.name in exclude_files:
                continue
            files.append(file_path)

    return sorted(files)  # Sort for consistent ordering


def get_tailwind_version() -> str | None:
    """Get version hash for tailwind static files.

    Returns:
        Version hash if tailwind file exists, None otherwise.

    """
    project_root = Path(__file__).parent.parent
    tailwind_file = project_root / "app/web/html/static/css/tailwind-styles.css"

    if not tailwind_file.exists():
        return None

    return get_file_hash(tailwind_file)[:8]


def get_libraries_version() -> str:
    """Get version hash for library static files."""
    project_root = Path(__file__).parent.parent

    # CSS libraries
    css_libs_dir = project_root / "app/web/html/static/css/libraries"
    css_files = discover_files(css_libs_dir, ["css"])

    # JS libraries
    js_libs_dir = project_root / "app/web/html/static/js/libraries"
    js_files = discover_files(js_libs_dir, ["js"])

    all_files = css_files + js_files
    if not all_files:
        msg = "No library files found"
        raise FileNotFoundError(msg)

    return get_combined_hash(all_files)


def get_custom_version() -> str:
    """Get version hash for custom static files."""
    project_root = Path(__file__).parent.parent

    # Custom JS files
    js_custom_dir = project_root / "app/web/html/static/js/custom"
    js_files = discover_files(js_custom_dir, ["js"])

    # Custom CSS files (excluding libraries and tailwind)
    css_dir = project_root / "app/web/html/static/css"
    css_files = discover_files(
        css_dir, ["css"], exclude_dirs=["libraries"], exclude_files=["tailwind-styles.css"]
    )

    all_files = js_files + css_files
    if not all_files:
        msg = "No custom files found"
        raise FileNotFoundError(msg)

    return get_combined_hash(all_files)


def get_current_versions_from_template() -> dict[str, str]:
    """Extract current version hashes from the base template."""
    project_root = Path(__file__).parent.parent
    base_template = project_root / "app/web/html/templates/shared/base.html"

    if not base_template.exists():
        msg = f"Base template not found: {base_template}"
        raise FileNotFoundError(msg)

    current_versions = {}
    with base_template.open("r") as f:
        content = f.read()

    lines = content.splitlines()
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith("{% set libraries_static_version ="):
            # Extract version between quotes: {% set libraries_static_version = 'hash' %}
            version = stripped_line.split("=")[1].strip().rstrip(" %}").strip("'\"")
            current_versions["libraries"] = version
        elif stripped_line.startswith("{% set custom_static_version ="):
            version = stripped_line.split("=")[1].strip().rstrip(" %}").strip("'\"")
            current_versions["custom"] = version
        elif stripped_line.startswith("{% set tailwind_static_version ="):
            version = stripped_line.split("=")[1].strip().rstrip(" %}").strip("'\"")
            current_versions["tailwind"] = version

    return current_versions


def _get_all_versions() -> tuple[dict[str, str], dict[str, str]]:
    """Get current and new version hashes for all static file types.

    Returns:
        Tuple of (current_versions, new_versions) dictionaries.

    """
    current_versions = get_current_versions_from_template()
    tailwind_version = get_tailwind_version()
    libraries_version = get_libraries_version()
    custom_version = get_custom_version()

    new_versions = {
        "libraries": libraries_version,
        "custom": custom_version,
    }

    # Only include tailwind version if the file exists
    if tailwind_version is not None:
        new_versions["tailwind"] = tailwind_version

    return current_versions, new_versions


def _check_version_changes(
    current_versions: dict[str, str], new_versions: dict[str, str]
) -> tuple[bool, list[str]]:
    """Check if any versions have changed.

    Args:
        current_versions: Current version hashes from template
        new_versions: New version hashes from files

    Returns:
        Tuple of (versions_changed, changed_versions_list)

    """
    versions_changed = False
    changed_versions = []

    for version_type, new_hash in new_versions.items():
        current_hash = current_versions.get(version_type, "")
        if current_hash != new_hash:
            versions_changed = True
            changed_versions.append(f"{version_type}: {current_hash} -> {new_hash}")

    return versions_changed, changed_versions


def _update_template_content(base_template: Path, new_versions: dict[str, str]) -> None:
    """Update the version lines in the base template file.

    Args:
        base_template: Path to the base template file
        new_versions: Dictionary of new version hashes

    """
    # Read the current template
    with base_template.open("r") as f:
        content = f.read()

    # Update the version lines
    lines = content.splitlines()
    libraries_version = new_versions["libraries"]
    custom_version = new_versions["custom"]
    tailwind_version = new_versions.get("tailwind")

    for i, line in enumerate(lines):
        if line.strip().startswith("{% set libraries_static_version ="):
            lines[i] = f"{{% set libraries_static_version = '{libraries_version}' %}}"
        elif line.strip().startswith("{% set custom_static_version ="):
            lines[i] = f"{{% set custom_static_version = '{custom_version}' %}}"
        elif (
            line.strip().startswith("{% set tailwind_static_version =")
            and tailwind_version is not None
        ):
            lines[i] = f"{{% set tailwind_static_version = '{tailwind_version}' %}}"
    lines.append("")  # Ensure file ends with a newline

    # Write the updated content
    with base_template.open("w") as f:
        f.write("\n".join(lines))


def _print_version_results(
    *,
    versions_changed: bool,
    changed_versions: list[str],
    new_versions: dict[str, str],
) -> None:
    """Print the results of version checking and updating.

    Args:
        versions_changed: Whether any versions changed
        changed_versions: List of version change descriptions
        new_versions: Dictionary of new version hashes

    """
    tailwind_version = new_versions.get("tailwind")
    libraries_version = new_versions["libraries"]
    custom_version = new_versions["custom"]

    if versions_changed:
        print("Static file versions have changed:")
        for change in changed_versions:
            print(f"  {change}")
        print("\nUpdated static versions:")
    else:
        print("No static file changes detected. Versions remain the same:")

    # Print version information
    if tailwind_version is not None:
        print(f"  tailwind_static_version: {tailwind_version}")
    else:
        print("  tailwind_static_version: (not updated - file not found)")
    print(f"  libraries_static_version: {libraries_version}")
    print(f"  custom_static_version: {custom_version}")


def update_base_template() -> bool:
    """Update the static version variables in base.html template.

    Returns:
        True if any versions changed, False otherwise.

    """
    project_root = Path(__file__).parent.parent
    base_template = project_root / "app/web/html/templates/shared/base.html"

    if not base_template.exists():
        msg = f"Base template not found: {base_template}"
        raise FileNotFoundError(msg)

    # Get current and new version hashes
    current_versions, new_versions = _get_all_versions()

    # Check if any versions changed
    versions_changed, changed_versions = _check_version_changes(current_versions, new_versions)

    # Update the template file
    _update_template_content(base_template, new_versions)

    # Print results
    _print_version_results(
        versions_changed=versions_changed,
        changed_versions=changed_versions,
        new_versions=new_versions,
    )

    return versions_changed


def main() -> None:
    """Update static versions in base template."""
    try:
        versions_changed = update_base_template()
        if versions_changed:
            print("\nStatic file versions have changed. Please commit the updated base.html file.")
            sys.exit(1)  # Exit with non-zero code for pre-commit hooks
        else:
            print("Static version update completed successfully!")
            sys.exit(0)
    except (FileNotFoundError, OSError) as e:
        print(f"Error updating static versions: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
