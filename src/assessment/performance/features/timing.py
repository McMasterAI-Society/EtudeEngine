"""Timing features: onset irregularity and local tempo instability, per traversal."""
from __future__ import annotations

import bisect
import math
import statistics
from collections import defaultdict

from assessment.performance import config as cfg
from assessment.common.utils import median, number


def _plausible_tempo(sec_per_beat):
    return cfg.MIN_SEC_PER_BEAT <= sec_per_beat <= cfg.MAX_SEC_PER_BEAT


def make_anchors(matches, *, exact_pitch_only=cfg.ANCHOR_EXACT_PITCH_ONLY,
                 chord_spread_limit=cfg.ANCHOR_MAX_CHORD_SPREAD_SEC):
    """(score beat, median onset) per beat, skipping widely split chords; plus inversion counts."""
    grouped = defaultdict(list)
    for r in matches:
        beat = number(r.get('score_onset_beat'))
        t = number(r.get('performance_onset_sec'))
        sp = number(r.get('score_pitch'))
        pp = number(r.get('performance_pitch'))
        if beat is None or t is None:
            continue
        if exact_pitch_only and (sp is None or pp is None or sp != pp):
            continue
        grouped[round(beat, 4)].append(t)
    dropped_spread = 0
    points = []
    for beat, times in sorted(grouped.items()):
        if max(times) - min(times) > chord_spread_limit:
            dropped_spread += 1
            continue
        points.append((beat, statistics.median(times)))
    inversions = sum(t2 <= t1 for (_b1, t1), (_b2, t2) in zip(points, points[1:]))
    return points, {'wide_onset_groups': dropped_spread, 'time_inversions': inversions}


def project_beat(beat, anchor_points, *, max_neighbor_distance=cfg.NEIGHBOR_MAX_DISTANCE_BEATS):
    """Expected onset of a score beat by interpolating nearby anchors (currently unused)."""
    if len(anchor_points) < 2:
        return None
    bs = [item[0] for item in anchor_points]
    i = bisect.bisect_left(bs, round(beat, 4))
    if i < len(bs) and abs(bs[i] - beat) <= 1e-4:
        return anchor_points[i][1]
    if i <= 0 or i >= len(bs):
        return None
    bl, tl = anchor_points[i-1]
    br, tr = anchor_points[i]
    if (beat - bl > max_neighbor_distance or br - beat > max_neighbor_distance
            or br <= bl or tr <= tl):
        return None
    sec_per_beat = (tr - tl) / (br - bl)
    if not _plausible_tempo(sec_per_beat):
        return None
    return tl + (beat - bl) * sec_per_beat


def project_beat_with_tempo(beat, anchor_points, *,
                            max_neighbor_distance=cfg.NEIGHBOR_MAX_DISTANCE_BEATS):
    """Expected onset of a score beat and the local seconds per beat, or (None, None)."""
    if len(anchor_points) < 2:
        return None, None
    bs = [p[0] for p in anchor_points]
    i = bisect.bisect_left(bs, round(beat, 4))
    if i < len(bs) and abs(bs[i]-beat) <= 1e-4:
        # The beat is itself an anchor (another note at this onset was played correctly).
        center = anchor_points[i][1]
        possibilities = []
        if i > 0:
            b0, t0 = anchor_points[i-1]
            if 0 < beat-b0 <= max_neighbor_distance and center > t0:
                possibilities.append((center-t0)/(beat-b0))
        if i+1 < len(anchor_points):
            b1, t1 = anchor_points[i+1]
            if 0 < b1-beat <= max_neighbor_distance and t1 > center:
                possibilities.append((t1-center)/(b1-beat))
        candidates = [v for v in possibilities if _plausible_tempo(v)]
        return (center, median(candidates)) if candidates else (None, None)
    if i == 0 or i == len(bs):
        return None, None
    b0, t0 = anchor_points[i-1]
    b1, t1 = anchor_points[i]
    if (b1 <= b0 or t1 <= t0 or beat-b0 > max_neighbor_distance
            or b1-beat > max_neighbor_distance):
        return None, None
    slope = (t1-t0)/(b1-b0)
    if not _plausible_tempo(slope):
        return None, None
    return t0+(beat-b0)*slope, slope


