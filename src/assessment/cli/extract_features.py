"""Extract per-performance skill features from aligner output (and MIDI, for dynamics).

Usage (from the repo root):
    PYTHONPATH=src python -m assessment.cli.extract_features BATCH_DIR --outdir feature_output \
        [--midi-dir data/majeppa] [--max-items 10] [--chord-audit]

BATCH_DIR holds batch_summary.csv and one S_XXXX_P_XXXX folder per pair.
Writes performance_features.csv, feature_quality.csv, feature_group_summary.csv
(and chord_event_audit.csv with --chord-audit). Blank feature = not trustworthy;
reasons are in feature_quality.csv. Features are estimates, not verified mistakes.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from assessment.alignment import note_consistency, row_notes
from assessment.config import config as cfg
from assessment.features.chords import chord_metric
from assessment.features.dynamics import dynamics_for_pair
from assessment.features.pitch import pitch_metrics
from assessment.features.timing import timing_metrics
from assessment.ingest import MajeppaIngestor
from assessment.io import read_csv, write_csv
from assessment.structure import analyze_structure
from assessment.utils import median, number
from assessment.validity import build_state, choose_validity

BASE_COLUMNS = ['score_id', 'performance_id', 'expertise_level', 'proficiency_group',
                'matcher', 'alignment_status']
CHORD_AUDIT_FIELDS = ('score_id', 'performance_id', 'run_index', 'score_onset_beat',
                      'expected_notes', 'recovered_notes', 'spread_ms', 'classification',
                      'monotonic_pitch_order', 'spacing_cv', 'pitches_in_onset_order',
                      'performed_onsets_sec')


def _blank_if_none(value):
    return value if value is not None else ''


def analyze_one(pair, *, substitution_tolerance=cfg.SUBSTITUTION_MAX_SEC,
                substitution_beats=cfg.SUBSTITUTION_BEATS, chord_audit=False):
    """All features for one pair: (public row, diagnostics row[, chord events])."""
    alignment, record = pair.alignment, pair.record
    score, perf, conflicts = row_notes(alignment.baseline_rows)
    if not score or not perf:
        raise ValueError('No score or performed notes found in baseline alignment')
    selected_issues = note_consistency(alignment.final_rows, score, perf)
    selected_issues |= {f'baseline_{p}' for p in note_consistency(alignment.baseline_rows, score, perf)}

    structure = analyze_structure(alignment, record, score)
    runs = structure.runs

    raw, pc = pitch_metrics(alignment, structure, score, perf,
                            tolerance_sec=substitution_tolerance, tolerance_beats=substitution_beats)
    raw.update(timing_metrics(runs))
    chord_stats, chord_events = chord_metric(runs, score, collect_events=True)
    raw.update(chord_stats)
    dyn, dyn_info = dynamics_for_pair(pair, structure, score, perf)
    raw.update(dyn)

    beats = [b for b, _p in score.values()]
    full_span = max(beats) - min(beats)
    covered_score_span = sum(max(0, r['hi']-r['lo']) for r in runs)
    max_traversal_span = max((r['hi']-r['lo'] for r in runs), default=0)
    observed_frac = (max_traversal_span/full_span if full_span > 0 else 1.0)
    selected_matches = [r for r in alignment.final_rows if r.get('label') == 'match']
    timing_inv_rate = raw['timing_time_inversions']/max(1, raw['distinct_score_onset_anchors']-len(runs))
    state = build_state(alignment=alignment, structure=structure, pitch_counts=pc, raw=raw,
                        conflicts=conflicts, selected_issues=selected_issues,
                        selected_matches=selected_matches, observed_frac=observed_frac,
                        timing_inv_rate=timing_inv_rate, dynamics_info=dyn_info)

    valid, reasons, features = {}, {}, {}
    for name in cfg.FEATURES:
        valid[name], reasons[name] = choose_validity(name, raw[name], state)
        features[name] = round(raw[name], 9) if valid[name] else ''

    decision = alignment.decision
    sid, pid = pair.score_id, pair.performance_id
    public = {
        'score_id': sid, 'performance_id': pid,
        'expertise_level': record.get('expertise_level') or decision.get('expertise_level', ''),
        'proficiency_group': cfg.LEVEL_GROUP.get(record.get('expertise_level') or decision.get('expertise_level'), 'unknown'),
        'matcher': state['matcher'], 'alignment_status': record.get('status') or decision.get('status', ''),
        **features,
    }
    diagnostics = {
        **{k: public[k] for k in BASE_COLUMNS},
        **{f'{name}_estimate': round(raw[name], 9) if raw[name] is not None else '' for name in cfg.FEATURES},
        **{f'{name}_valid': valid[name] for name in cfg.FEATURES},
        **{f'{name}_reason': reasons[name] for name in cfg.FEATURES},
        'reference_score_notes': len(score), 'performed_notes': len(perf),
        'selected_matches': len(selected_matches),
        'selected_insertions': len(pc['performed_unmatched_all']),
        'selected_insertions_in_evaluable_segments': len(pc['performed_unmatched']),
        'baseline_insertions': len(pc['baseline_unmatched']),
        'uncertain_performance_windows': len(structure.uncertain_windows),
        'uncertain_performance_notes_excluded': pc['excluded_note_count'],
        'evaluable_performance_notes': pc['evaluable_perf'],
        'evaluable_performance_fraction': round(pc['evaluable_fraction'], 6),
        'selected_direct_pitch_mismatches': pc['n_direct'],
        'inferred_traversals': len(runs), 'candidate_backward_jumps': len(structure.jumps),
        'candidate_improbable_forward_skips': len(structure.forward_skips),
        'potential_skipped_passage': bool(structure.forward_skips),
        'unexplained_candidate_jumps': state['unexplained_jump_count'],
        'expected_note_opportunities_in_observed_spans': pc['score_opportunities'],
        'unmatched_expected_opportunities_before_substitution': pc['unmatched_opportunities'],
        'conservative_substitution_pairs': pc['n_sub'],
        'possible_omissions_after_pairing': pc['n_missing'],
        'possible_extra_notes_after_pairing': pc['n_extra'],
        'observed_score_span_fraction': round(observed_frac, 6),
        'score_beat_span_across_traversals': round(covered_score_span, 5),
        'score_note_reuse_within_traversal': pc['duplicate_score_in_run'],
        'timing_residual_samples': raw['timing_residual_samples'],
        'tempo_change_samples': raw['tempo_change_samples'],
        'distinct_score_onset_anchors': raw['distinct_score_onset_anchors'],
        'timing_time_inversions': raw['timing_time_inversions'],
        'timing_wide_chord_anchors_skipped': raw['timing_wide_chord_anchors_skipped'],
        'chords_measured': raw['chords_measured'],
        'chord_raw_median_spread_ms': _blank_if_none(raw['chord_raw_median_spread_ms']),
        'chords_synchronization_candidates': raw['chords_synchronization_candidates'],
        'chords_possible_rolls': raw['chords_possible_rolls'],
        'chords_ambiguous_wide': raw['chords_ambiguous_wide'],
        'chord_sync_candidate_fraction': _blank_if_none(raw['chord_sync_candidate_fraction']),
        'chord_possible_roll_fraction': _blank_if_none(raw['chord_possible_roll_fraction']),
        'chords_insufficient_matches': raw['chords_insufficient_matches'],
        'chords_over_150ms': raw['chords_over_150ms'],
        'baseline_major_unmatched_clusters': len(structure.clusters),
        'alignment_note_id_issues': '|'.join(sorted(selected_issues)),
        'score_metadata_conflicts': '|'.join(sorted(set(conflicts))),
        'potential_repeat_or_restart': bool(structure.jumps),
        'intentional_repeat_not_verified': bool(structure.jumps),
        'structural_warning_text': ' | '.join(decision.get('warnings') or []),
        'projectable_missing_notes': pc['substitution_info']['projectable_missing_notes'],
        'velocity_notes': raw['velocity_notes'],
        'velocity_cv': round(raw['velocity_cv'], 6) if raw['velocity_cv'] is not None else '',
        'dynamics_windows': raw['dynamics_windows'],
        'dynamics_runs_used': raw['dynamics_runs_used'],
        'perf_velocity_join_rate': round(dyn_info['perf_velocity_join_rate'], 6),
        'score_velocity_join_rate': round(dyn_info['score_velocity_join_rate'], 6),
        'score_velocity_distinct': dyn_info['score_velocity_distinct'],
        'dynamics_error': dyn_info['dynamics_error'],
        'error': '',
    }
    if chord_audit:
        for event in chord_events:
            event['score_id'] = sid
            event['performance_id'] = pid
        return public, diagnostics, chord_events
    return public, diagnostics


def group_summary(feature_rows):
    """Per level group and feature: counts and median/min/max of valid values."""
    groups = defaultdict(list)
    for row in feature_rows:
        groups[row.get('proficiency_group', 'unknown')].append(row)
    summaries = []
    for group in ('beginner', 'intermediate', 'advanced', 'unknown'):
        members = groups.get(group, [])
        if not members:
            continue
        for feature in cfg.FEATURES:
            nums = sorted(v for v in (number(row.get(feature)) for row in members) if v is not None)
            summaries.append({
                'proficiency_group': group, 'feature': feature,
                'recordings': len(members), 'valid_recordings': len(nums),
                'median': median(nums) if nums else '',
                'min': min(nums) if nums else '', 'max': max(nums) if nums else '',
            })
    return summaries


def _parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('batch_dir', type=Path, help='Directory containing batch_summary.csv and S_XXXX_P_XXXX subfolders')
    p.add_argument('--outdir', type=Path, default=Path('feature_output'))
    p.add_argument('--max-items', type=int, default=None, help='Process first N recordings, for a trial')
    p.add_argument('--substitution-tolerance', type=float, default=cfg.SUBSTITUTION_MAX_SEC,
                   help='Maximum allowed onset separation in seconds for possible substitutions')
    p.add_argument('--substitution-beats', type=float, default=cfg.SUBSTITUTION_BEATS,
                   help='Tempo-relative tolerance in beats (also capped by --substitution-tolerance)')
    p.add_argument('--chord-audit', action='store_true',
                   help='Write chord_event_audit.csv with per-chord raw onset/order/roll diagnostics')
    p.add_argument('--audit-score', default='',
                   help='Limit chord event audit to this score ID, e.g. S_0032')
    p.add_argument('--midi-dir', type=Path, default=None,
                   help='MAJEPPA folder with performance/P_XXXX.mid and score/S_XXXX.mid, for dynamics features')
    args = p.parse_args()
    if args.max_items is not None and args.max_items < 1:
        p.error('--max-items must be positive')
    lo, hi = cfg.CLI_SUBSTITUTION_SEC_RANGE
    if not (lo <= args.substitution_tolerance <= hi):
        p.error(f'--substitution-tolerance must lie between {lo} and {hi} seconds')
    lo, hi = cfg.CLI_SUBSTITUTION_BEATS_RANGE
    if not (lo <= args.substitution_beats <= hi):
        p.error(f'--substitution-beats must lie between {lo:.2f} and {hi:.2f} beats')
    return p, args


def main():
    p, args = _parse_args()
    inp, out = args.batch_dir.resolve(), args.outdir.resolve()
    if inp == out:
        p.error('Output folder must differ from input folder')
    rows, fields = read_csv(inp / 'batch_summary.csv')
    required = {'score_id', 'performance_id', 'expertise_level'}
    if not required.issubset(fields):
        p.error(f'batch summary missing {sorted(required-fields)}')
    pairs = MajeppaIngestor(rows, midi_dir=args.midi_dir.resolve() if args.midi_dir else None,
                            alignment_dir=inp, limit=args.max_items)
    if not len(pairs):
        p.error('No rows in batch summary')

    features, quality, all_chords = [], [], []
    for index, pair in enumerate(pairs, 1):
        sid, pid, rec = pair.score_id, pair.performance_id, pair.record
        try:
            include_audit = args.chord_audit and (not args.audit_score or args.audit_score == sid)
            result = analyze_one(pair, substitution_tolerance=args.substitution_tolerance,
                                 substitution_beats=args.substitution_beats, chord_audit=include_audit)
            if include_audit:
                row, diag, chords = result
                all_chords.extend(chords)
            else:
                row, diag = result
            features.append(row)
            quality.append(diag)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            msg = f'{type(exc).__name__}: {exc}'
            print(f'WARNING {sid}/{pid}: {msg}', file=sys.stderr)
            features.append({'score_id': sid, 'performance_id': pid,
                             'expertise_level': rec.get('expertise_level', ''),
                             'proficiency_group': cfg.LEVEL_GROUP.get(rec.get('expertise_level'), 'unknown'),
                             'matcher': rec.get('matcher', ''), 'alignment_status': rec.get('status', ''),
                             **{k: '' for k in cfg.FEATURES}})
            quality.append({'score_id': sid, 'performance_id': pid, 'error': msg})
        if index % 25 == 0 or index == len(pairs):
            print(f'Extracted {index}/{len(pairs)}', flush=True)

    write_csv(out / 'performance_features.csv', features, BASE_COLUMNS+list(cfg.FEATURES))
    extra_quality_cols = []
    for q in quality:
        for key in q:
            if key not in BASE_COLUMNS and key not in extra_quality_cols:
                extra_quality_cols.append(key)
    write_csv(out / 'feature_quality.csv', quality, BASE_COLUMNS+extra_quality_cols)
    write_csv(out / 'feature_group_summary.csv', group_summary(features),
              ['proficiency_group', 'feature', 'recordings', 'valid_recordings', 'median', 'min', 'max'])
    if args.chord_audit:
        write_csv(out / 'chord_event_audit.csv', all_chords, CHORD_AUDIT_FIELDS)
        print(f'Chord events audited: {len(all_chords)}', flush=True)

    errors = sum(bool(q.get('error')) for q in quality)
    complete = sum(all(number(row.get(f)) is not None for f in cfg.FEATURES) for row in features)
    print(f'\nFINISHED: {len(pairs)} recordings; {errors} errors; {complete} with all {len(cfg.FEATURES)} valid features')
    for feat in cfg.FEATURES:
        n = sum(number(row.get(feat)) is not None for row in features)
        print(f'  {feat}: {n}/{len(pairs)} valid')
    print(f'Outputs: {out}')
    print('Reminder: feature estimates and suspected substitutions/restarts are NOT verified playing errors.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        raise SystemExit(f'ERROR: {exc}') from exc
