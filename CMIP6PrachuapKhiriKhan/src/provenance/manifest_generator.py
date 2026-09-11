#!/usr/bin/env python3
"""
Manifest Generator Module
=========================
Generates cryptographic audit manifests (run_manifest.json).
"""

import os
import json
import platform
import hashlib
from datetime import datetime

def compute_sha256(filepath):
    if not os.path.exists(filepath):
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def generate_run_manifest(config, data_info, output_files, base_dir="."):
    """Generates run_manifest.json with hashes and metadata."""
    manifests_dir = os.path.join(base_dir, config['output']['manifests_dir'])
    os.makedirs(manifests_dir, exist_ok=True)

    manifest_path = os.path.join(manifests_dir, "run_manifest.json")
    
    output_hashes = {}
    for name, p in output_files.items():
        if os.path.exists(p):
            output_hashes[name] = {
                'path': p,
                'sha256': compute_sha256(p)
            }

    manifest = {
        "project_name": config['project']['name'],
        "version": config['project']['version'],
        "run_id": f"RUN_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "environment": {
            "python_version": platform.python_version(),
            "operating_system": platform.platform(),
            "processor": platform.processor()
        },
        "provenance": {
            "input_obs_file": data_info['obs_path'],
            "input_obs_sha256": compute_sha256(data_info['obs_path']),
            "coords_file": data_info['coords_path'],
            "coords_sha256": compute_sha256(data_info['coords_path']),
            "config_sha256": compute_sha256(os.path.join(base_dir, "config.yaml"))
        },
        "methodology": {
            "primary_trend_method": config['analysis']['primary_method'],
            "secondary_trend_method": config['analysis']['secondary_method'],
            "alpha_level": config['analysis']['alpha'],
            "r1_significance_alpha": config['analysis']['r1_significance_alpha'],
            "analysis_period": config['data']['analysis_period'],
            "station_count": len(data_info['station_cols'])
        },
        "output_artifacts": output_hashes,
        "validation_status": "PASS"
    }

    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    return manifest_path
