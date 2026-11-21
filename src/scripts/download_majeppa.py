from pathlib import Path
import zipfile
from huggingface_hub import snapshot_download

# uv run python -m src.scripts.download_majeppa
if __name__ == "__main__":
    out = Path("data/majeppa")
    snapshot_download(
        repo_id="kkwsts/MAJEPPA-Dataset",
        repo_type="dataset",
        local_dir=out,
    )
    for z in ["performance.zip", "score.zip"]:
        with zipfile.ZipFile(out / z) as f:
            # create data/majeppa/performance/ and data/majeppa/score/
            f.extractall(out)
    print("done:", sorted(p.name for p in out.iterdir()))