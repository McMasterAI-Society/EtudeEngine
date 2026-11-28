## Setup

### Folder structure

```
.
├── data/                              # downloaded datasets (gitignored)
│   ├── majeppa/                       # MAJEPPA: metadata.csv, alignment.parquet, performance/, score/
│   └── psyllabus/                     # PSyllabus: new_clean_data.json (levels 1–11), optional MIDI
├── src/
│   ├── assessment/
│   │   ├── common/                    # shared by everything below
│   │   │   ├── io.py                  # CSV read/write
│   │   │   ├── midi.py                # MIDI reader: notes, pedal, time signatures
│   │   │   └── utils.py               # small helpers (number parsing, median)
│   │   ├── performance/               # scoring a performance against its score
│   │   │   ├── config.py              # all thresholds
│   │   │   ├── ingest.py              # iterate score–performance pairs by ID
│   │   │   ├── alignment.py           # load + validate a note-level alignment
│   │   │   ├── structure.py           # repeats, skips, passes through the score
│   │   │   ├── validity.py            # when a feature is trustworthy enough to report
│   │   │   ├── features/              # pitch.py, timing.py, chords.py, dynamics.py
│   │   │   └── cli/extract_features.py  # runs the above, writes the feature CSVs
│   │   ├── difficulty/                # piece difficulty on the 1–11 scale
│   │   │   ├── schema.py              # Piece, DifficultyEstimate
│   │   │   ├── catalog/               # psyllabus.py, matching.py, catalog.py (pieces + difficulty)
│   │   │   └── model/                 # piece_features.py, ranker.py, calibration.py, estimate.py
│   │   └── anchoring/                 # scoring the user from piece difficulty (stubs)
│   │       ├── schema.py              # SkillEstimate
│   │       ├── quality.py             # features → quality q (0–1)
│   │       └── anchor.py              # q + piece difficulty → skill out of 11
│   ├── scripts/
│   │   ├── download_majeppa.py        # → data/majeppa
│   │   ├── download_psyllabus.py      # → data/psyllabus
│   │   └── anchor_demo.py             # end-to-end anchoring demo (stubbed steps)
│   └── templates/                     # reference code (gitignored)
├── main.py
└── pyproject.toml
```

Run feature extraction: `PYTHONPATH=src python -m assessment.performance.cli.extract_features BATCH_DIR --outdir feature_output --midi-dir data/majeppa`

## Research

- [`huggingface/MAJEPPA`](https://huggingface.co/datasets/kkwsts/MAJEPPA-Dataset/viewer/metadata/train?p=1&views%5B%5D=metadata&sql=--+The+SQL+console+is+powered+by+DuckDB+WASM+and+runs+entirely+in+the+browser.%0A--+Get+started+by+typing+a+query+or+selecting+a+view+from+the+options+below.%0ASELECT+*+FROM+metadata+LIMIT+10%3B). A dataset of youtube videos of performances over piano pieces. Each entry is tied to a video link, performance file with id `P_*` and score `S_*`. It holds a MIDI recording of each entry for processing and analysis i.e. skill assessment.
- [Applications of the Elo rating system in adaptive educational systems](https://www.sciencedirect.com/science/article/pii/S036013151630080X?via%3Dihub). 
- [Estimating Rasch Measures with Known Polytomous (or Rating Scale) Item Difficulties Anchored Maximum Likelihood Estimation (AMLE)](https://www.rasch.org/rmt/rmt122q.htm).