# Reusing Workflow for Another Province / Region

To apply this analysis framework to another study area, province, river basin, or custom set of stations:

1. Prepare your daily rainfall dataset in CSV format according to `docs/data_format.md`.
2. Save your dataset in `data/raw/` or any local folder.
3. Prepare station metadata (DOCX or CSV) and place it in `data/metadata/`.
4. Copy `config/config_example.yaml` to a new configuration file (e.g., `config/config_myregion.yaml`).
5. Edit `config_myregion.yaml` with your file paths, project name, wet threshold, and station columns.
6. Run the full pipeline:
   ```bash
   python scripts/run_full_analysis.py --config config/config_myregion.yaml
   ```
7. Results will automatically be generated in `outputs/<project_name>/`.
