"""Convert BoxCars116k -> VMMRdb-style flat class folders.

Source: DATA/BoxCars116k/json_data/dataset.json ("samples" list). Each sample has
a free-text "annotation" ("<make> <model...>", no year) and a list of "instances"
(already pre-cropped per-vehicle chips). Instance images live at
DATA/BoxCars116k/images/<instance["path"]>.

Output: DATA/boxcars116k_vmmr/<slug>/<slug>_<idx>.<ext>  (symlinks, no re-encoding
needed since BoxCars instances are already cropped chips).

Usage:
    uv run boxcars116k.py --sample 30   # smoke test: first N samples only
    uv run boxcars116k.py               # full run (all samples)
"""
import argparse
import json
import sys

sys.path.insert(
    0,
    "/Users/logan/Developer/vibes/WORK/CLS/VMMRdb/.claude/worktrees/vmmr-multi-dataset-prep/code/preprocess",
)
from naming import slug, DATA

SRC = DATA / "BoxCars116k"
JSON_PATH = SRC / "json_data" / "dataset.json"
IMAGES_DIR = SRC / "images"
OUT_DIR = DATA / "boxcars116k_vmmr"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Only process the first N samples (for validation).",
    )
    args = parser.parse_args()

    with open(JSON_PATH) as f:
        data = json.load(f)

    samples = data["samples"]
    if args.sample is not None:
        samples = samples[: args.sample]

    class_counts = {}  # slug -> next index (1-based)
    n_images = 0
    n_skipped_mask = 0
    n_missing_src = 0
    n_existing = 0
    skipped_annotations = set()

    for sample in samples:
        annotation = (sample.get("annotation") or "").strip()
        tokens = annotation.split()
        if len(tokens) < 2:
            # need at least make + model
            skipped_annotations.add(annotation)
            continue
        make = tokens[0]
        model = " ".join(tokens[1:])
        cls = slug(make, model, year=None)
        if not cls:
            skipped_annotations.add(annotation)
            continue

        out_class_dir = OUT_DIR / cls

        for instance in sample.get("instances", []):
            rel_path = instance["path"]
            if rel_path.endswith("_mask.png"):
                n_skipped_mask += 1
                continue

            src_path = IMAGES_DIR / rel_path
            if not src_path.exists():
                n_missing_src += 1
                continue

            out_class_dir.mkdir(parents=True, exist_ok=True)
            idx = class_counts.get(cls, 1)
            ext = src_path.suffix  # keep original extension (.png)
            out_path = out_class_dir / f"{cls}_{idx}{ext}"
            class_counts[cls] = idx + 1

            if out_path.exists() or out_path.is_symlink():
                n_existing += 1
                continue

            out_path.symlink_to(src_path.resolve())
            n_images += 1

    print(f"Classes: {len(class_counts)}")
    print(f"Images symlinked (new): {n_images}")
    print(f"Images already existing (skipped, resumable): {n_existing}")
    print(f"Mask files skipped: {n_skipped_mask}")
    print(f"Missing source files: {n_missing_src}")
    if skipped_annotations:
        print(f"Skipped annotations (couldn't derive make/model): {sorted(skipped_annotations)}")
    example_classes = sorted(class_counts)[:5]
    print(f"Example class folders: {example_classes}")


if __name__ == "__main__":
    main()
