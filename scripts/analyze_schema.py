"""Analyze CSV schemas, candidate keys, and foreign-key relationships."""

import argparse
import csv
import json
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

CUSTOMERS = "olist_customers_dataset.csv"
ORDERS = "olist_orders_dataset.csv"
ORDER_ITEMS = "olist_order_items_dataset.csv"
ORDER_PAYMENTS = "olist_order_payments_dataset.csv"
ORDER_REVIEWS = "olist_order_reviews_dataset.csv"
PRODUCTS = "olist_products_dataset.csv"
SELLERS = "olist_sellers_dataset.csv"
TRANSLATIONS = "product_category_name_translation.csv"
GEOLOCATION = "olist_geolocation_dataset.csv"

DATASET_LABELS = {
    CUSTOMERS: "customers",
    ORDERS: "orders",
    ORDER_ITEMS: "order_items",
    ORDER_PAYMENTS: "order_payments",
    ORDER_REVIEWS: "order_reviews",
    PRODUCTS: "products",
    SELLERS: "sellers",
    TRANSLATIONS: "product_category_name_translation",
    GEOLOCATION: "geolocation",
}

REQUIRED_DATASETS = set(DATASET_LABELS)

KEY_FIELDS = {
    CUSTOMERS: [("customer_id", ("customer_id",), False)],
    ORDERS: [("order_id", ("order_id",), False)],
    ORDER_ITEMS: [
        ("order_id + order_item_id", ("order_id", "order_item_id"), False)
    ],
    ORDER_PAYMENTS: [
        (
            "order_id + payment_sequential",
            ("order_id", "payment_sequential"),
            False,
        )
    ],
    PRODUCTS: [("product_id", ("product_id",), False)],
    SELLERS: [("seller_id", ("seller_id",), False)],
    TRANSLATIONS: [
        ("product_category_name", ("product_category_name",), False)
    ],
    ORDER_REVIEWS: [("review_id", ("review_id",), True)],
    GEOLOCATION: [
        ("geolocation_zip_code_prefix", ("geolocation_zip_code_prefix",), True),
        (
            "ZIP prefix + latitude + longitude",
            (
                "geolocation_zip_code_prefix",
                "geolocation_lat",
                "geolocation_lng",
            ),
            True,
        ),
        ("all columns (exact row)", None, True),
    ],
}

RELATIONSHIP_SPECS = (
    ("orders.customer_id", ORDERS, "customer_id", CUSTOMERS, "customer_id"),
    ("order_items.order_id", ORDER_ITEMS, "order_id", ORDERS, "order_id"),
    ("order_items.product_id", ORDER_ITEMS, "product_id", PRODUCTS, "product_id"),
    ("order_items.seller_id", ORDER_ITEMS, "seller_id", SELLERS, "seller_id"),
    (
        "order_payments.order_id",
        ORDER_PAYMENTS,
        "order_id",
        ORDERS,
        "order_id",
    ),
    (
        "order_reviews.order_id",
        ORDER_REVIEWS,
        "order_id",
        ORDERS,
        "order_id",
    ),
    (
        "products.product_category_name",
        PRODUCTS,
        "product_category_name",
        TRANSLATIONS,
        "product_category_name",
    ),
)


class AnalysisError(Exception):
    """Raised when an input CSV cannot be analyzed reliably."""


@dataclass
class DatasetProfile:
    filename: str
    columns: list[str]
    row_count: int = 0
    null_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class CandidateKeyResult:
    dataset: str
    label: str
    columns: tuple[str, ...]
    investigative: bool
    null_key_rows: int = 0
    duplicate_rows: int = 0
    unique_keys: int = 0


@dataclass
class RelationshipResult:
    label: str
    source_dataset: str
    source_column: str
    target_dataset: str
    target_column: str
    row_count: int = 0
    null_key_rows: int = 0
    orphan_rows: int = 0


@dataclass
class SchemaAnalysis:
    datasets: list[DatasetProfile]
    candidate_keys: list[CandidateKeyResult]
    relationships: list[RelationshipResult]


def _is_null(value: str) -> bool:
    return not value.strip()


