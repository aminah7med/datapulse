import csv
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_schema import AnalysisError, analyze_schema, write_report

FIXTURE_ROWS = {
    "olist_customers_dataset.csv": (
        ["customer_id", "customer_unique_id"],
        [["c1", "u1"], ["c1", "u2"], ["", "u3"]],
    ),
    "olist_orders_dataset.csv": (
        ["order_id", "customer_id"],
        [["o1", "c1"], ["o1", "missing-customer"], ["o2", ""]],
    ),
    "olist_order_items_dataset.csv": (
        ["order_id", "order_item_id", "product_id", "seller_id"],
        [
            ["o1", "1", "p1", "s1"],
            ["missing-order", "1", "missing-product", "missing-seller"],
            ["o2", "1", "p1", "s1"],
        ],
    ),
    "olist_order_payments_dataset.csv": (
        ["order_id", "payment_sequential"],
        [["o1", "1"], ["o1", "1"], ["", "2"]],
    ),
    "olist_order_reviews_dataset.csv": (
        ["review_id", "order_id"],
        [["r1", "o1"], ["r1", "missing-order"], ["", "o2"]],
    ),
    "olist_products_dataset.csv": (
        ["product_id", "product_category_name"],
        [["p1", "category"], ["p2", "untranslated"], ["", ""]],
    ),
    "olist_sellers_dataset.csv": (
        ["seller_id"],
        [["s1"]],
    ),
    "product_category_name_translation.csv": (
        ["product_category_name", "product_category_name_english"],
        [["category", "Category"]],
    ),
    "olist_geolocation_dataset.csv": (
        [
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ],
        [
            ["10000", "-10.0", "-40.0", "city", "ST"],
            ["10000", "-10.0", "-40.0", "city", "ST"],
            ["10000", "-11.0", "-41.0", "city", "ST"],
        ],
    ),
}


def create_fixture(raw_dir: Path) -> dict[str, bytes]:
    originals = {}
    for filename, (columns, rows) in FIXTURE_ROWS.items():
        path = raw_dir / filename
        with path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(columns)
            writer.writerows(rows)
        originals[filename] = path.read_bytes()
    return originals


class TestAnalyzeSchema(unittest.TestCase):
    def test_counts_nulls_duplicate_keys_and_relationships(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            raw_dir = Path(temporary_dir)
            original_files = create_fixture(raw_dir)

            analysis = analyze_schema(raw_dir)

            datasets = {profile.filename: profile for profile in analysis.datasets}
            self.assertEqual(datasets["olist_customers_dataset.csv"].row_count, 3)
            self.assertEqual(
                datasets["olist_customers_dataset.csv"].null_counts["customer_id"],
                1,
            )

            keys = {
                (result.dataset, result.label): result
                for result in analysis.candidate_keys
            }
            customers = keys[("customers", "customer_id")]
            self.assertEqual(customers.null_key_rows, 1)
            self.assertEqual(customers.duplicate_rows, 1)
            self.assertEqual(customers.unique_keys, 1)

            review_id = keys[("order_reviews", "review_id")]
            self.assertTrue(review_id.investigative)
            self.assertEqual(review_id.null_key_rows, 1)
            self.assertEqual(review_id.duplicate_rows, 1)

            geo_zip = keys[("geolocation", "geolocation_zip_code_prefix")]
            geo_coordinates = keys[
                ("geolocation", "ZIP prefix + latitude + longitude")
            ]
            geo_full_row = keys[("geolocation", "all columns (exact row)")]
            self.assertEqual(geo_zip.duplicate_rows, 2)
            self.assertEqual(geo_coordinates.duplicate_rows, 1)
            self.assertEqual(geo_full_row.duplicate_rows, 1)

            references = {result.label: result for result in analysis.relationships}
            self.assertEqual(references["orders.customer_id"].orphan_rows, 1)
            self.assertEqual(references["orders.customer_id"].null_key_rows, 1)
            self.assertEqual(references["order_items.order_id"].orphan_rows, 1)
            self.assertEqual(references["order_items.product_id"].orphan_rows, 1)
            self.assertEqual(references["order_items.seller_id"].orphan_rows, 1)
            self.assertEqual(references["order_payments.order_id"].null_key_rows, 1)
            self.assertEqual(references["order_reviews.order_id"].orphan_rows, 1)
            self.assertEqual(
                references["products.product_category_name"].orphan_rows, 1
            )
            self.assertEqual(
                {name: (raw_dir / name).read_bytes() for name in original_files},
                original_files,
            )

    def test_writes_report_with_schema_and_relationship_results(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            raw_dir = Path(temporary_dir)
            create_fixture(raw_dir)
            output = raw_dir / "docs" / "schema-analysis.md"

            write_report(analyze_schema(raw_dir), output, raw_dir)

            report = output.read_text(encoding="utf-8")
            self.assertIn("## Dataset schemas", report)
            self.assertIn("## Candidate-key analysis", report)
            self.assertIn("## Referential-integrity analysis", report)
            self.assertIn("ZIP prefix alone is not assumed to be unique", report)

    def test_rejects_malformed_row_with_record_location(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            raw_dir = Path(temporary_dir)
            create_fixture(raw_dir)
            path = raw_dir / "olist_customers_dataset.csv"
            path.write_text("customer_id,customer_unique_id\nc1\n", encoding="utf-8")

            with self.assertRaisesRegex(
                AnalysisError, "olist_customers_dataset.csv.*record 2"
            ):
                analyze_schema(raw_dir)


if __name__ == "__main__":
    unittest.main()
