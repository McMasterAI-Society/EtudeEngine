"""Fill in difficulty for every catalog piece without a true PSyllabus level."""
from __future__ import annotations

from assessment.difficulty.catalog.catalog import PieceCatalog
from assessment.difficulty.model.calibration import LevelCalibrator
from assessment.difficulty.model.ranker import DifficultyRanker
from assessment.difficulty.schema import DifficultyEstimate


def estimate_missing_difficulties(catalog: PieceCatalog, ranker: DifficultyRanker,
                                  calibrator: LevelCalibrator, features_by_score: dict) -> int:
    """Rank all pieces, calibrate on anchors, set model estimates; returns how many were filled.

    features_by_score: {score_id: piece_features(score MIDI)}.
    """
    # TODO:
    #   1. raw = {sid: ranker.score(f) for sid, f in features_by_score.items()}
    #   2. calibrator.fit([raw[p.score_id] for p in catalog.anchors()],
    #                     [p.difficulty.level for p in catalog.anchors()])
    #   3. for pieces without difficulty: catalog.set_difficulty(
    #          sid, DifficultyEstimate(calibrator.level(raw[sid]), "model", uncertainty=1.0))
    raise NotImplementedError