def _read_csv(path: Path):
    """Yield a validated header followed by rows from a CSV file."""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source, strict=True)
            header = next(reader, None)
            if not header or not any(column.strip() for column in header):
                raise AnalysisError(f"{path}: missing or empty CSV header")
            if any(not column.strip() for column in header):
                raise AnalysisError(f"{path}: CSV header contains an empty column name")
            if len(set(header)) != len(header):
                raise AnalysisError(f"{path}: CSV header contains duplicate column names")

            yield header
            for record_number, row in enumerate(reader, start=2):
                if len(row) != len(header):
                    raise AnalysisError(
                        f"{path}: malformed record {record_number} "
                        f"(physical line {reader.line_num}); expected "
                        f"{len(header)} fields, found {len(row)}"
                    )
                yield row
    except AnalysisError:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise AnalysisError(f"{path}: {type(exc).__name__}: {exc}") from exc


def _candidate_results(
    filename: str, columns: list[str]
) -> list[CandidateKeyResult]:
    results = []
    for label, configured_columns, investigative in KEY_FIELDS.get(filename, []):
        key_columns = tuple(columns) if configured_columns is None else configured_columns
        missing = [column for column in key_columns if column not in columns]
        if missing:
            raise AnalysisError(
                f"{filename}: candidate key {label!r} refers to missing "
                f"column(s): {', '.join(missing)}"
            )
        results.append(
            CandidateKeyResult(
                dataset=DATASET_LABELS[filename],
                label=label,
                columns=key_columns,
                investigative=investigative,
            )
        )
    return results


def analyze_schema(raw_dir: Path) -> SchemaAnalysis:
    """Analyze all CSV files under *raw_dir* without changing them."""
    if not raw_dir.is_dir():
        raise AnalysisError(f"Source directory does not exist: {raw_dir}")

    paths = sorted(raw_dir.rglob("*.csv"))
    if not paths:
        raise AnalysisError(f"No CSV files found under: {raw_dir}")

    paths_by_name = {}
    for path in paths:
        if path.name in paths_by_name:
            raise AnalysisError(
                f"Multiple CSV files have the same name: {path.name}"
            )
        paths_by_name[path.name] = path

    missing_files = sorted(REQUIRED_DATASETS - paths_by_name.keys())
    if missing_files:
        raise AnalysisError(
            "Required dataset file(s) not found under "
            f"{raw_dir}: {', '.join(missing_files)}"
        )

    profiles: list[DatasetProfile] = []
    candidate_keys: list[CandidateKeyResult] = []
    target_values: dict[tuple[str, str], set[str]] = {}
    relationships = [
        RelationshipResult(
            label=label,
            source_dataset=DATASET_LABELS[source_file],
            source_column=source_column,
            target_dataset=DATASET_LABELS[target_file],
            target_column=target_column,
        )
        for label, source_file, source_column, target_file, target_column
        in RELATIONSHIP_SPECS
    ]

    for _, _, _, target_file, target_column in RELATIONSHIP_SPECS:
        target_values.setdefault((target_file, target_column), set())

    with tempfile.TemporaryDirectory(prefix="datapulse-schema-") as temporary_dir:
        database_path = Path(temporary_dir) / "candidate-keys.sqlite3"
        connection = sqlite3.connect(database_path)
        try:
            connection.execute(
                "CREATE TABLE seen_keys ("
                "dataset TEXT NOT NULL, "
                "key_name TEXT NOT NULL, "
                "key_value TEXT NOT NULL, "
                "PRIMARY KEY (dataset, key_name, key_value)"
                ") WITHOUT ROWID"
            )

            for path in paths:
                reader = iter(_read_csv(path))
                columns = next(reader)
                profile = DatasetProfile(
                    filename=path.name,
                    columns=columns,
                    null_counts=dict.fromkeys(columns, 0),
                )
                profiles.append(profile)
                file_candidates = _candidate_results(path.name, columns)
                candidate_keys.extend(file_candidates)

                target_column_names = {
                    column
                    for (target_file, column) in target_values
                    if target_file == path.name
                }
                for column in target_column_names:
                    if column not in columns:
                        raise AnalysisError(
                            f"{path.name}: relationship target column "
                            f"{column!r} is missing"
                        )

                for row in reader:
                    profile.row_count += 1
                    row_values = dict(zip(columns, row, strict=True))

                    for column, value in row_values.items():
                        if _is_null(value):
                            profile.null_counts[column] += 1

                    for column in target_column_names:
                        value = row_values[column]
                        if not _is_null(value):
                            target_values[(path.name, column)].add(value)

                    for result in file_candidates:
                        values = tuple(row_values[column] for column in result.columns)
                        if any(_is_null(value) for value in values):
                            result.null_key_rows += 1
                            continue

                        key_json = json.dumps(values, ensure_ascii=False)
                        cursor = connection.execute(
                            "INSERT OR IGNORE INTO seen_keys "
                            "(dataset, key_name, key_value) VALUES (?, ?, ?)",
                            (result.dataset, result.label, key_json),
                        )
                        if cursor.rowcount == 0:
                            result.duplicate_rows += 1
                        else:
                            result.unique_keys += 1

            connection.commit()

            for relationship, specification in zip(
                relationships, RELATIONSHIP_SPECS, strict=True
            ):
                _, source_file, source_column, target_file, target_column = specification
                source_path = paths_by_name[source_file]
                reader = iter(_read_csv(source_path))
                columns = next(reader)
                if source_column not in columns:
                    raise AnalysisError(
                        f"{source_file}: relationship source column "
                        f"{source_column!r} is missing"
                    )

                accepted_values = target_values[(target_file, target_column)]
                for row in reader:
                    relationship.row_count += 1
                    value = row[columns.index(source_column)]
                    if _is_null(value):
                        relationship.null_key_rows += 1
                    elif value not in accepted_values:
                        relationship.orphan_rows += 1
        finally:
            connection.close()

    return SchemaAnalysis(
        datasets=profiles,
        candidate_keys=candidate_keys,
        relationships=relationships,
    )


