from pathlib import Path
import csv

def read_csv(path):
    with Path(path).open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f'Empty CSV: {path}')
        return list(reader), set(reader.fieldnames)


def write_csv(path, rows, headers):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)