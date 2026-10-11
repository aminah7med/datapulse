
import argparse
import csv
from pathlib import Path
from datetime import UTC, datetime

def profile_csv(path: Path) -> dict:
    """Profile a CSV file without loading all rows into memory."""

    result = {
        "name": path.name,
        "size_bytes": path.stat().st_size,
        "encoding": "utf-8-sig",
        "columns": [],
        "row_count": 0,
        "blank_counts": [],
        "malformed_rows": 0,
        "error": None,
    }

    try:
        # Detect the text encoding using a small sample.
        with path.open("rb") as file:
            sample_bytes = file.read(65536)

        try:
            sample_bytes.decode("utf-8-sig")
            encoding = "utf-8-sig"
        except UnicodeDecodeError:
            encoding = "cp1252"

        result["encoding"] = encoding

        # Use explicit CSV settings instead of guessing the dialect.
        with path.open(
            "r",
            encoding=encoding,
            newline="",
        ) as file:
            reader = csv.reader(
                file,
                delimiter=",",
                quotechar='"',
                doublequote=True,
                strict=True,
            )

            columns = next(reader, None)

            if not columns or not any(c.strip() for c in columns):
                result["error"] = "Missing or empty CSV header."
                return result

            result["columns"] = columns
            result["blank_counts"] = [0] * len(columns)

            for row in reader:
                result["row_count"] += 1

                if len(row) != len(columns):
                    result["malformed_rows"] += 1

                for index in range(len(columns)):
                    value = row[index] if index < len(row) else ""

                    if not value.strip():
                        result["blank_counts"][index] += 1

    except (OSError, UnicodeError, csv.Error) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    return result


def write_report(profiles: list, output: Path, raw_dir: Path) -> None:
    """Write profiling results to a Markdown report."""

    lines = [
        "# DataPulse — Dataset Profile",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Source directory: `{raw_dir}`",
        "",
    ]

    if not profiles:
        lines.extend([
            "No CSV files found.",
            "",
        ])

    for item in profiles:
        lines.extend([
            f"## {item['name']}",
            "",
            f"- File size: {item['size_bytes'] / (1024 ** 2):.2f} MiB",
            f"- Encoding: `{item['encoding']}`",
            f"- Rows: {item['row_count']:,}",
            f"- Columns: {len(item['columns'])}",
            f"- Rows with inconsistent field counts: {item['malformed_rows']:,}",
            "",
        ])

        if item["columns"]:
            lines.append("### Columns and blank values")
            lines.append("")

            for name, count in zip(
                item["columns"], item["blank_counts"]
            ):
                lines.append(f"- `{name}`: {count:,} blank values")

            lines.append("")

        if item["error"]:
            lines.extend([
                f"**Processing error:** `{item['error']}`",
                "",
            ])

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Report saved to: {output}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Profile CSV datasets for DataPulse."
    )
    parser.add_argument(
        "--raw-dir", type=Path, default=Path("data/raw")
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("docs/dataset-profile.md")
    )
    args = parser.parse_args()

    if not args.raw_dir.is_dir():
        parser.error(f"Directory does not exist: {args.raw_dir}")

    csv_files = sorted(args.raw_dir.glob("*.csv"))

    profiles = [profile_csv(path) for path in csv_files]
    write_report(profiles, args.output, args.raw_dir)

    failed = [
        item for item in profiles if item["error"]
    ]

    print(f"Files profiled: {len(profiles)}")
    print(f"Files with errors: {len(failed)}")

    return 1 if not profiles or failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
