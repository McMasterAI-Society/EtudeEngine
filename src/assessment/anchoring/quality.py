"""Turn a performance's feature row into a quality score q in (0, 1)."""
from __future__ import annotations

# Direction per feature: +1 = higher is better, -1 = higher is worse.
FEATURE_DIRECTIONS = {
    "missing_note_rate": -1, "extra_note_rate": -1, "possible_wrong_note_rate": -1,
    "timing_irregularity_beats": -1, "tempo_instability_log": -1, "chord_onset_spread_ms": -1,
    "velocity_range_p5_p95": +1, "dynamics_following_rho": +1,
}


def performance_quality(row: dict, peers: list[dict] | None = None) -> float:
    """q for one row of performance_features.csv (blank features are skipped).

    Demo idea: percentile of a combined, direction-signed score among peer performances
    of the same piece (peers), or among all performances if the piece has too few.
    """
    # TODO: z-score each valid feature against peers, sign by FEATURE_DIRECTIONS, average,
    #       convert to a percentile -> q; clip to (0.02, 0.98) before anchoring.
    raise NotImplementedError
