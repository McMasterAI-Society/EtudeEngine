"""Iterate score–performance pairs by ID; MIDI and alignment load lazily on access."""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path

from assessment.performance.alignment import Alignment, load_alignment
from assessment.common.io import read_csv
from assessment.common.midi import MidiFile, read_midi


@lru_cache(maxsize=64)
def _cached_score(path: str) -> MidiFile:
    """Scores are shared by many performances, so keep recent ones in memory."""
    return read_midi(path)


@dataclass
class Pair:
    """One performance with its score, metadata row and alignment folder."""
    record: dict
    midi_dir: Path | None = None
    alignment_dir: Path | None = None

    @property
    def score_id(self) -> str:
        return self.record['score_id']

    @property
    def performance_id(self) -> str:
        return self.record['performance_id']

    @cached_property
    def performance(self) -> MidiFile:
        return read_midi(self.midi_dir / 'performance' / f'{self.performance_id}.mid')

    @property
    def score(self) -> MidiFile:
        return _cached_score(str(self.midi_dir / 'score' / f'{self.score_id}.mid'))

    @property
    def alignment_folder(self) -> Path:
        return self.alignment_dir / f'{self.score_id}_{self.performance_id}'

    @cached_property
    def alignment(self) -> Alignment:
        return load_alignment(self.alignment_folder)


class MajeppaIngestor:
    """Yields one Pair per record, in order."""

    def __init__(self, records, *, midi_dir=None, alignment_dir=None, limit=None):
        records = list(records)
        self.records = records[:limit] if limit is not None else records
        self.midi_dir = Path(midi_dir) if midi_dir else None
        self.alignment_dir = Path(alignment_dir) if alignment_dir else None

    def __len__(self):
        return len(self.records)

    def __iter__(self):
        for record in self.records:
            yield Pair(record, self.midi_dir, self.alignment_dir)

    @classmethod
    def from_batch(cls, batch_dir, *, midi_dir=None, limit=None):
        """Pairs listed in an aligner batch (batch_summary.csv + S_P folders)."""
        rows, _fields = read_csv(Path(batch_dir) / 'batch_summary.csv')
        return cls(rows, midi_dir=midi_dir, alignment_dir=batch_dir, limit=limit)

    @classmethod
    def from_metadata(cls, data_dir, *, levels=None, recording_types=None, limit=None):
        """Score-paired performances from MAJEPPA's metadata.csv, optionally filtered."""
        rows, _fields = read_csv(Path(data_dir) / 'metadata.csv')
        rows = [r for r in rows if r.get('score_id')
                and (levels is None or r.get('expertise_level') in levels)
                and (recording_types is None or r.get('recording_type') in recording_types)]
        return cls(rows, midi_dir=data_dir, limit=limit)
