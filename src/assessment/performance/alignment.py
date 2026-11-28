"""Load one score–performance alignment folder and validate its note IDs."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from assessment.common.io import read_csv
from assessment.common.utils import number

ROW_FIELDS = (
    'label', 'score_note_id', 'performance_note_id', 'score_pitch',
    'performance_pitch', 'score_onset_beat', 'performance_onset_sec',
)


@dataclass
class Alignment:
    """Contents of an S_XXXX_P_XXXX folder written by the aligner."""
    decision: dict
    baseline_rows: list[dict]
    final_rows: list[dict]


def load_alignment(folder) -> Alignment:
    """Read decision.json plus the baseline and final alignment CSVs."""
    folder = Path(folder)
    with (folder / 'decision.json').open('r', encoding='utf-8') as handle:
        decision = json.load(handle)
    baseline_rows, baseline_fields = read_csv(folder / 'baseline_alignment.csv')
    final_rows, final_fields = read_csv(folder / 'final_alignment.csv')
    for file_label, fields in [('baseline', baseline_fields), ('final', final_fields)]:
        missing = set(ROW_FIELDS) - fields
        if missing:
            raise ValueError(f'{file_label} CSV missing columns: {sorted(missing)}')
    return Alignment(decision, baseline_rows, final_rows)


def row_notes(rows):
    """Unique score notes {id: (beat, pitch)} and performance notes {id: (sec, pitch)}.

    Built from the BASELINE alignment, where IDs are unique; also returns ID conflicts.
    """
    scores, perfs, conflicts = {}, {}, []
    for row in rows:
        sid = (row.get('score_note_id') or '').strip()
        pid = (row.get('performance_note_id') or '').strip()
        sb, sp = number(row.get('score_onset_beat')), number(row.get('score_pitch'))
        pt, pp = number(row.get('performance_onset_sec')), number(row.get('performance_pitch'))
        if sid and sb is not None and sp is not None:
            note = (sb, int(sp))
            if sid in scores and scores[sid] != note:
                conflicts.append('score_id_conflict')
            scores.setdefault(sid, note)
        if pid and pt is not None and pp is not None:
            note = (pt, int(pp))
            if pid in perfs and perfs[pid] != note:
                conflicts.append('performance_id_conflict')
            perfs.setdefault(pid, note)
    return scores, perfs, conflicts


def note_consistency(rows, scores, perfs):
    """Set of ID problems: bad labels, incomplete matches, unknown or duplicated notes."""
    matched_ids = []
    observed_ids = []
    issues = set()
    for row in rows:
        label = row.get('label')
        sid = (row.get('score_note_id') or '').strip()
        pid = (row.get('performance_note_id') or '').strip()
        if label not in ('match', 'insertion', 'deletion'):
            issues.add('unexpected_alignment_label')
        if label == 'match':
            if not sid or not pid:
                issues.add('incomplete_match')
            if sid and sid not in scores:
                issues.add('unknown_score_id')
            if pid and pid not in perfs:
                issues.add('unknown_performance_id')
            if pid:
                matched_ids.append(pid)
        if label in ('match', 'insertion'):
            if not pid:
                issues.add('missing_performance_id')
            else:
                observed_ids.append(pid)
    if len(observed_ids) != len(set(observed_ids)):
        issues.add('duplicate_performance_note_rows')
    if len(observed_ids) != len(perfs) or set(observed_ids) != set(perfs):
        issues.add('incomplete_performance_note_coverage')
    return issues
