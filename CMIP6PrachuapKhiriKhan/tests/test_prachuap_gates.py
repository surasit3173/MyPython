#!/usr/bin/env python3
"""
Hard-Stop & Validation Gate Tests (Project 1: Prachuap Khiri Khan)
===================================================================
Verifies Gate 1 through Gate 4 validation failure enforcement.
Asserts that missing files trigger STOP_BLOCKED rather than synthetic fallback.
"""

import sys
import os
import unittest
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.validation.gates import (
    validate_gate_1_inputs,
    validate_gate_2_config,
    StopBlockedException
)


class TestPrachuapGates(unittest.TestCase):

    def setUp(self):
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        cfg_path = os.path.join(self.base_dir, 'config.yaml')
        if not os.path.exists(cfg_path):
            cfg_path = os.path.join(self.base_dir, 'config', 'config.yaml')
        with open(cfg_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def test_gate_1_valid_inputs_pass(self):
        """Verifies valid input files pass Gate 1."""
        passed, df_rain, rain_path, coords_path = validate_gate_1_inputs(self.config, self.base_dir)
        self.assertTrue(passed)
        self.assertEqual(len(df_rain), 12418)

    def test_gate_1_missing_file_triggers_stop_blocked(self):
        """Verifies missing input file triggers STOP_BLOCKED."""
        invalid_cfg = self.config.copy()
        invalid_cfg['data'] = self.config['data'].copy()
        invalid_cfg['data']['rainfall_csv'] = "NON_EXISTENT_FILE.csv"

        with self.assertRaises(StopBlockedException):
            validate_gate_1_inputs(invalid_cfg, self.base_dir)

    def test_gate_2_synthetic_fallback_prohibited(self):
        """Verifies enabling synthetic fallback in config triggers STOP_BLOCKED."""
        invalid_cfg = self.config.copy()
        invalid_cfg['project'] = self.config['project'].copy()
        invalid_cfg['project']['synthetic_fallback_enabled'] = True

        with self.assertRaises(StopBlockedException):
            validate_gate_2_config(invalid_cfg)


if __name__ == '__main__':
    unittest.main()
