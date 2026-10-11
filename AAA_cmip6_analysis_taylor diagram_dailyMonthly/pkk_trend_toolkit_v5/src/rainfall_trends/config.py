"""Configuration schema and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    """Raised when a configuration is absent or internally inconsistent."""


@dataclass(frozen=True)
class AnalysisConfig:
    area_name: str
    rainfall_path: str
    station_metadata_path: str
    input_layout: str = "wide"
    date_columns: tuple[str, str, str] = ("Year", "Month", "Day")
    date_column: str = "date"
    station_column: str = "station_id"
    value_column: str = "rain_mm"
    metadata_station_column: str = "station_id"
    latitude_column: str = "latitude"
    longitude_column: str = "longitude"
    elevation_column: str = "elevation_m"
    wet_months: tuple[int, ...] = (5, 6, 7, 8, 9, 10)
    dry_months: tuple[int, ...] = (11, 12, 1, 2, 3, 4)
    completeness_threshold: float = 1.0
    alpha: float = 0.05
    hr_max_lag: int = 3
    acf_alpha: float = 0.05
    bootstrap_reps: int = 2000
    bootstrap_block_length: int = 3
    monte_carlo_reps: int = 10000
    fdr_reps: int = 5000
    seed: int = 42
    phi_levels: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6, 0.8)
    standardized_slopes: tuple[float, ...] = (0.01, 0.025, 0.05)
    fdr_phi: float = 0.4
    fdr_spatial_rho: float = 0.3
    station_weighting: str = "equal"
    source_urls: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "AnalysisConfig":
        values = dict(raw)
        for key in ("date_columns", "wet_months", "dry_months", "phi_levels", "standardized_slopes", "source_urls"):
            if key in values:
                values[key] = tuple(values[key])
        config = cls(**values)
        config.validate()
        return config

    @classmethod
    def load(cls, path: str | Path) -> "AnalysisConfig":
        source = Path(path)
        if not source.is_file():
            raise ConfigurationError(f"Configuration file does not exist: {source}")
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"Cannot read configuration {source}: {exc}") from exc
        return cls.from_mapping(raw)

    def validate(self) -> None:
        if not self.area_name.strip():
            raise ConfigurationError("area_name must be non-empty")
        if self.input_layout not in {"wide", "long"}:
            raise ConfigurationError("input_layout must be 'wide' or 'long'")
        if not 0 < self.completeness_threshold <= 1:
            raise ConfigurationError("completeness_threshold must be in (0, 1]")
        if not 0 < self.alpha < 1 or not 0 < self.acf_alpha < 1:
            raise ConfigurationError("alpha values must be in (0, 1)")
        if self.hr_max_lag < 1:
            raise ConfigurationError("hr_max_lag must be at least 1")
        if self.station_weighting != "equal":
            raise ConfigurationError("version 5 supports only explicit equal station weighting")

    def resolved_paths(self, config_path: str | Path) -> tuple[Path, Path]:
        base = Path(config_path).resolve().parent
        rain = (base / self.rainfall_path).resolve()
        stations = (base / self.station_metadata_path).resolve()
        return rain, stations
