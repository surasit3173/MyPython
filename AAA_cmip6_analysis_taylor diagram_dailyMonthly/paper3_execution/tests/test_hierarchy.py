import unittest

import pandas as pd

from paper3core.hierarchy import grid_signatures


class GridSignatureTests(unittest.TestCase):
    def test_identical_station_series_share_one_grid_signature(self):
        """Catches counting stations mapped to one model grid cell as independent."""
        frame = pd.DataFrame(
            {
                "A": [0.0, 1.0, 2.0, 3.0],
                "B": [0.0, 1.0, 2.0, 3.0],
                "C": [0.0, 1.0, 2.0, 3.000001],
            }
        )
        signatures = grid_signatures(frame)

        self.assertEqual(signatures["A"], signatures["B"])
        self.assertNotEqual(signatures["A"], signatures["C"])


if __name__ == "__main__":
    unittest.main()
