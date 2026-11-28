"""Repeats, skips and uncertain stretches; splits a performance into score traversals."""
from __future__ import annotations

import bisect
import statistics
from collections import defaultdict
from dataclasses import dataclass

from assessment.performance import config as cfg
from assessment.common.utils import number


@dataclass
class Structure:
    """Where the player went in the score, and the resulting traversals ("runs")."""
    matcher: str
    jumps: list
    forward_skips: list
    clusters: list
    uncertain_windows: list
    runs: list
    cuts: list


def merge_windows(windows, pad=cfg.UNCERTAIN_WINDOW_PAD_SEC):
    """Pad and merge uncertain performance-time intervals."""
    prepared = []
    for entry in windows:
        start = number(entry.get('start'))
        end = number(entry.get('end'))
        if start is not None and end is not None and end >= start:
            prepared.append((max(0.0, start-pad), end+pad))
    merged = []
    for start, end in sorted(prepared):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def in_windows(t, windows):
    return t is not None and any(lo <= t <= hi for lo, hi in windows)


def count_performance_notes_in_windows(perfs, windows):
    return sum(in_windows(t, windows) for t, _pitch in perfs.values())


def _score_position_over_time(rows):
    """[(time, median score beat)] of matched notes, grouped by rounded onset."""
    grouped = defaultdict(list)
    for r in rows:
        if r.get('label') != 'match':
            continue
        t, b = number(r.get('performance_onset_sec')), number(r.get('score_onset_beat'))
        if t is not None and b is not None:
            grouped[round(t, cfg.JUMP_TIME_GROUP_DECIMALS)].append(b)
    return [(t, statistics.median(v)) for t, v in sorted(grouped.items())]


def jump_events(rows, min_drop=cfg.REPEAT_MIN_BACKWARD_BEATS):
    """Backward jumps in score position: likely repeats or restarts."""
    ordered = _score_position_over_time(rows)
    return [
        {'from_sec': t1, 'to_sec': t2, 'from_beat': b1, 'to_beat': b2,
         'jump_beats': b1 - b2}
        for (t1, b1), (t2, b2) in zip(ordered, ordered[1:])
        if b1 - b2 >= min_drop
    ]


def improbable_forward_skips(rows, min_beats=cfg.SKIP_MIN_FORWARD_BEATS,
                             fastest_seconds_per_beat=cfg.SKIP_MAX_SEC_PER_BEAT):
    """Forward leaps too fast to have been played: skipped passage or matcher glitch."""
    ordered = _score_position_over_time(rows)
    return [
        {'from_sec': t1, 'to_sec': t2, 'from_beat': b1, 'to_beat': b2,
         'jump_beats': b2-b1}
        for (t1, b1), (t2, b2) in zip(ordered, ordered[1:])
        if (b2-b1 >= min_beats and (t2-t1)/(b2-b1) < fastest_seconds_per_beat)
    ]


def build_runs(rows, jumps, scores, forward_skips=None, uncertain_windows=None):
    """Cut matched notes into continuous traversals; each run owns the score span it covered."""
    windows = uncertain_windows or []
    cuts = sorted({j['to_sec'] for j in list(jumps) + list(forward_skips or [])}
                  | {bound for window in windows for bound in window})
    by_run = defaultdict(list)
    for row in rows:
        if row.get('label') != 'match':
            continue
        t = number(row.get('performance_onset_sec'))
        b = number(row.get('score_onset_beat'))
        if t is not None and b is not None and not in_windows(t, windows):
            by_run[bisect.bisect_right(cuts, t)].append(row)

    score_sorted = sorted((b, sid) for sid, (b, _pitch) in scores.items())
    score_beats = [beat for beat, _ in score_sorted]
    runs = []
    for index, matches in sorted(by_run.items()):
        beats = [number(r['score_onset_beat']) for r in matches]
        beats = [b for b in beats if b is not None]
        if not beats:
            continue
        lo, hi = min(beats), max(beats)
        left = bisect.bisect_left(score_beats, lo - 1e-4)
        right = bisect.bisect_right(score_beats, hi + 1e-4)
        expected_ids = {sid for _, sid in score_sorted[left:right]}
        matched_ids = [(r.get('score_note_id') or '').strip() for r in matches]
        matched_set = set(matched_ids) & expected_ids
        times = [number(r.get('performance_onset_sec')) for r in matches]
        times = [t for t in times if t is not None]
        runs.append({
            'run_index': index, 'matches': matches, 'lo': lo, 'hi': hi,
            'start_sec': min(times), 'end_sec': max(times),
            'expected_ids': expected_ids, 'matched_score_ids': matched_set,
            'missing_ids': expected_ids - matched_set,
            'reused_ids_in_run': len(matched_ids) - len(set(matched_ids)),
        })
    return runs, cuts


def analyze_structure(alignment, record, scores, *,
                      min_backward_beats=cfg.REPEAT_MIN_BACKWARD_BEATS) -> Structure:
    """Find repeats, skips and uncertain stretches, then build the runs."""
    final = alignment.final_rows
    jumps = jump_events(final, min_backward_beats)
    forward_skips = improbable_forward_skips(final)
    clusters = (alignment.decision.get('suspicion') or {}).get('major_clusters') or []
    matcher = alignment.decision.get('matcher') or record.get('matcher', '')
    # The repeat-aware matcher resolves gaps itself; only exclude them otherwise.
    windows = merge_windows(clusters) if matcher != 'repeat_hmm' else []
    runs, cuts = build_runs(final, jumps, scores, forward_skips, windows)
    return Structure(matcher, jumps, forward_skips, clusters, windows, runs, cuts)
