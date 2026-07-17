from importlib.metadata import version


def installed_distribution_version(package_name: str) -> str:
    """Read one installed distribution version without shelling out."""

    return version(package_name)
