"""Read the PSyllabus labels (new_clean_data.json) into simple records."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PSyllabusPiece:
    """One labelled piece from PSyllabus."""
    key: str             # dict key, e.g. "Faure G.Barcarolle 9 - op 101 A minor"
    composer: str        # "Faure G." (surname + initial)
    title: str           # PS_title, e.g. "Barcarolle 9 - op 101 A minor"
    level: int           # ps_rating, 1–11
    syllabus: str        # source exam board/syllabus
    youtube_link: str


def load_psyllabus(path: Path = Path("data/psyllabus/new_clean_data.json")) -> list[PSyllabusPiece]:
    """All 7,901 labelled pieces.

    Fields per entry (checked 2026-11-27): composer, PS_title, ps_rating (str), syllabus,
    youtube_link, related_entries {board: level}, duration, period.
    """
    # TODO: json.load(path) -> {key: entry}; build PSyllabusPiece(key, entry["composer"],
    #       entry["PS_title"], int(entry["ps_rating"]), entry["syllabus"], entry["youtube_link"])
    raise NotImplementedError
