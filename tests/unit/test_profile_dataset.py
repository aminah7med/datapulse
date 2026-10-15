
import tempfile
import unittest
from pathlib import Path

from scripts.profile_dataset import profile_csv, write_report


class TestProfileCsv(unittest.TestCase):

    def test_counts_rows_columns_and_blanks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "orders.csv"
            path.write_text(
                "order_id,amount,customer\n"
                "1,10,A\n"
                "2,,B\n"
                "3,   ,\n",
                encoding="utf-8",
            )

            result = profile_csv(path)

            self.assertIsNone(result["error"])
            self.assertEqual(result["row_count"], 3)
            self.assertEqual(len(result["columns"]), 3)
            self.assertEqual(result["blank_counts"], [0, 2, 1])
            self.assertEqual(result["malformed_rows"], 0)

    def test_detects_inconsistent_row_lengths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text(
                "a,b\n"
                "1,2\n"
                "3\n"
                "4,5,6\n",
                encoding="utf-8",
            )

            result = profile_csv(path)

            self.assertIsNone(result["error"])
            self.assertEqual(result["row_count"], 3)
            self.assertEqual(result["malformed_rows"], 2)
            self.assertEqual(result["blank_counts"], [0, 1])

    def test_reports_missing_file_without_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp)
            path = raw_dir / "missing.csv"
            output = raw_dir / "report.md"

            result = profile_csv(path)
            write_report([result], output, raw_dir)
            report = output.read_text(encoding="utf-8")

            self.assertIsNotNone(result["error"])
            self.assertIsNone(result["size_bytes"])
            self.assertIn("- File size: unavailable", report)
            self.assertIn("**Processing error:**", report)


if __name__ == "__main__":
    unittest.main()
