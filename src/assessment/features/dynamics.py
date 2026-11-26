"""Dynamics features: velocity range and how loudness follows the score, per traversal."""
from __future__ import annotations

import bisect
import statistics
from collections import defaultdict

from assessment.config import config as cfg
from assessment.structure import in_windows
from assessment.utils import median, number


def velocity_lookup(notes, midi_notes, *, by, tolerance):
    """Map aligned note IDs to MIDI velocity by same pitch + nearest onset.

    notes: {id: (position, pitch)}; by: 'onset_sec' (performance) or 'onset_beat' (score).
    Returns ({id: velocity}, fraction of notes joined).
    """
    by_pitch = defaultdict(list)
    for note in midi_notes:
        by_pitch[note.pitch].append((getattr(note, by), note.velocity))
    keys = {pitch: [c[0] for c in sorted(cands)] for pitch, cands in by_pitch.items()}
    vels = {pitch: [c[1] for c in sorted(cands)] for pitch, cands in by_pitch.items()}
    found = {}
    for note_id, (position, pitch) in notes.items():
        ks = keys.get(pitch)
        if not ks:
            continue
        i = bisect.bisect_left(ks, position)
        best = min((j for j in (i-1, i) if 0 <= j < len(ks)), key=lambda j: abs(ks[j]-position))
        if abs(ks[best] - position) <= tolerance:
            found[note_id] = vels[pitch][best]
    return found, (len(found)/len(notes) if notes else 0.0)


def _ranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j+1 < len(order) and values[order[j+1]] == values[order[i]]:
            j += 1
        for k in range(i, j+1):
            ranks[order[k]] = (i + j) / 2      # average rank for ties
        i = j + 1
    return ranks


def spearman(x, y):
    """Rank correlation; None if fewer than 3 points or either side is constant."""
    if len(x) < 3:
        return None
    try:
        return statistics.correlation(_ranks(x), _ranks(y))
    except statistics.StatisticsError:
        return None


def dynamics_metric(runs, perf_velocity, score_velocity, perfs, excluded_windows=None, *,
                    window_beats=cfg.DYNAMICS_WINDOW_BEATS, min_notes=cfg.DYNAMICS_MIN_NOTES,
                    min_windows=cfg.DYNAMICS_MIN_WINDOWS):
    """velocity_range_p5_p95 over played notes; dynamics_following_rho averaged over runs."""
    windows = excluded_windows or []
    vels = sorted(v for pid, v in perf_velocity.items()
                  if pid in perfs and not in_windows(perfs[pid][0], windows))

    def percentile(p):                          # nearest-rank, on the sorted list
        return vels[min(len(vels)-1, int(round(p*(len(vels)-1))))]

    rhos, weights = [], []
    for run in runs:
        per_window = defaultdict(lambda: ([], []))
        for row in run['matches']:
            sid = (row.get('score_note_id') or '').strip()
            pid = (row.get('performance_note_id') or '').strip()
            beat = number(row.get('score_onset_beat'))
            sp, pp = number(row.get('score_pitch')), number(row.get('performance_pitch'))
            if beat is None or sp is None or sp != pp:
                continue
            if sid in score_velocity and pid in perf_velocity:
                performed, written = per_window[int(beat // window_beats)]
                performed.append(perf_velocity[pid])
                written.append(score_velocity[sid])
        if len(per_window) < min_windows:
            continue
        order = sorted(per_window)
        rho = spearman([median(per_window[k][0]) for k in order],
                       [median(per_window[k][1]) for k in order])
        if rho is not None:
            rhos.append(rho)
            weights.append(len(order))

    low, high = cfg.VELOCITY_RANGE_PERCENTILES
    mean_v = statistics.mean(vels) if vels else 0
    return {
        'velocity_range_p5_p95': (percentile(high) - percentile(low)) if len(vels) >= min_notes else None,
        'dynamics_following_rho': (sum(r*w for r, w in zip(rhos, weights)) / sum(weights)) if rhos else None,
        'velocity_notes': len(vels),
        'velocity_cv': statistics.pstdev(vels) / mean_v if len(vels) >= 2 and mean_v > 0 else None,
        'dynamics_windows': sum(weights),
        'dynamics_runs_used': len(rhos),
    }


def dynamics_for_pair(pair, structure, scores, perfs):
    """Join MIDI velocities to the aligned notes and compute dynamics; never raises on bad MIDI.

    Returns (metrics, join_info) where join_info feeds validity and diagnostics.
    """
    info = {'perf_velocity_join_rate': 0.0, 'score_velocity_join_rate': 0.0,
            'score_velocity_distinct': 0, 'dynamics_error': ''}
    metrics = {name: None for name in cfg.DYNAMICS_FEATURES}
    metrics.update(velocity_notes=0, velocity_cv=None, dynamics_windows=0, dynamics_runs_used=0)
    if pair.midi_dir is None:
        info['dynamics_error'] = 'no_midi_dir_given'
        return metrics, info
    score_velocity = {}
    try:
        perf_notes = pair.performance.notes
        score_notes = pair.score.notes
        perf_velocity, info['perf_velocity_join_rate'] = velocity_lookup(
            perfs, perf_notes, by='onset_sec', tolerance=cfg.PERF_VELOCITY_JOIN_TOL_SEC)
        score_velocity, info['score_velocity_join_rate'] = velocity_lookup(
            scores, score_notes, by='onset_beat', tolerance=cfg.SCORE_VELOCITY_JOIN_TOL_BEATS)
        metrics = dynamics_metric(structure.runs, perf_velocity, score_velocity, perfs,
                                  structure.uncertain_windows)
    except (OSError, ValueError, IndexError) as exc:
        info['dynamics_error'] = f'midi_read_failed:{type(exc).__name__}'
    info['score_velocity_distinct'] = len(set(score_velocity.values()))
    return metrics, info
