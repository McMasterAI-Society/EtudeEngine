"""Difficulty rankers: give each piece a raw score where higher = harder (order matters, not scale)."""
from __future__ import annotations

from typing import Protocol


class DifficultyRanker(Protocol):
    """Anything that can be trained on labelled pieces and score new ones."""

    def fit(self, features: list[dict[str, float]], levels: list[int]) -> DifficultyRanker: ...

    def score(self, features: dict[str, float]) -> float: ...


class FeatureRanker:
    """Fallback ranker trained on PSyllabus levels from simple piece features."""

    def fit(self, features: list[dict[str, float]], levels: list[int]) -> FeatureRanker:
        # TODO: e.g. linear/ordinal regression on standardized features (sklearn), or a
        #       pairwise ranking model; evaluate with Kendall tau on a held-out split.
        raise NotImplementedError

    def score(self, features: dict[str, float]) -> float:
        raise NotImplementedError


class PSyllabusModelRanker:
    """Wrapper for the PSyllabus authors' difficulty model, IF it is public (unverified).

    Ramoneda, Lee, Jeong, Valero-Mas & Serra (2025). "Can Audio Reveal Music Performance
    Difficulty? Insights from the Piano Syllabus Dataset." IEEE/ACM TASLP.
    Paper: https://arxiv.org/abs/2403.03947 · Data: https://zenodo.org/records/14794592
    Best model: Kendall tau_c 0.78 (rank agreement with true levels), but only ~37% exact-level
    accuracy -> use its scores for ORDER, then calibrate to levels (calibration.py).
    Input is audio features (CQT) and/or transcribed piano roll, not score MIDI.
    """

    def fit(self, features, levels):
        return self   # pretrained

    def score(self, features) -> float:
        raise NotImplementedError("Check whether the PSyllabus model weights/code are released.")
