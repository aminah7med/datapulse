from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_core_package_boundaries_exist() -> None:
    package_root = PROJECT_ROOT / "src" / "datapulse"
    expected_packages = {
        "config",
        "incidents",
        "ingestion",
        "quality",
        "storage",
        "transformation",
        "validation",
    }

    assert {path.name for path in package_root.iterdir() if path.is_dir()} == expected_packages
    assert (package_root / "__init__.py").is_file()
    assert all((package_root / name / "__init__.py").is_file() for name in expected_packages)
