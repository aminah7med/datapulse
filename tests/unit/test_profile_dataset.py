
import tempfile
import unittest
from pathlib import Path

from scripts.profile_dataset import profile_csv


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


if __name__ == "__main__":
    unittest.main()
