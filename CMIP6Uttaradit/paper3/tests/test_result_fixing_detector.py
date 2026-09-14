import unittest
import os
import glob

class TestResultFixingDetector(unittest.TestCase):
    def setUp(self):
        self.src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")

    def test_no_hardcoded_scientific_results(self):
        """Scan Python scripts in src/ for hardcoded scientific result assignments."""
        py_files = glob.glob(os.path.join(self.src_dir, "*.py"))
        suspicious_patterns = [
            "pe_enso =", "p_value =", "observed_response =", "qdm_response =", "raw_response ="
        ]

        for fpath in py_files:
            with open(fpath, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f, start=1):
                    # Ignore comments
                    code_part = line.split("#")[0].strip()
                    for pattern in suspicious_patterns:
                        if pattern in code_part:
                            # Verify if RHS is a literal float/int
                            rhs = code_part.split("=")[1].strip()
                            try:
                                float(rhs)
                                self.fail(f"Hardcoded scientific result found in {fpath}:{line_idx}: {line.strip()}")
                            except ValueError:
                                pass # Dynamic expression

    def test_no_hardcoded_province_logic(self):
        """Scan statistical core scripts for province-specific branching."""
        core_files = [
            os.path.join(self.src_dir, "statistics.py"),
            os.path.join(self.src_dir, "precipitation_indices.py"),
            os.path.join(self.src_dir, "enso_classifier.py")
        ]
        for fpath in core_files:
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                    self.assertNotIn("if province ==", content)
                    self.assertNotIn("if region ==", content)

if __name__ == "__main__":
    unittest.main()
