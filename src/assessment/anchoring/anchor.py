"""Anchored skill: piece difficulty adjusted by how well it was played (Rasch form)."""
from __future__ import annotations

from assessment.anchoring.schema import SkillEstimate

Q_CLIP = (0.02, 0.98)      # avoid infinite logits at q = 0 or 1
LEVEL_RANGE = (1.0, 11.0)  # same scale as PSyllabus piece difficulty


def anchored_skill(performance_id: str, difficulty: float, quality: float, *,
                   scale: float = 1.0, band: float = 1.0) -> SkillEstimate:
    """Skill out of 11: theta = d + scale * log(q / (1 - q)), clipped to [1, 11].

    q = 0.5 means 'playing at the piece's level'; scale converts quality logits into
    difficulty levels (to tune on MAJEPPA labels).
    """
    # TODO: clip q to Q_CLIP; theta = d + scale * log(q / (1 - q)), clipped to LEVEL_RANGE;
    #       band = (theta - band, theta + band), each clipped to LEVEL_RANGE;
    #       return SkillEstimate(performance_id, theta, band, difficulty, quality)
    raise NotImplementedError
