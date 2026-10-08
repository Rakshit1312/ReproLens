import csv
from pathlib import Path


def build_features(csv_path: str | Path) -> list[dict]:
    """
    Convert raw development/CI environment information
    into structured ReproLens features.

    Difference features describe whether Dev and CI differ.
    Compatibility features describe whether the CI environment
    is compatible with the project requirements.
    """

    csv_path = Path(csv_path)

    with csv_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    features = []

    for row in rows:
        runtime_mismatch = (
            row["runtime_dev"] != row["runtime_ci"]
        )

        dependency_mismatch = (
            row["dependency_dev"] != row["dependency_ci"]
        )

        os_mismatch = (
            row["os_dev"] != row["os_ci"]
        )

        config_mismatch = (
            row["config_dev"] != row["config_ci"]
        )

        resource_mismatch = (
            row["resource_dev"] != row["resource_ci"]
        )

        features.append(
            {
                "id": row["id"],
                "project": row["project"],

                # Environment difference features
                "runtime_mismatch": int(runtime_mismatch),
                "dependency_mismatch": int(dependency_mismatch),
                "os_mismatch": int(os_mismatch),
                "config_mismatch": int(config_mismatch),
                "resource_mismatch": int(resource_mismatch),

                # Compatibility features
                "runtime_compatible": int(
                    row["runtime_compatible"]
                ),
                "dependency_compatible": int(
                    row["dependency_compatible"]
                ),
                "os_compatible": int(
                    row["os_compatible"]
                ),
                "config_compatible": int(
                    row["config_compatible"]
                ),
                "resource_sufficient": int(
                    row["resource_sufficient"]
                ),

                # Ground-truth target
                "environment_failure": int(
                    row["environment_failure"]
                ),
            }
        )

    return features


if __name__ == "__main__":
    data = build_features(
        "data/experiments/environment_failures.csv"
    )

    for row in data:
        print(row)