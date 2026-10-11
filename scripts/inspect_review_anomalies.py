
import csv
from collections import Counter
from pathlib import Path

path = Path("data/raw/olist_order_reviews_dataset.csv")

with path.open("r", encoding="utf-8-sig", newline="") as file:
    reader = csv.reader(file, strict=True)
    headers = next(reader, None)

    if not headers:
        raise ValueError("CSV file has no header.")

    expected_fields = len(headers)
    counts = Counter()
    samples_shown = 0

    print(f"Expected fields per row: {expected_fields}")
    print(f"Columns: {headers}")
    print("-" * 70)

    for record_number, row in enumerate(reader, start=1):
        if len(row) != expected_fields:
            counts[len(row)] += 1

            if samples_shown < 15:
                print(
                    f"Record: {record_number} | "
                    f"Physical line ending: {reader.line_num} | "
                    f"Expected: {expected_fields} | "
                    f"Actual: {len(row)}"
                )

                for index, value in enumerate(row[:10]):
                    print(f"  Field {index + 1}: {value[:100]!r}")

                print("-" * 70)
                samples_shown += 1

    print("\nField-count summary:")
    for field_count, total in sorted(counts.items()):
        print(
            f"{field_count} fields: {total} records "
            f"(expected {expected_fields})"
        )

    print(f"\nTotal inconsistent records: {sum(counts.values())}")
