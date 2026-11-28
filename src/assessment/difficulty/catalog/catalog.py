"""The piece catalog: every MAJEPPA score with its difficulty, behind one interface.

File-backed for now (CSV); a web service can wrap the same methods later.
"""
from __future__ import annotations

from pathlib import Path

from assessment.difficulty.schema import DifficultyEstimate, Piece

DEFAULT_PATH = Path("results/catalog.csv")


class PieceCatalog:
    """Look up pieces and their difficulty by MAJEPPA score_id."""

    def __init__(self, pieces: list[Piece]):
        self._pieces = {p.score_id: p for p in pieces}

    # --- building ---------------------------------------------------------------
    @classmethod
    def from_majeppa(cls, metadata_csv: Path = Path("data/majeppa/metadata.csv")) -> PieceCatalog:
        """One Piece per distinct score_id (composer + piece_title from metadata)."""
        # TODO: read metadata.csv, keep rows with score_id, dedupe by score_id.
        raise NotImplementedError

    def apply_matches(self, matches) -> int:
        """Attach PSyllabus levels as true-label difficulties; returns how many matched."""
        # TODO: for each Match: piece.psyllabus_key = m.psyllabus_key;
        #       piece.difficulty = DifficultyEstimate(m.level, source="psyllabus", uncertainty=0)
        raise NotImplementedError

    # --- serving ------------------------------------------------------------------
    def pieces(self) -> list[Piece]:
        return list(self._pieces.values())

    def get(self, score_id: str) -> Piece:
        return self._pieces[score_id]

    def get_difficulty(self, score_id: str) -> DifficultyEstimate | None:
        return self._pieces[score_id].difficulty

    def set_difficulty(self, score_id: str, estimate: DifficultyEstimate) -> None:
        self._pieces[score_id].difficulty = estimate

    def anchors(self) -> list[Piece]:
        """Pieces with a true PSyllabus level (used to calibrate the model)."""
        return [p for p in self._pieces.values()
                if p.difficulty is not None and p.difficulty.source == "psyllabus"]

    # --- persistence --------------------------------------------------------------
    def save(self, path: Path = DEFAULT_PATH) -> None:
        """Write score_id, composer, title, psyllabus_key, level, source, uncertainty."""
        # TODO: assessment.common.io.write_csv(path, rows, headers)
        raise NotImplementedError

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> PieceCatalog:
        # TODO: assessment.common.io.read_csv(path) -> Pieces with DifficultyEstimate
        raise NotImplementedError
