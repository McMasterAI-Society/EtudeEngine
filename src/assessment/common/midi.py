"""Standard-library MIDI reader: notes, sustain pedal and time signatures."""
from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from pathlib import Path

MIDI_DEFAULT_US_PER_QUARTER = 500_000  # 120 bpm when a file has no tempo event


@dataclass(frozen=True)
class Note:
    """One note; times exactly as stored in the file (no trimming or quantising)."""
    onset_sec: float
    onset_beat: float          # quarter notes (ticks / ticks per quarter)
    pitch: int
    velocity: int
    offset_sec: float | None   # None if the file never releases the note


@dataclass
class MidiFile:
    """Parsed MIDI file. Notes are sorted by onset; zero-length notes are kept."""
    file_id: str
    notes: list[Note]
    pedal: list[tuple[float, int]] = field(default_factory=list)            # (sec, CC64 value)
    time_signatures: list[tuple[float, float, int, int]] = field(default_factory=list)  # (sec, beat, num, den)
    ticks_per_quarter: int = 0


def _read_varlen(data, pos):
    value = 0
    while True:
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos


def _tick_converter(tempos, division):
    """Return a function mapping ticks to seconds under the file's tempo map."""
    tempos = sorted(tempos)
    if not tempos or tempos[0][0] != 0:
        tempos.insert(0, (0, MIDI_DEFAULT_US_PER_QUARTER))
    marks, seconds = [], 0.0
    for i, (t, us) in enumerate(tempos):
        if i:
            prev_t, prev_us = tempos[i-1]
            seconds += (t - prev_t) * prev_us / 1e6 / division
        marks.append((t, seconds, us))
    mark_ticks = [m[0] for m in marks]

    def to_seconds(tick):
        t0, s0, us = marks[bisect.bisect_right(mark_ticks, tick) - 1]
        return s0 + (tick - t0) * us / 1e6 / division
    return to_seconds


def read_midi(path) -> MidiFile:
    """Parse a Standard MIDI File (SMPTE time division not supported)."""
    path = Path(path)
    data = path.read_bytes()
    if data[:4] != b'MThd':
        raise ValueError(f'Not a MIDI file: {path}')
    header_len = int.from_bytes(data[4:8], 'big')
    n_tracks = int.from_bytes(data[10:12], 'big')
    division = int.from_bytes(data[12:14], 'big')
    if division & 0x8000:
        raise ValueError(f'SMPTE time division not supported: {path}')

    pos = 8 + header_len
    onsets, offsets, pedal, tempos, signatures = [], {}, [], [], []
    for _ in range(n_tracks):
        if data[pos:pos+4] != b'MTrk':
            raise ValueError(f'Bad track chunk in {path}')
        end = pos + 8 + int.from_bytes(data[pos+4:pos+8], 'big')
        pos += 8
        tick, status = 0, None
        active = {}                              # (channel, pitch) -> queue of onset indices
        while pos < end:
            delta, pos = _read_varlen(data, pos)
            tick += delta
            byte = data[pos]
            if byte == 0xFF:                     # meta event
                kind = data[pos+1]
                size, pos = _read_varlen(data, pos+2)
                if kind == 0x51 and size == 3:
                    tempos.append((tick, int.from_bytes(data[pos:pos+3], 'big')))
                elif kind == 0x58 and size >= 2:
                    signatures.append((tick, data[pos], 2 ** data[pos+1]))
                pos += size
                status = None
                continue
            if byte in (0xF0, 0xF7):             # sysex
                size, pos = _read_varlen(data, pos+1)
                pos += size
                status = None
                continue
            if byte & 0x80:                      # new status byte; else running status
                status = byte
                pos += 1
            elif status is None:
                raise ValueError(f'Running status without a status byte in {path}')
            kind, channel = status & 0xF0, status & 0x0F
            n_data = 1 if kind in (0xC0, 0xD0) else 2
            args = data[pos:pos+n_data]
            pos += n_data
            if kind == 0x90 and args[1] > 0:
                active.setdefault((channel, args[0]), []).append(len(onsets))
                onsets.append((tick, args[0], args[1]))
            elif kind == 0x80 or (kind == 0x90 and args[1] == 0):
                queue = active.get((channel, args[0]))
                if queue:
                    offsets[queue.pop(0)] = tick
            elif kind == 0xB0 and args[0] == 64:
                pedal.append((tick, args[1]))
        pos = end

    to_sec = _tick_converter(tempos, division)
    notes = [Note(to_sec(tick), tick / division, pitch, velocity,
                  to_sec(offsets[i]) if i in offsets else None)
             for i, (tick, pitch, velocity) in enumerate(onsets)]
    notes.sort(key=lambda n: (n.onset_sec, n.onset_beat, n.pitch, n.velocity))
    return MidiFile(
        file_id=path.stem,
        notes=notes,
        pedal=sorted((to_sec(t), v) for t, v in pedal),
        time_signatures=sorted((to_sec(t), t / division, num, den) for t, num, den in signatures),
        ticks_per_quarter=division,
    )
