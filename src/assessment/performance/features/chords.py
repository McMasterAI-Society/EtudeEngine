"""Chord feature: onset spread of synchronised chords, excluding likely rolls."""
from __future__ import annotations

import statistics
from collections import defaultdict

from assessment.performance import config as cfg
from assessment.common.utils import median, number


def classify_chord_event(notes, spread_ms, *, roll_min_spread=cfg.ROLL_MIN_SPREAD_MS,
                         ambiguous_wide=cfg.CHORD_AMBIGUOUS_WIDE_MS,
                         max_plausible_roll=cfg.ROLL_MAX_SPREAD_MS):
    """Label a chord's onset pattern: possible_roll, ambiguous_wide or synchronization_candidate.

    notes = [(pitch, onset_sec), ...]. Describes the pattern, not the player's intent.
    """
    ordered = sorted(notes, key=lambda n: (n[1], n[0]))
    pitches = [int(p) for p, _t in ordered]
    times = [t for _p, t in ordered]
    gaps_ms = [1000*(b-a) for a, b in zip(times, times[1:])]
    monotonic = (len(pitches) >= cfg.ROLL_MIN_NOTES and len(set(pitches)) == len(pitches)
                 and (all(a < b for a, b in zip(pitches, pitches[1:]))
                      or all(a > b for a, b in zip(pitches, pitches[1:]))))
    regularity_cv = (statistics.pstdev(gaps_ms)/statistics.mean(gaps_ms)
                     if len(gaps_ms) >= 2 and statistics.mean(gaps_ms) > 0 else None)
    possible_roll = (monotonic and roll_min_spread <= spread_ms <= max_plausible_roll
                     and all(g >= cfg.ROLL_MIN_GAP_MS for g in gaps_ms)
                     and regularity_cv is not None and regularity_cv <= cfg.ROLL_MAX_SPACING_CV)
    if possible_roll:
        classification = 'possible_roll'
    elif spread_ms > ambiguous_wide:
        classification = 'ambiguous_wide'
    else:
        classification = 'synchronization_candidate'
    return classification, monotonic, regularity_cv, gaps_ms


def chord_metric(runs, scores, *, min_chords=cfg.MIN_CHORDS, collect_events=False):
    """chord_onset_spread_ms over fully matched chords, plus roll/ambiguity counts (and events)."""
    by_score_beat = defaultdict(set)
    for sid, (beat, _pitch) in scores.items():
        by_score_beat[round(beat, 4)].add(sid)
    raw_spreads, syn_spreads, possible_rolls, ambiguous, partial = [], [], 0, 0, 0
    events = []
    for run in runs:
        matched_per_beat = defaultdict(dict)
        for row in run['matches']:
            sid = (row.get('score_note_id') or '').strip()
            sp = number(row.get('score_pitch'))
            pp = number(row.get('performance_pitch'))
            sec = number(row.get('performance_onset_sec'))
            beat = number(row.get('score_onset_beat'))
            if not sid or sp is None or pp is None or sp != pp or sec is None or beat is None:
                continue
            matched_per_beat[round(beat, 4)].setdefault(sid, (int(sp), sec))
        # Chords this run should have played (fully missed ones are reported as incomplete).
        observed_chord_beats = sorted(beat for beat, ids in by_score_beat.items()
                                      if len(ids) >= 2 and (ids & run['expected_ids']))
        for beat in observed_chord_beats:
            notes = matched_per_beat.get(beat, {})
            expected_ids = by_score_beat[beat]
            if len(notes) < 2 or set(notes) != expected_ids:
                partial += 1
                if collect_events:
                    events.append({'run_index': run['run_index'], 'score_onset_beat': beat,
                                   'expected_notes': len(expected_ids), 'recovered_notes': len(notes),
                                   'spread_ms': '', 'classification': 'incomplete_chord',
                                   'monotonic_pitch_order': '', 'spacing_cv': '',
                                   'pitches_in_onset_order': '', 'performed_onsets_sec': ''})
                continue
            observed = list(notes.values())
            times = [sec for _pitch, sec in observed]
            spread = (max(times)-min(times))*1000.0
            raw_spreads.append(spread)
            status, monotonic, cv, _gaps = classify_chord_event(observed, spread)
            if status == 'possible_roll':
                possible_rolls += 1
            elif status == 'ambiguous_wide':
                ambiguous += 1
            else:
                syn_spreads.append(spread)
            if collect_events:
                ordered = sorted(observed, key=lambda item: (item[1], item[0]))
                events.append({'run_index': run['run_index'], 'score_onset_beat': beat,
                               'expected_notes': len(expected_ids), 'recovered_notes': len(notes),
                               'spread_ms': round(spread, 6), 'classification': status,
                               'monotonic_pitch_order': monotonic,
                               'spacing_cv': round(cv, 5) if cv is not None else '',
                               'pitches_in_onset_order': ' '.join(str(p) for p, _ in ordered),
                               'performed_onsets_sec': ' '.join(f'{t:.5f}' for _, t in ordered)})
    measured = len(raw_spreads)
    candidate_share = len(syn_spreads)/measured if measured else None
    metrics = {
        'chord_onset_spread_ms': median(syn_spreads) if len(syn_spreads) >= min_chords else None,
        'chord_raw_median_spread_ms': median(raw_spreads),
        'chords_measured': measured, 'chords_insufficient_matches': partial,
        'chords_over_150ms': sum(x > cfg.CHORD_AMBIGUOUS_WIDE_MS for x in raw_spreads),
        'chords_synchronization_candidates': len(syn_spreads),
        'chords_possible_rolls': possible_rolls,
        'chords_ambiguous_wide': ambiguous,
        'chord_sync_candidate_fraction': candidate_share,
        'chord_possible_roll_fraction': (possible_rolls/measured if measured else None),
    }
    return (metrics, events) if collect_events else metrics
