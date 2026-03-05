import csv
import os
from typing import Dict


def write_event(path: str, event: Dict[str, object]) -> None:
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sorted(event.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(event)
