"""Event-level bootstrap and permutation inference for hierarchical responses."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


PHASES = ("EL_NINO", "LA_NINA", "NEUTRAL")
STAT_NAMES = (
    "el_absolute",
    "el_pct",
    "la_absolute",
    "la_pct",
    "phase_contrast_absolute",
    "phase_contrast_pct",
    "neutral_centered_asymmetry_absolute",
    "neutral_centered_asymmetry_pct",
)


@dataclass
class _Group:
    name: str
    matrix: np.ndarray
    indices: dict[str, np.ndarray]


def _mean_and_count(matrix: np.ndarray, indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    selected = matrix[indices, :]
    count = np.isfinite(selected).sum(axis=0)
    total = np.nansum(selected, axis=0)
    mean = np.divide(total, count, out=np.full(total.shape, np.nan), where=count > 0)
    return mean, count


def _group_statistics(
    group: _Group,
    indices: dict[str, np.ndarray],
    *,
    minimum_seasons: int,
) -> np.ndarray:
    el, n_el = _mean_and_count(group.matrix, indices["EL_NINO"])
    la, n_la = _mean_and_count(group.matrix, indices["LA_NINA"])
    neutral, n_neutral = _mean_and_count(group.matrix, indices["NEUTRAL"])
    eligible_el = (n_el >= minimum_seasons) & (n_neutral >= minimum_seasons)
    eligible_la = (n_la >= minimum_seasons) & (n_neutral >= minimum_seasons)
    eligible_joint = eligible_el & eligible_la

    el_abs = np.where(eligible_el, el - neutral, np.nan)
    la_abs = np.where(eligible_la, la - neutral, np.nan)
    safe_neutral = np.isfinite(neutral) & (np.abs(neutral) > 1.0e-12)
    el_pct = np.where(eligible_el & safe_neutral, 100.0 * el_abs / neutral, np.nan)
    la_pct = np.where(eligible_la & safe_neutral, 100.0 * la_abs / neutral, np.nan)
    contrast_abs = np.where(eligible_joint, la_abs - el_abs, np.nan)
    contrast_pct = np.where(eligible_joint, la_pct - el_pct, np.nan)
    true_asym_abs = np.where(eligible_joint, la_abs + el_abs, np.nan)
    true_asym_pct = np.where(eligible_joint, la_pct + el_pct, np.nan)
    arrays = (
        el_abs,
        el_pct,
        la_abs,
        la_pct,
        contrast_abs,
        contrast_pct,
        true_asym_abs,
        true_asym_pct,
    )
    output = []
    for values in arrays:
        finite = values[np.isfinite(values)]
        output.append(float(np.median(finite)) if finite.size else np.nan)
    return np.asarray(output, dtype=float)


def _prepare_groups(data: pd.DataFrame, source_kind: str) -> list[_Group]:
    required = {"climate_year", "enso_phase", "station", "value"}
    if source_kind == "model":
        required.update({"model", "grid_signature"})
    missing = required.difference(data.columns)
    if missing:
        raise KeyError(f"inference input missing columns: {sorted(missing)}")
    filtered = data[data["enso_phase"].isin(PHASES)].copy()
    groups: list[_Group] = []
    if source_kind == "observed":
        chunks = [("OBSERVED", filtered)]
        entity = "station"
    elif source_kind == "model":
        grid_seasons = (
            filtered.groupby(
                ["model", "grid_signature", "climate_year", "enso_phase"],
                as_index=False,
                dropna=False,
            )["value"]
            .median()
        )
        chunks = list(grid_seasons.groupby("model", sort=True))
        entity = "grid_signature"
    else:
        raise ValueError("source_kind must be 'observed' or 'model'")

    for name, chunk in chunks:
        labels_per_year = chunk.groupby("climate_year")["enso_phase"].nunique()
        if (labels_per_year > 1).any():
            raise ValueError(f"multiple ENSO labels for one climate year in {name}")
        labels = chunk.groupby("climate_year")["enso_phase"].first().sort_index()
        pivot = chunk.pivot_table(
            index="climate_year", columns=entity, values="value", aggfunc="median"
        ).reindex(labels.index)
        indices = {
            phase: np.flatnonzero(labels.to_numpy(dtype=str) == phase)
            for phase in PHASES
        }
        groups.append(
            _Group(str(name), pivot.to_numpy(dtype=float), indices)
        )
    return groups


def _aggregate_group_statistics(
    groups: list[_Group],
    indices_by_group: list[dict[str, np.ndarray]],
    *,
    minimum_seasons: int,
) -> np.ndarray:
    rows = [
        _group_statistics(group, indices, minimum_seasons=minimum_seasons)
        for group, indices in zip(groups, indices_by_group, strict=True)
    ]
    if not rows:
        return np.full(len(STAT_NAMES), np.nan)
    matrix = np.vstack(rows)
    output = np.full(matrix.shape[1], np.nan)
    for position in range(matrix.shape[1]):
        finite = matrix[:, position][np.isfinite(matrix[:, position])]
        if finite.size:
            output[position] = float(np.median(finite))
    return output


def _quantile_interval(values: np.ndarray, confidence_level: float) -> tuple[float, float, int]:
    finite = values[np.isfinite(values)]
    if not finite.size:
        return np.nan, np.nan, 0
    alpha = (1.0 - confidence_level) / 2.0
    return (
        float(np.quantile(finite, alpha)),
        float(np.quantile(finite, 1.0 - alpha)),
        int(finite.size),
    )


def _permutation_p(null_values: np.ndarray, observed: float) -> float:
    finite = null_values[np.isfinite(null_values)]
    if not finite.size or not np.isfinite(observed):
        return np.nan
    return float((1 + np.sum(np.abs(finite) >= abs(observed))) / (len(finite) + 1))


def infer_joint_phases(
    data: pd.DataFrame,
    *,
    source_kind: str,
    minimum_seasons: int,
    bootstrap_repetitions: int,
    permutation_repetitions: int,
    seed: int,
    confidence_level: float = 0.95,
) -> dict[str, object]:
    """Infer El Niño, La Niña, phase contrast, and true neutral asymmetry.

    The resampling unit is the management-season climate year. For model data,
    resampling occurs independently within model before the ensemble median.
    """
    groups = _prepare_groups(data, source_kind)
    original_indices = [group.indices for group in groups]
    point = _aggregate_group_statistics(
        groups, original_indices, minimum_seasons=minimum_seasons
    )
    rng = np.random.default_rng(seed)

    bootstrap = np.full((bootstrap_repetitions, len(STAT_NAMES)), np.nan)
    for repetition in range(bootstrap_repetitions):
        sampled = []
        for group in groups:
            sampled.append(
                {
                    phase: rng.choice(index, size=len(index), replace=True)
                    if len(index)
                    else index
                    for phase, index in group.indices.items()
                }
            )
        bootstrap[repetition] = _aggregate_group_statistics(
            groups, sampled, minimum_seasons=minimum_seasons
        )

    permutation = np.full((permutation_repetitions, len(STAT_NAMES)), np.nan)
    for repetition in range(permutation_repetitions):
        shuffled = []
        for group in groups:
            counts = {phase: len(group.indices[phase]) for phase in PHASES}
            pooled = np.concatenate([group.indices[phase] for phase in PHASES])
            permuted = rng.permutation(pooled)
            stop_el = counts["EL_NINO"]
            stop_la = stop_el + counts["LA_NINA"]
            shuffled.append(
                {
                    "EL_NINO": permuted[:stop_el],
                    "LA_NINA": permuted[stop_el:stop_la],
                    "NEUTRAL": permuted[stop_la:],
                }
            )
        permutation[repetition] = _aggregate_group_statistics(
            groups, shuffled, minimum_seasons=minimum_seasons
        )

    positions = {name: position for position, name in enumerate(STAT_NAMES)}
    responses: dict[str, dict[str, float | int]] = {}
    for phase, prefix in (("EL_NINO", "el"), ("LA_NINA", "la")):
        absolute_position = positions[f"{prefix}_absolute"]
        percent_position = positions[f"{prefix}_pct"]
        absolute_low, absolute_high, valid_bootstrap = _quantile_interval(
            bootstrap[:, absolute_position], confidence_level
        )
        percent_low, percent_high, _ = _quantile_interval(
            bootstrap[:, percent_position], confidence_level
        )
        counts = np.asarray([len(group.indices[phase]) for group in groups], dtype=int)
        neutral_counts = np.asarray(
            [len(group.indices["NEUTRAL"]) for group in groups], dtype=int
        )
        responses[phase] = {
            "response_absolute": float(point[absolute_position]),
            "response_pct": float(point[percent_position]),
            "ci_low_absolute": absolute_low,
            "ci_high_absolute": absolute_high,
            "ci_low_pct": percent_low,
            "ci_high_pct": percent_high,
            "permutation_p_pct": _permutation_p(
                permutation[:, percent_position], point[percent_position]
            ),
            "valid_bootstrap_repetitions": valid_bootstrap,
            "n_groups": int(len(groups)),
            "n_phase_min": int(counts.min()) if counts.size else 0,
            "n_phase_median": float(np.median(counts)) if counts.size else 0.0,
            "n_neutral_min": int(neutral_counts.min()) if neutral_counts.size else 0,
            "n_neutral_median": float(np.median(neutral_counts)) if neutral_counts.size else 0.0,
        }

    asymmetry: dict[str, float | int] = {}
    for name in (
        "phase_contrast_absolute",
        "phase_contrast_pct",
        "neutral_centered_asymmetry_absolute",
        "neutral_centered_asymmetry_pct",
    ):
        position = positions[name]
        low, high, valid = _quantile_interval(bootstrap[:, position], confidence_level)
        asymmetry[name] = float(point[position])
        asymmetry[f"{name}_ci_low"] = low
        asymmetry[f"{name}_ci_high"] = high
        asymmetry[f"{name}_permutation_p"] = _permutation_p(
            permutation[:, position], point[position]
        )
        asymmetry[f"{name}_valid_bootstrap"] = valid

    return {
        "responses": responses,
        "asymmetry": asymmetry,
        "resampling_unit": "management-season climate year",
        "bootstrap_repetitions": int(bootstrap_repetitions),
        "permutation_repetitions": int(permutation_repetitions),
        "confidence_level": float(confidence_level),
        "seed": int(seed),
    }

