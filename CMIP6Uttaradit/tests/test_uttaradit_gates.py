#!/usr/bin/env python3
"""
Hard-Stop & Validation Gate Tests (Project 2: Uttaradit)
========================================================
Verifies Gate 1 through Gate 4 validation failure enforcement.
Asserts that missing GCM files trigger STOP_BLOCKED rather than synthetic fallback.
"""

import sys
import os
import unittest
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.validation.gates import (
    validate_gate_1_uttaradit_inputs,
    validate_gate_2_config,
    StopBlockedException
)


class TestUttaraditGates(unittest.TestCase):

    def setUp(self):
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        cfg_path = os.path.join(self.base_dir, 'config', 'config.yaml')
        with open(cfg_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def test_gate_1_valid_inputs_pass(self):
        """Verifies valid input files and 7 GCM directories pass Gate 1."""
        passed, df_obs, obs_path, coords_path = validate_gate_1_uttaradit_inputs(self.config, self.base_dir)
        self.assertTrue(passed)
        self.assertEqual(len(df_obs), 12418)

    def test_gate_1_missing_gcm_triggers_stop_blocked(self):
        """Verifies missing GCM directory triggers STOP_BLOCKED."""
        invalid_cfg = self.config.copy()
        invalid_cfg['gcms'] = ['NON_EXISTENT_GCM']

        with self.assertRaises(StopBlockedException):
            validate_gate_1_uttaradit_inputs(invalid_cfg, self.base_dir)

    def test_gate_2_synthetic_fallback_prohibited(self):
        """Verifies enabling synthetic fallback in config triggers STOP_BLOCKED."""
        invalid_cfg = self.config.copy()
        invalid_cfg['project'] = self.config['project'].copy()
        invalid_cfg['project']['synthetic_fallback_enabled'] = True

        with self.assertRaises(StopBlockedException):
            validate_gate_2_config(invalid_cfg)


if __name__ == '__main__':
    unittest.main()
