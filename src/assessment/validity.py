"""Quality flags per performance, and whether each feature is trustworthy enough to report."""
from __future__ import annotations

from assessment.config import config as cfg


def build_state(*, alignment, structure, pitch_counts, raw, conflicts, selected_issues,
                selected_matches, observed_frac, timing_inv_rate, dynamics_info):
    """Collect the flags choose_validity() and the diagnostics need."""
    decision = alignment.decision
    selection = decision.get('selection') or {}
    unexplained = selection.get('unexplained_backward_jumps') or []
    pitch_disagree = (len(pitch_counts['direct_mismatches'])/len(selected_matches)) if selected_matches else 0.0
    return {
        'invalid_ids': bool(selected_issues),
        'matcher': structure.matcher,
        'too_few_matches': len(selected_matches) < cfg.MIN_SELECTED_MATCHES,
        'hmm_no_repeat_jump': (decision.get('matcher') == 'repeat_hmm' and not structure.jumps),
        'baseline_structural_gap': bool(structure.clusters),
        'unexplained_jump_count': len(unexplained),
        'conflicting_score_notes': bool(conflicts),
        'low_observed_score_span': observed_frac < cfg.LOW_OBSERVED_SPAN_FRACTION,
        'note_evaluable_fraction': pitch_counts['evaluable_fraction'],
        'evaluated_expected_notes': pitch_counts['score_opportunities'],
        'chord_sync_candidate_fraction': raw['chord_sync_candidate_fraction'] or 0.0,
        'duplicate_score_note_in_run': pitch_counts['duplicate_score_in_run'] > 0,
        'forward_skip_count': len(structure.forward_skips),
        'selected_pitch_mismatch_rate': pitch_disagree,
        'timing_inversion_rate': timing_inv_rate,
        **dynamics_info,
    }


def choose_validity(name, estimate, state):
    """(is_valid, 'reason|reason') for one feature."""
    reasons = []
    if estimate is None:
        reasons.append('insufficient_support_or_not_estimable')
    if state['invalid_ids']:
        reasons.append('invalid_or_duplicate_alignment_note_ids')
    if name in cfg.PITCH_FEATURES:
        if state['too_few_matches']:
            reasons.append('too_few_matched_notes_to_establish_score_context')
        if state['hmm_no_repeat_jump']:
            reasons.append('repeat_matcher_without_detected_score_reset')
        if state['conflicting_score_notes']:
            reasons.append('conflicting_score_note_metadata')
        if state['note_evaluable_fraction'] < cfg.MIN_EVALUABLE_FRACTION:
            reasons.append('too_little_performance_outside_uncertain_passages')
        if state['evaluated_expected_notes'] < cfg.MIN_EXPECTED_NOTES:
            reasons.append('too_few_expected_note_opportunities')
        if state['duplicate_score_note_in_run'] and name in ('missing_note_rate', 'possible_wrong_note_rate'):
            reasons.append('score_note_reused_inside_inferred_traversal')
        if state['selected_pitch_mismatch_rate'] > cfg.MAX_PITCH_MISMATCH_RATE:
            reasons.append('many_score_performance_pitch_disagreements')
    elif name in cfg.DYNAMICS_FEATURES:
        if state['dynamics_error']:
            reasons.append(state['dynamics_error'])
        elif state['perf_velocity_join_rate'] < cfg.MIN_PERF_VELOCITY_JOIN:
            reasons.append('performance_velocity_join_incomplete')
        if name == 'dynamics_following_rho' and not state['dynamics_error']:
            if state['score_velocity_join_rate'] < cfg.MIN_SCORE_VELOCITY_JOIN:
                reasons.append('score_velocity_join_incomplete_check_beat_units')
            if state['score_velocity_distinct'] < cfg.MIN_SCORE_DISTINCT_VELOCITIES:
                reasons.append('score_has_no_dynamic_variation')
    else:
        if state['timing_inversion_rate'] > cfg.MAX_TIMING_INVERSION_RATE:
            reasons.append('nonmonotonic_score_to_performance_mapping')
        if name == 'chord_onset_spread_ms' and state['chord_sync_candidate_fraction'] < cfg.MIN_CHORD_SYNC_FRACTION:
            reasons.append('most_chords_rolled_or_ambiguous')
    return (not reasons), '|'.join(reasons)
