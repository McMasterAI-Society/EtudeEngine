"""Match MAJEPPA scores to PSyllabus pieces by composer and title."""
from __future__ import annotations

from dataclasses import dataclass

from assessment.difficulty.catalog.psyllabus import PSyllabusPiece
from assessment.difficulty.schema import Piece


@dataclass
class Match:
    """A proposed MAJEPPA ↔ PSyllabus pairing."""
    score_id: str
    psyllabus_key: str
    level: int
    confidence: float    # 0–1; keep only confident matches as anchors


def normalize_composer(name: str) -> str:
    """Comparable composer key: lowercase surname, accents stripped.

    PSyllabus: "Faure G." / MAJEPPA: full canonical names (e.g. "Gabriel Fauré").
    """
    # TODO: unicodedata.normalize("NFKD") + drop accents; take surname (PSyllabus: before
    #       the initial; MAJEPPA: last word); lowercase.
    raise NotImplementedError


def normalize_title(title: str) -> str:
    """Comparable title key: piece type + numbers (opus, no.), lowercase, no punctuation."""
    # TODO: lowercase, unify "op."/"opus", "no."/"nr"/"#", strip keys like "a minor" if noisy.
    raise NotImplementedError


def match_pieces(pieces: list[Piece], psyllabus: list[PSyllabusPiece], *,
                 min_confidence: float = 0.8) -> list[Match]:
    """Best PSyllabus match per MAJEPPA score, above min_confidence."""
    # TODO: block by normalized composer, then score title similarity
    #       (e.g. difflib.SequenceMatcher on normalized titles + exact opus/number agreement).
    raise NotImplementedError
