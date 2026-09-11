"""Blocked cross-fitted precipitation quantile delta mapping."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import rankdata


def midrank_probabilities(values) -> np.ndarray:
    """Hazen plotting positions with average ranks for tied values."""
    array = np.asarray(values, dtype=float)
    probabilities = np.full(array.shape, np.nan, dtype=float)
    valid = np.isfinite(array)
    if valid.any():
        ranks = rankdata(array[valid], method="average")
        probabilities[valid] = (ranks - 0.5) / valid.sum()
    return probabilities


def _fit_apply_group(
    observed_calibration: np.ndarray,
    model_calibration: np.ndarray,
    model_target: np.ndarray,
    *,
    wet_threshold: float,
    min_wet_days: int,
) -> tuple[np.ndarray, dict[str, float | int]]:
    observed = observed_calibration[np.isfinite(observed_calibration)]
    model = model_calibration[np.isfinite(model_calibration)]
    target = np.asarray(model_target, dtype=float)
    if observed.size == 0 or model.size == 0:
        raise ValueError("empty QDM calibration group")

    observed_wet = np.sort(observed[observed >= wet_threshold])
    observed_wet_fraction = observed_wet.size / observed.size
    model_wet_threshold = float(
        np.quantile(model, max(0.0, 1.0 - observed_wet_fraction), method="linear")
    )
    model_wet_threshold = max(0.0, model_wet_threshold)
    # Include threshold ties while still excluding true zero precipitation.
    # A strict '>' can discard the entire wet sample when a model is quantized.
    model_wet = np.sort(model[(model >= model_wet_threshold) & (model > 0.0)])
    if observed_wet.size < min_wet_days or model_wet.size < min_wet_days:
        raise ValueError(
            "too few wet calibration days "
            f"(observed={observed_wet.size}, model={model_wet.size}, min={min_wet_days})"
        )

    result = np.full(target.shape, np.nan, dtype=float)
    valid = np.isfinite(target)
    result[valid] = 0.0
    wet_target = valid & (target >= model_wet_threshold) & (target > 0.0)
    if wet_target.any():
        wet_values = target[wet_target]
        probabilities = midrank_probabilities(wet_values)
        model_calibration_quantiles = np.quantile(
            model_wet, probabilities, method="linear"
        )
        observed_calibration_quantiles = np.quantile(
            observed_wet, probabilities, method="linear"
        )
        with np.errstate(divide="ignore", invalid="ignore"):
            delta = np.divide(
                wet_values,
                model_calibration_quantiles,
                out=np.ones_like(wet_values),
                where=model_calibration_quantiles > 0,
            )
        corrected = np.maximum(observed_calibration_quantiles * delta, 0.0)
        result[wet_target] = corrected

    diagnostics = {
        "n_observed_calibration": int(observed.size),
        "n_model_calibration": int(model.size),
        "n_observed_wet": int(observed_wet.size),
        "n_model_wet": int(model_wet.size),
        "n_target": int(valid.sum()),
        "n_target_wet": int(wet_target.sum()),
        "observed_wet_fraction": float(observed_wet_fraction),
        "model_wet_threshold_mm": float(model_wet_threshold),
    }
    return result, diagnostics


def crossfit_qdm(
    observed: pd.Series,
    model: pd.Series,
    *,
    climate_year: pd.Series,
    blocks: list[tuple[int, int]],
    wet_threshold: float = 1.0,
    group_by_month: bool = True,
    min_wet_days: int = 5,
    sparse_month_fallback: str | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    """Apply leave-one-block-out multiplicative QDM without observation leakage.

    Target-model values determine their own empirical ranks, which is permitted
    by QDM; observations from the target climate-year block are never used.
    """
    common_index = observed.index
    if not model.index.equals(common_index) or not climate_year.index.equals(common_index):
        raise ValueError("observed, model, and climate_year indices must match")
    output = pd.Series(np.nan, index=common_index, dtype=float, name="qdm")
    diagnostic_rows = []
    months = range(1, 13) if group_by_month else (0,)

    for block_start, block_end in blocks:
        target_block = climate_year.between(block_start, block_end)
        calibration_block = ~target_block
        for month in months:
            month_mask = (
                pd.Series(common_index.month == month, index=common_index)
                if group_by_month
                else pd.Series(True, index=common_index)
            )
            target_mask = target_block & month_mask
            if not target_mask.any():
                continue
            calibration_mask = calibration_block & month_mask
            fallback_used = False
            calibration_months = str(month) if group_by_month else "all"
            try:
                corrected, diagnostics = _fit_apply_group(
                    observed.loc[calibration_mask].to_numpy(dtype=float),
                    model.loc[calibration_mask].to_numpy(dtype=float),
                    model.loc[target_mask].to_numpy(dtype=float),
                    wet_threshold=wet_threshold,
                    min_wet_days=min_wet_days,
                )
            except ValueError as error:
                if (
                    sparse_month_fallback != "adjacent_3_month_pool"
                    or not group_by_month
                    or "too few wet calibration days" not in str(error)
                ):
                    raise
                adjacent_months = [12 if month == 1 else month - 1, month, 1 if month == 12 else month + 1]
                pooled_month_mask = pd.Series(
                    common_index.month.isin(adjacent_months), index=common_index
                )
                pooled_calibration_mask = calibration_block & pooled_month_mask
                corrected, diagnostics = _fit_apply_group(
                    observed.loc[pooled_calibration_mask].to_numpy(dtype=float),
                    model.loc[pooled_calibration_mask].to_numpy(dtype=float),
                    model.loc[target_mask].to_numpy(dtype=float),
                    wet_threshold=wet_threshold,
                    min_wet_days=min_wet_days,
                )
                fallback_used = True
                calibration_months = ",".join(str(value) for value in adjacent_months)
            output.loc[target_mask] = corrected
            diagnostic_rows.append(
                {
                    "block_start": int(block_start),
                    "block_end": int(block_end),
                    "month": int(month),
                    "calibration_months": calibration_months,
                    "sparse_fallback_used": fallback_used,
                    "n_target_observations_used": 0,
                    **diagnostics,
                }
            )
    return output, pd.DataFrame(diagnostic_rows)
