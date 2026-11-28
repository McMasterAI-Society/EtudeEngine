"""Map raw ranker scores onto the 1–11 level scale using the matched (anchor) pieces."""
from __future__ import annotations

LEVEL_MIN, LEVEL_MAX = 1, 11


class LevelCalibrator:
    """Monotonic score → level mapping: interpolation between known anchors."""

    def fit(self, raw_scores: list[float], levels: list[int]) -> LevelCalibrator:
        """Learn the mapping from anchor pieces (raw score, true PSyllabus level)."""
        # TODO: sklearn.isotonic.IsotonicRegression(y_min=1, y_max=11, out_of_bounds="clip")
        #       fallback if too few anchors: map score ranks onto PSyllabus's level distribution.
        raise NotImplementedError

    def level(self, raw_score: float) -> float:
        """Calibrated level in [1, 11]."""
        raise NotImplementedError
