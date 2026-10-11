"""Hierarchy-respecting ENSO response estimates and multiplicity utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _response_table(
    data: pd.DataFrame,
    *,
    entity_columns: list[str],
    phase: str,
    minimum_seasons: int,
) -> pd.DataFrame:
    rows = []
    for keys, group in data.groupby(entity_columns, sort=True, dropna=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        valid = group[np.isfinite(group["value"].astype(float))]
        selected = valid[valid["enso_phase"] == phase]
        neutral = valid[valid["enso_phase"] == "NEUTRAL"]
        n_phase = int(selected["climate_year"].nunique())
        n_neutral = int(neutral["climate_year"].nunique())
        eligible = n_phase >= minimum_seasons and n_neutral >= minimum_seasons
        phase_mean = float(selected["value"].mean()) if n_phase else np.nan
        neutral_mean = float(neutral["value"].mean()) if n_neutral else np.nan
        absolute = phase_mean - neutral_mean if eligible else np.nan
        percent = (
            100.0 * absolute / neutral_mean
            if eligible and np.isfinite(neutral_mean) and abs(neutral_mean) > 1.0e-12
            else np.nan
        )
        row = dict(zip(entity_columns, keys, strict=True))
        row.update(
            {
                "phase": phase,
                "n_phase": n_phase,
                "n_neutral": n_neutral,
                "phase_mean": phase_mean,
                "neutral_mean": neutral_mean,
                "response_absolute": absolute,
                "response_pct": percent,
                "eligible": bool(eligible),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def observed_response(
    data: pd.DataFrame, *, phase: str, minimum_seasons: int
) -> tuple[dict[str, float | int], pd.DataFrame]:
    """Station responses followed by an equal-weight regional median."""
    entities = _response_table(
        data,
        entity_columns=["station"],
        phase=phase,
        minimum_seasons=minimum_seasons,
    )
    eligible = entities[entities["eligible"]]
    estimate = {
        "response_absolute": float(eligible["response_absolute"].median()),
        "response_pct": float(eligible["response_pct"].median()),
        "n_entities": int(len(eligible)),
        "n_phase": int(data.loc[data["enso_phase"] == phase, "climate_year"].nunique()),
        "n_neutral": int(data.loc[data["enso_phase"] == "NEUTRAL", "climate_year"].nunique()),
    }
    return estimate, entities


def model_response(
    data: pd.DataFrame, *, phase: str, minimum_seasons: int
) -> tuple[dict[str, float | int], pd.DataFrame, pd.DataFrame]:
    """Station -> unique grid signature -> model -> ensemble aggregation."""
    grid_seasons = (
        data.groupby(
            ["model", "grid_signature", "climate_year", "enso_phase"],
            as_index=False,
            dropna=False,
        )["value"]
        .median()
    )
    grid_rows = _response_table(
        grid_seasons,
        entity_columns=["model", "grid_signature"],
        phase=phase,
        minimum_seasons=minimum_seasons,
    )
    model_rows = (
        grid_rows[grid_rows["eligible"]]
        .groupby("model", as_index=False)
        .agg(
            response_absolute=("response_absolute", "median"),
            response_pct=("response_pct", "median"),
            n_grid_signatures=("grid_signature", "nunique"),
            n_phase=("n_phase", "min"),
            n_neutral=("n_neutral", "min"),
        )
    )
    estimate = {
        "response_absolute": float(model_rows["response_absolute"].median()),
        "response_pct": float(model_rows["response_pct"].median()),
        "n_entities": int(len(model_rows)),
        "n_phase": int(model_rows["n_phase"].min()) if len(model_rows) else 0,
        "n_neutral": int(model_rows["n_neutral"].min()) if len(model_rows) else 0,
        "intermodel_iqr_pct": (
            float(model_rows["response_pct"].quantile(0.75) - model_rows["response_pct"].quantile(0.25))
            if len(model_rows)
            else np.nan
        ),
    }
    return estimate, model_rows, grid_rows


def classify_preservation(
    raw_response_pct: float,
    qdm_response_pct: float,
    *,
    near_zero: float,
    preserved_ratio: tuple[float, float] = (0.8, 1.2),
) -> dict[str, float | bool | str]:
    """Classify magnitude preservation after a pre-specified near-zero gate."""
    raw = float(raw_response_pct)
    qdm = float(qdm_response_pct)
    if not np.isfinite(raw) or not np.isfinite(qdm):
        return {"category": "INSUFFICIENT", "magnitude_ratio": np.nan, "shift_pct_points": np.nan, "sign_preserved": False}
    shift = qdm - raw
    if abs(raw) < near_zero:
        return {"category": "INDETERMINATE_RAW_NEAR_ZERO", "magnitude_ratio": np.nan, "shift_pct_points": shift, "sign_preserved": bool(np.sign(raw) == np.sign(qdm))}
    ratio = abs(qdm) / abs(raw)
    sign_preserved = bool(np.sign(raw) == np.sign(qdm))
    if not sign_preserved:
        category = "REVERSED"
    elif ratio < preserved_ratio[0]:
        category = "ATTENUATED"
    elif ratio > preserved_ratio[1]:
        category = "AMPLIFIED"
    else:
        category = "PRESERVED"
    return {
        "category": category,
        "magnitude_ratio": float(ratio),
        "shift_pct_points": float(shift),
        "sign_preserved": sign_preserved,
    }


def benjamini_hochberg(p_values) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values, preserving input order."""
    values = np.asarray(p_values, dtype=float)
    output = np.full(values.shape, np.nan, dtype=float)
    finite_positions = np.flatnonzero(np.isfinite(values))
    if not len(finite_positions):
        return output
    order = finite_positions[np.argsort(values[finite_positions])]
    ranked = values[order]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    output[order] = np.minimum(adjusted, 1.0)
    return output

