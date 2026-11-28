"""Output of anchoring: a player's skill on the 1–11 piece-difficulty scale."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SkillEstimate:
    """A player's skill from one performance, anchored on the piece's difficulty."""
    performance_id: str
    theta: float                         # skill on the difficulty scale (1–11)
    level_band: tuple[float, float]      # e.g. (theta - 1, theta + 1), clipped to [1, 11]
    difficulty: float                    # d used
    quality: float                       # q used (0–1)
    details: dict = field(default_factory=dict)
