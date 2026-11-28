"""Pitch features: missing, extra and wrong-note rates over the observed score spans."""
from __future__ import annotations

import bisect

from assessment.performance import config as cfg
from assessment.performance.features.timing import make_anchors, project_beat_with_tempo
from assessment.performance.structure import count_performance_notes_in_windows, in_windows
from assessment.common.utils import number


def substitution_candidates(runs, scores, selected_rows, *, tolerance_sec=cfg.SUBSTITUTION_MAX_SEC,
                            tolerance_beats=cfg.SUBSTITUTION_BEATS, excluded_windows=None):
    """Pair missed score notes with nearby wrong-pitch extra notes (one-to-one, per traversal)."""
    windows = excluded_windows or []
    max_dist = cfg.SUBSTITUTION_MAX_PITCH_DIST
    insertions = {}
    for row in selected_rows:
        if row.get('label') == 'insertion' and row.get('performance_note_id'):
            t = number(row.get('performance_onset_sec'))
            pitch = number(row.get('performance_pitch'))
            if t is not None and pitch is not None and not in_windows(t, windows):
                insertions[row['performance_note_id']] = (t, int(pitch))
    sorted_insertions = sorted((t, pid, pitch) for pid, (t, pitch) in insertions.items())
    times = [x[0] for x in sorted_insertions]
    pairs, estimated_missing = [], 0
    for run in runs:
        anchors, _ = make_anchors(run['matches'])
        for sid in run['missing_ids']:
            beat, score_pitch = scores[sid]
            expected_t, sec_per_beat = project_beat_with_tempo(beat, anchors)
            if expected_t is None or sec_per_beat is None:
                continue
            estimated_missing += 1
            window = min(tolerance_sec, max(cfg.SUBSTITUTION_MIN_WINDOW_SEC, tolerance_beats*sec_per_beat))
            lower = bisect.bisect_left(times, expected_t-window)
            upper = bisect.bisect_right(times, expected_t+window)
            for t, pid, perf_pitch in sorted_insertions[lower:upper]:
                if t < run['start_sec']-window or t > run['end_sec']+window:
                    continue                     # stay inside this traversal
                dist = abs(perf_pitch-score_pitch)
                if dist == 0 or dist > max_dist:
                    continue
                cost = abs(t-expected_t)/window + dist/float(max_dist)
                pairs.append((cost, run['run_index'], sid, pid, expected_t, t))
    pairs.sort()
    taken_missing, taken_perf, chosen = set(), set(), []
    for _cost, run_index, sid, pid, expected_t, performed_t in pairs:
        key = (run_index, sid)
        if key in taken_missing or pid in taken_perf:
            continue
        taken_missing.add(key)
        taken_perf.add(pid)
        chosen.append((run_index, sid, pid, expected_t, performed_t))
    return chosen, {
        'projectable_missing_notes': estimated_missing,
        'possible_substitution_count': len(chosen),
        'substitution_tolerance_beats': tolerance_beats,
        'substitution_max_tolerance_sec': tolerance_sec,
    }


def pitch_metrics(alignment, structure, scores, perfs, *, tolerance_sec=cfg.SUBSTITUTION_MAX_SEC,
                  tolerance_beats=cfg.SUBSTITUTION_BEATS):
    """The three pitch rates, plus the counts behind them (for validity and diagnostics)."""
    runs, windows = structure.runs, structure.uncertain_windows
    final_rows, baseline_rows = alignment.final_rows, alignment.baseline_rows

    excluded_note_count = count_performance_notes_in_windows(perfs, windows)
    evaluable_perf = len(perfs) - excluded_note_count
    score_opportunities = sum(len(r['expected_ids']) for r in runs)
    unmatched_opportunities = sum(len(r['missing_ids']) for r in runs)

    paired, substitution_info = substitution_candidates(
        runs, scores, final_rows, tolerance_sec=tolerance_sec,
        tolerance_beats=tolerance_beats, excluded_windows=windows)
    direct_mismatches = [r for run in runs for r in run['matches']
                         if number(r.get('score_pitch')) is not None
                         and number(r.get('performance_pitch')) is not None
                         and number(r['score_pitch']) != number(r['performance_pitch'])]
    n_direct = len({r.get('performance_note_id') for r in direct_mismatches})
    n_sub = len(paired)
    performed_unmatched_all = {r['performance_note_id'] for r in final_rows
                               if r.get('label') == 'insertion' and r.get('performance_note_id')}
    performed_unmatched = {r['performance_note_id'] for r in final_rows
                           if r.get('label') == 'insertion' and r.get('performance_note_id')
                           and not in_windows(number(r.get('performance_onset_sec')), windows)}
    baseline_unmatched = {r['performance_note_id'] for r in baseline_rows
                          if r.get('label') == 'insertion' and r.get('performance_note_id')}
    n_missing = max(0, unmatched_opportunities-n_sub)
    n_extra = max(0, len(performed_unmatched)-n_sub)
    n_wrong = n_direct+n_sub

    rates = {
        'missing_note_rate': n_missing/score_opportunities if score_opportunities else None,
        'extra_note_rate': n_extra/evaluable_perf if evaluable_perf else None,
        'possible_wrong_note_rate': n_wrong/score_opportunities if score_opportunities else None,
    }
    counts = {
        'excluded_note_count': excluded_note_count,
        'evaluable_perf': evaluable_perf,
        'evaluable_fraction': evaluable_perf/len(perfs) if perfs else 0.0,
        'score_opportunities': score_opportunities,
        'unmatched_opportunities': unmatched_opportunities,
        'duplicate_score_in_run': sum(r['reused_ids_in_run'] for r in runs),
        'direct_mismatches': direct_mismatches,
        'n_direct': n_direct, 'n_sub': n_sub, 'n_missing': n_missing, 'n_extra': n_extra,
        'performed_unmatched_all': performed_unmatched_all,
        'performed_unmatched': performed_unmatched,
        'baseline_unmatched': baseline_unmatched,
        'substitution_info': substitution_info,
    }
    return rates, counts
