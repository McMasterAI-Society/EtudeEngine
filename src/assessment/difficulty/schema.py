"""Objects passed between the catalog and the difficulty model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Piece:
    """One piece in the catalog (a MAJEPPA score, possibly matched to PSyllabus)."""
    score_id: str                        # MAJEPPA S_XXXX
    composer: str
    title: str
    psyllabus_key: str | None = None     # key in new_clean_data.json, if matched
    difficulty: DifficultyEstimate | None = None


@dataclass
class DifficultyEstimate:
    """A piece's difficulty on the PSyllabus 1–11 scale."""
    level: float                         # 1–11 (float: model estimates can fall between levels)
    source: str                          # "psyllabus" (true label) or "model" (ranked + calibrated)
    uncertainty: float | None = None     # e.g. ±1 level for model estimates
