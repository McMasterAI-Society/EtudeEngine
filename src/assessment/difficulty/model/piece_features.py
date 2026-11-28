"""Score-level difficulty features from a piece's MIDI (input to the ranker)."""
from __future__ import annotations

from assessment.common.midi import MidiFile


def piece_features(midi: MidiFile) -> dict[str, float]:
    """Numbers that tend to rise with difficulty.

    Candidates: notes per second, max/mean simultaneous notes (chord size), pitch range,
    mean |interval| and large-leap rate, fastest local note rate, duration.
    """
    # TODO: compute from midi.notes (onset_sec, pitch); group chords by onset (e.g. 35–50 ms).
    raise NotImplementedError
