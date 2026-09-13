import unittest
import os
import subprocess

class TestCrossRegionReusability(unittest.TestCase):
    def setUp(self):
        self.paper3_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.src_script = os.path.join(self.paper3_dir, "src", "run_pipeline.py")
        self.example_config = os.path.join(self.paper3_dir, "config", "example_region.yaml")

    def test_example_region_execution(self):
        """Verify pipeline executes on a second region configuration without code modification."""
        cmd = ["python3", self.src_script, "--config", self.example_config]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Cross-region pipeline failed: {res.stderr}")

        output_dir = os.path.join(self.paper3_dir, "outputs_example_region")
        self.assertTrue(os.path.exists(output_dir))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "tables", "enso_response_summary.csv")))
        self.assertTrue(os.path.exists(os.path.join(output_dir, "figures", "Figure2_Observed_ENSO_Response.png")))

if __name__ == "__main__":
    unittest.main()