def trimmed_mean_abs(values, trim_fraction=cfg.RESIDUAL_TRIM_FRACTION):
    """Mean |value| after dropping the largest few (robust to single glitches)."""
    if not values:
        return None
    ordered = sorted(abs(v) for v in values)
    count_to_keep = max(1, len(ordered)-int(math.floor(trim_fraction*len(ordered))))
    return statistics.mean(ordered[:count_to_keep])


def robust_line(points):
    """Theil–Sen fit: (seconds per beat, intercept), or None if the tempo is implausible."""
    slopes = []
    for i, (b1, t1) in enumerate(points):
        for b2, t2 in points[i+1:]:
            if b2 - b1 >= cfg.ROBUST_LINE_MIN_BEAT_GAP:
                slopes.append((t2-t1)/(b2-b1))
    if not slopes:
        return None
    slope = statistics.median(slopes)
    if not _plausible_tempo(slope):
        return None
    intercept = statistics.median(t - slope*b for b, t in points)
    return slope, intercept


def timing_metrics(runs, *, min_residuals=cfg.MIN_RESIDUALS, min_tempo_steps=cfg.MIN_TEMPO_STEPS):
    """timing_irregularity_beats and tempo_instability_log, plus their sample counts."""
    abs_residual_beats, local_tempo_changes = [], []
    inversions, dropped_onset_groups, n_anchor_points = 0, 0, 0
    search, reach = cfg.RESIDUAL_NEIGHBOR_SEARCH, cfg.RESIDUAL_NEIGHBOR_MAX_BEATS
    context_n, step = cfg.RESIDUAL_CONTEXT_EACH_SIDE, cfg.TEMPO_WINDOW_STEP_BEATS
    half = cfg.TEMPO_WINDOW_HALF_WIDTH_BEATS
    for run in runs:
        points, flags = make_anchors(run['matches'])
        inversions += flags['time_inversions']
        dropped_onset_groups += flags['wide_onset_groups']
        n_anchor_points += len(points)
        n = len(points)
        if n < cfg.RUN_MIN_ANCHORS:
            continue

        # Irregularity: each anchor vs a local line fitted to its neighbours (not itself).
        for i, (beat, sec) in enumerate(points):
            left = [p for p in points[max(0, i-search):i] if beat - p[0] <= reach]
            right = [p for p in points[i+1:min(n, i+1+search)] if p[0] - beat <= reach]
            if len(left) < cfg.RESIDUAL_MIN_EACH_SIDE or len(right) < cfg.RESIDUAL_MIN_EACH_SIDE:
                continue
            regression = robust_line(left[-context_n:] + right[:context_n])
            if regression is None:
                continue
            slope, intercept = regression
            abs_residual_beats.append(abs(sec - (slope*beat+intercept))/slope)

        # Instability: tempo in sliding score-beat windows, compared between neighbours.
        b0, b1 = points[0][0], points[-1][0]
        window_estimates = []
        center = b0 + step
        while center <= b1 - step:
            lo = bisect.bisect_left(points, (center-half, -math.inf))
            hi = bisect.bisect_right(points, (center+half, math.inf))
            candidates = points[lo:hi]
            if (len(candidates) >= cfg.TEMPO_WINDOW_MIN_ANCHORS
                    and candidates[-1][0]-candidates[0][0] >= cfg.TEMPO_WINDOW_MIN_SPAN_BEATS):
                max_gap = max((bb-ba for (ba, _ta), (bb, _tb) in zip(candidates, candidates[1:])), default=0)
                if max_gap <= cfg.TEMPO_WINDOW_MAX_GAP_BEATS:
                    regression = robust_line(candidates)
                    if regression is not None:
                        window_estimates.append((center, regression[0]))
            center += step
        for (c1, s1), (c2, s2) in zip(window_estimates, window_estimates[1:]):
            if c2-c1 <= cfg.TEMPO_NEIGHBOR_MAX_STEP_BEATS:
                local_tempo_changes.append(abs(math.log(s2/s1)))

    return {
        'timing_irregularity_beats': trimmed_mean_abs(abs_residual_beats) if len(abs_residual_beats) >= min_residuals else None,
        'tempo_instability_log': median(local_tempo_changes) if len(local_tempo_changes) >= min_tempo_steps else None,
        'timing_residual_samples': len(abs_residual_beats),
        'tempo_change_samples': len(local_tempo_changes),
        'distinct_score_onset_anchors': n_anchor_points,
        'timing_time_inversions': inversions,
        'timing_wide_chord_anchors_skipped': dropped_onset_groups,
    }