def _inline_code(value: str) -> str:
    return f"`{value.replace('|', r'\|')}`"


def write_report(analysis: SchemaAnalysis, output: Path, raw_dir: Path) -> None:
    """Write a Markdown summary of a completed schema analysis."""
    lines = [
        "# DataPulse — Source Schema and Relationship Analysis",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Source directory: `{raw_dir}`",
        "",
        "This report is analysis-only. It does not alter source files, "
        "create database tables, or deduplicate records.",
        "",
        "Null means an empty or whitespace-only CSV field. Candidate-key "
        "duplicate counts are repeated complete key values beyond their "
        "first occurrence. Referential-integrity counts include every source "
        "row; blank foreign keys are reported separately from orphans.",
        "",
        "## Dataset schemas",
        "",
    ]

    for profile in analysis.datasets:
        lines.extend(
            [
                f"### {DATASET_LABELS.get(profile.filename, profile.filename)} "
                f"(`{profile.filename}`)",
                "",
                f"- Rows: {profile.row_count:,}",
                f"- Columns: {len(profile.columns)}",
                "",
                "| Column | Null values |",
                "| --- | ---: |",
            ]
        )
        lines.extend(
            f"| {_inline_code(column)} | {profile.null_counts[column]:,} |"
            for column in profile.columns
        )
        lines.append("")

    lines.extend(
        [
            "## Candidate-key analysis",
            "",
            (
                "| Dataset | Key fields | Null-key rows | Duplicate rows | "
                "Unique complete keys | Assessment |"
            ),
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for result in analysis.candidate_keys:
        assessment = (
            "Investigative only; not asserted as a key"
            if result.investigative
            else "Candidate"
        )
        fields = " + ".join(result.columns)
        lines.append(
            f"| {_inline_code(result.dataset)} | {_inline_code(fields)} | "
            f"{result.null_key_rows:,} | {result.duplicate_rows:,} | "
            f"{result.unique_keys:,} | {assessment} |"
        )
    lines.extend(
        [
            "",
            "Review `review_id` is measured for nulls and duplicates but is "
            "not assumed to be unique. Geolocation is investigated using ZIP "
            "prefix, ZIP prefix + latitude + longitude, and the complete row; "
            "ZIP prefix alone is not assumed to be unique.",
            "",
            "## Referential-integrity analysis",
            "",
            "| Relationship | Source rows | Null-key rows | Orphan rows |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for result in analysis.relationships:
        lines.append(
            f"| {_inline_code(result.label)} | {result.row_count:,} | "
            f"{result.null_key_rows:,} | {result.orphan_rows:,} |"
        )
    lines.append("")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze CSV schemas, candidate keys, and relationships."
    )
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--output", type=Path, default=Path("docs/schema-analysis.md")
    )
    args = parser.parse_args()

    try:
        analysis = analyze_schema(args.raw_dir)
        write_report(analysis, args.output, args.raw_dir)
    except AnalysisError as exc:
        print(f"Schema analysis failed: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Could not write schema analysis report: {exc}", file=sys.stderr)
        return 1

    print(f"Analyzed {len(analysis.datasets)} CSV files.")
    print(f"Report saved to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
