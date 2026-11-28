"""Download the Piano Syllabus (PSyllabus) dataset from Zenodo (record 14794592).

uv run python -m src.scripts.download_psyllabus           -> labels only (~14 MB)
uv run python -m src.scripts.download_psyllabus --midi    -> + transcribed MIDI (52 MB)
Other optional parts: --pianoroll (77 MB), --cqt (2.1 GB, audio features; usually not needed).
"""
import argparse
import json
import urllib.request
import zipfile
from pathlib import Path

RECORD_API = "https://zenodo.org/api/records/14794592"
ALWAYS = ["new_clean_data.json", "split_audio.json"]   # labels/metadata + train/test splits
OPTIONAL = {"midi": "mid.zip", "pianoroll": "pianoroll5.zip", "cqt": "cqt5.zip"}


def download(url: str, dest: Path) -> None:
    """Stream to a .part file, then rename, so an interrupted run never leaves a broken file."""
    if dest.exists():
        print(f"  already have {dest.name}")
        return
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as response, open(tmp, "wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    tmp.rename(dest)


def main() -> None:
    p = argparse.ArgumentParser(description="Download the Piano Syllabus (PSyllabus) dataset from Zenodo.")
    p.add_argument("--out", type=Path, default=Path("data/psyllabus"))
    for flag, name in OPTIONAL.items():
        p.add_argument(f"--{flag}", action="store_true", help=f"also download {name}")
    args = p.parse_args()

    with urllib.request.urlopen(RECORD_API) as response:
        files = {f["key"]: f for f in json.load(response)["files"]}
    wanted = ALWAYS + [name for flag, name in OPTIONAL.items() if getattr(args, flag)]

    args.out.mkdir(parents=True, exist_ok=True)
    for name in wanted:
        info = files[name]
        print(f"{name} ({info['size'] / 1e6:.0f} MB)")
        dest = args.out / name
        download(info["links"]["self"], dest)
        if name.endswith(".zip"):
            with zipfile.ZipFile(dest) as z:
                z.extractall(args.out)
    print("done:", sorted(p.name for p in args.out.iterdir()))


if __name__ == "__main__":
    main()
