"""Tunable thresholds for feature extraction.

Values match the originals in src/templates/steven.py, so output is unchanged.
Units are in the names: _SEC seconds, _BEATS score beats, _MS milliseconds.
"""

# --- Labels and features -----------------------------------------------------
LEVEL_GROUP = {
    "adult_beginner": "beginner", "child_beginner": "beginner",
    "adult_intermediate": "intermediate",
    "piano_teacher": "advanced", "child_professional": "advanced",  # team decision pending
    "virtuoso": "advanced",
}
PITCH_FEATURES = ("missing_note_rate", "extra_note_rate", "possible_wrong_note_rate")
TIMING_FEATURES = ("timing_irregularity_beats", "tempo_instability_log")
CHORD_FEATURES = ("chord_onset_spread_ms",)
DYNAMICS_FEATURES = ("velocity_range_p5_p95", "dynamics_following_rho")
FEATURES = PITCH_FEATURES + TIMING_FEATURES + CHORD_FEATURES + DYNAMICS_FEATURES

# --- Structure: repeats, skips, uncertain stretches ----------------------------
JUMP_TIME_GROUP_DECIMALS = 2         # matched notes grouped by onset rounded to 0.01 s
REPEAT_MIN_BACKWARD_BEATS = 8.0      # score position dropping back >= this = repeat/restart
SKIP_MIN_FORWARD_BEATS = 8.0         # leap forward >= this ...
SKIP_MAX_SEC_PER_BEAT = 0.10         # ... faster than this = skipped passage or glitch
UNCERTAIN_WINDOW_PAD_SEC = 0.15      # padding around suspicious unmatched clusters

# --- Tempo sanity bounds (timing + substitutions) ------------------------------
MIN_SEC_PER_BEAT = 0.08              # local tempo slopes outside [min, max] are rejected
MAX_SEC_PER_BEAT = 3.5
NEIGHBOR_MAX_DISTANCE_BEATS = 4.0    # max distance to anchors used for projection

# --- Anchors ------------------------------------------------------------------
ANCHOR_EXACT_PITCH_ONLY = True       # only correctly pitched matches become timing anchors
ANCHOR_MAX_CHORD_SPREAD_SEC = 0.15   # onset groups wider than this are not anchors

# --- Timing irregularity + tempo instability ----------------------------------
ROBUST_LINE_MIN_BEAT_GAP = 0.20      # anchor pairs closer than this are skipped in Theil–Sen
RUN_MIN_ANCHORS = 5                  # runs with fewer anchors are skipped
RESIDUAL_NEIGHBOR_SEARCH = 8         # look up to 8 anchors each side ...
RESIDUAL_NEIGHBOR_MAX_BEATS = 4.0    # ... within 4 beats ...
RESIDUAL_MIN_EACH_SIDE = 2           # ... need at least 2 on each side ...
RESIDUAL_CONTEXT_EACH_SIDE = 4       # ... and fit the line through the nearest 4 each side
RESIDUAL_TRIM_FRACTION = 0.05        # drop the largest 5% |residuals| before averaging
MIN_RESIDUALS = 12                   # fewer residuals -> timing_irregularity blank

TEMPO_WINDOW_STEP_BEATS = 2.0        # local-tempo windows every 2 beats (also start/end margin)
TEMPO_WINDOW_HALF_WIDTH_BEATS = 2.25 # each window spans centre ± 2.25 beats
TEMPO_WINDOW_MIN_ANCHORS = 4         # anchors needed inside a window
TEMPO_WINDOW_MIN_SPAN_BEATS = 1.5    # anchors must cover at least this many beats
TEMPO_WINDOW_MAX_GAP_BEATS = 2.0     # no anchor gap larger than this inside a window
TEMPO_NEIGHBOR_MAX_STEP_BEATS = 2.1  # only compare consecutive windows this close
MIN_TEMPO_STEPS = 4                  # fewer -> tempo_instability blank

# --- Substitutions / wrong notes ----------------------------------------------
SUBSTITUTION_MAX_SEC = 0.20          # absolute cap on onset distance (CLI --substitution-tolerance)
SUBSTITUTION_BEATS = 0.20            # tempo-relative tolerance (CLI --substitution-beats)
SUBSTITUTION_MIN_WINDOW_SEC = 0.04   # tolerance never smaller than this
SUBSTITUTION_MAX_PITCH_DIST = 24     # semitones; further apart = not a substitution (also cost scale)
CLI_SUBSTITUTION_SEC_RANGE = (0.01, 1.0)
CLI_SUBSTITUTION_BEATS_RANGE = (0.02, 0.50)

# --- Chords -------------------------------------------------------------------
ROLL_MIN_SPREAD_MS = 90.0            # possible roll: spread at least this ...
ROLL_MAX_SPREAD_MS = 700.0           # ... at most this ...
ROLL_MIN_GAP_MS = 12.0               # ... every gap at least this ...
ROLL_MAX_SPACING_CV = 0.50           # ... and evenly spaced
ROLL_MIN_NOTES = 3                   # 2-note chords can't be judged as rolls
CHORD_AMBIGUOUS_WIDE_MS = 150.0      # wider non-roll chords are ambiguous
MIN_CHORDS = 5                       # fewer sync chords -> chord_onset_spread blank

# --- Dynamics -----------------------------------------------------------------
PERF_VELOCITY_JOIN_TOL_SEC = 0.03    # performance note -> MIDI onset match tolerance
SCORE_VELOCITY_JOIN_TOL_BEATS = 0.02 # score note -> MIDI onset (quarter beats)
DYNAMICS_WINDOW_BEATS = 2.0          # loudness compared per 2 score beats
DYNAMICS_MIN_NOTES = 20              # fewer evaluable notes -> velocity_range blank
DYNAMICS_MIN_WINDOWS = 4             # fewer windows in a run -> run skipped
VELOCITY_RANGE_PERCENTILES = (0.05, 0.95)

# --- Validity: when a feature is blanked --------------------------------------
MIN_SELECTED_MATCHES = 10
MIN_EVALUABLE_FRACTION = 0.25
MIN_EXPECTED_NOTES = 15
MAX_PITCH_MISMATCH_RATE = 0.10
MAX_TIMING_INVERSION_RATE = 0.05
MIN_CHORD_SYNC_FRACTION = 0.20
LOW_OBSERVED_SPAN_FRACTION = 0.40    # flagged only, not used for blanking
MIN_PERF_VELOCITY_JOIN = 0.90
MIN_SCORE_VELOCITY_JOIN = 0.80
MIN_SCORE_DISTINCT_VELOCITIES = 3
