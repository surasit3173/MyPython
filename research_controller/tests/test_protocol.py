"""
Unit and regression tests for protocol.py artifact path isolation.
"""

import tempfile
import unittest
from pathlib import Path

from protocol import ArtifactPathError, RunManifest, prepare_run_directory


class TestProtocolPathIsolation(unittest.TestCase):
    def test_reject_empty_or_whitespace_components(self):
        with self.assertRaises(ArtifactPathError):
            prepare_run_directory(Path("/tmp"), "", "run1")

        with self.assertRaises(ArtifactPathError):
            prepare_run_directory(Path("/tmp"), "   ", "run1")

        with self.assertRaises(ArtifactPathError):
            prepare_run_directory(Path("/tmp"), "project1", "  ")

    def test_reject_dot_dot_traversal(self):
        traversal_vectors = [
            "../secret",
            "project/../../etc",
            "..",
            "project/../project2",
            "run_dir/../",
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            for vec in traversal_vectors:
                with self.assertRaises(ArtifactPathError, msg=f"Failed to reject traversal vector: {vec}"):
                    prepare_run_directory(base_dir, vec, "run1")

                with self.assertRaises(ArtifactPathError, msg=f"Failed to reject traversal vector: {vec}"):
                    prepare_run_directory(base_dir, "project1", vec)

    def test_reject_absolute_paths_and_drive_letters(self):
        absolute_vectors = [
            "/etc/passwd",
            "/tmp/run",
            "C:\\Windows\\System32",
            "D:/data",
            "\\\\network\\share",
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            for vec in absolute_vectors:
                with self.assertRaises(ArtifactPathError, msg=f"Failed to reject absolute path: {vec}"):
                    prepare_run_directory(base_dir, vec, "run1")

                with self.assertRaises(ArtifactPathError, msg=f"Failed to reject absolute path: {vec}"):
                    prepare_run_directory(base_dir, "project1", vec)

    def test_reject_leading_trailing_slashes(self):
        invalid_slashes = [
            "/project1",
            "project1/",
            "/project1/",
            "/run1",
            "run1/",
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            for vec in invalid_slashes:
                with self.assertRaises(ArtifactPathError):
                    prepare_run_directory(base_dir, vec, "run1")

                with self.assertRaises(ArtifactPathError):
                    prepare_run_directory(base_dir, "project1", vec)

    def test_run_manifest_component_validation(self):
        with self.assertRaises(ArtifactPathError):
            RunManifest(project_id="../bad_project", run_id="run1", task_id="t1")

        with self.assertRaises(ArtifactPathError):
            RunManifest(project_id="CMIP6Lampang", run_id="/etc/run1", task_id="t1")

    def test_canonical_relative_path_containment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir).resolve()
            dirs = prepare_run_directory(base_dir, "CMIP6Lampang", "run_lampang_001")
            run_dir = dirs["run_dir"].resolve()

            # Ensure run_dir is strictly contained inside base_dir
            self.assertTrue(run_dir.is_relative_to(base_dir))
            self.assertNotEqual(run_dir, base_dir)
            self.assertTrue(run_dir.exists())
            self.assertTrue(dirs["analysis_results"].exists())
            self.assertTrue(dirs["validation"].exists())
            self.assertTrue(dirs["review"].exists())


if __name__ == "__main__":
    unittest.main()
