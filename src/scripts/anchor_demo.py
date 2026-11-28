"""End-to-end anchoring demo: catalog → piece difficulty → performance quality → anchored skill.

uv run python -m src.scripts.anchor_demo   (needs data/majeppa, data/psyllabus, feature_output/)
Each step calls a stub; fill them in order and the demo starts working step by step.
"""
from pathlib import Path

DATA = Path("data")
FEATURES_CSV = Path("feature_output/performance_features.csv")   # from assessment.performance.cli.extract_features


def main() -> None:
    # 1. Catalog: MAJEPPA pieces + PSyllabus matches (true levels)
    #    from assessment.difficulty.catalog.catalog import PieceCatalog
    #    from assessment.difficulty.catalog.psyllabus import load_psyllabus
    #    from assessment.difficulty.catalog.matching import match_pieces
    #    catalog = PieceCatalog.from_majeppa(DATA / "majeppa/metadata.csv")
    #    matched = catalog.apply_matches(match_pieces(catalog.pieces(), load_psyllabus()))
    #    print(f"matched {matched}/{len(catalog.pieces())} pieces to PSyllabus")

    # 2. Difficulty for unmatched pieces: rank + calibrate on the matches
    #    from assessment.common.midi import read_midi
    #    from assessment.difficulty.model.piece_features import piece_features
    #    from assessment.difficulty.model.ranker import FeatureRanker
    #    from assessment.difficulty.model.calibration import LevelCalibrator
    #    from assessment.difficulty.model.estimate import estimate_missing_difficulties
    #    feats = {p.score_id: piece_features(read_midi(DATA / f"majeppa/score/{p.score_id}.mid"))
    #             for p in catalog.pieces()}
    #    ranker = FeatureRanker().fit(...)   # train on PSyllabus MIDI + levels (download --midi)
    #    estimate_missing_difficulties(catalog, ranker, LevelCalibrator(), feats)
    #    catalog.save()

    # 3. Quality per performance, then anchored skill
    #    from assessment.common.io import read_csv
    #    from assessment.anchoring.quality import performance_quality
    #    from assessment.anchoring.anchor import anchored_skill
    #    rows, _ = read_csv(FEATURES_CSV)
    #    skills = []
    #    for row in rows:
    #        d = catalog.get_difficulty(row["score_id"])
    #        if d is None: continue
    #        peers = [r for r in rows if r["score_id"] == row["score_id"]]
    #        skills.append((row["proficiency_group"],
    #                       anchored_skill(row["performance_id"], d.level, performance_quality(row, peers))))

    # 4. Result: does theta separate beginner / intermediate / advanced?
    #    median theta per proficiency_group (+ rank correlation with the group order)
    raise NotImplementedError("Fill in the stubs, then uncomment the steps above in order.")


if __name__ == "__main__":
    main()
