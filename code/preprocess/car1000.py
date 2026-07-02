"""Convert Car-1000-dataset into a flat VMMRdb-style class tree.

Source:
  DATA/Car-1000-dataset/cls_info/class_info.json
      -> list of {"id", "name_from_new", "name_from_old", "type_info"}
      "name_from_old" = "<zh>_<zh>==<EnglishMake>_<EnglishModel>"
  DATA/Car-1000-dataset/all_images/<id>/<id>_<n>.jpg

Output:
  DATA/car1000_vmmr/<slug>/<slug>_<idx>.jpg  (symlinks to originals, no crop needed)

No year label is available -> slug(make, model, year=None).
Multiple source class ids that normalize to the same slug (e.g. distinct
trims of the same make/model) are merged into one output class folder with
a continuous image index.

Usage:
  uv run code/preprocess/car1000.py --sample 30
  uv run code/preprocess/car1000.py            # full run (not run by this agent)
"""
import argparse
import json
import sys

sys.path.insert(
    0,
    "/Users/logan/Developer/vibes/WORK/CLS/VMMRdb/.claude/worktrees/vmmr-multi-dataset-prep/code/preprocess",
)
from naming import slug, DATA

SRC = DATA / "Car-1000-dataset"
CLASS_INFO = SRC / "cls_info" / "class_info.json"
IMAGES_DIR = SRC / "all_images"
OUT = DATA / "car1000_vmmr"


def parse_make_model(name_from_old: str):
    """'江铃_凯运==JMC_Kaiyun' -> ('JMC', 'Kaiyun')."""
    if "==" not in name_from_old:
        return None
    _, eng = name_from_old.split("==", 1)
    eng = eng.strip()
    if "_" not in eng:
        return None
    make, model = eng.split("_", 1)
    make = make.strip()
    model = model.strip()
    if not make or not model:
        return None
    return make, model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=None, help="process only first N classes")
    args = ap.parse_args()

    with open(CLASS_INFO, encoding="utf-8") as f:
        classes = json.load(f)

    if args.sample:
        classes = classes[: args.sample]

    OUT.mkdir(parents=True, exist_ok=True)

    n_classes_seen = 0
    n_images = 0
    skipped_labels = []
    example_class_dirs = []
    slug_counters = {}  # slug -> next output index

    for entry in classes:
        cid = entry.get("id")
        name_from_old = entry.get("name_from_old", "")
        parsed = parse_make_model(name_from_old)
        if parsed is None:
            skipped_labels.append((cid, name_from_old, "unparseable name_from_old"))
            continue

        make, model = parsed
        class_slug = slug(make, model, year=None)
        if not class_slug:
            skipped_labels.append((cid, name_from_old, "empty slug"))
            continue

        src_dir = IMAGES_DIR / cid
        if not src_dir.is_dir():
            skipped_labels.append((cid, name_from_old, f"missing image dir {src_dir}"))
            continue

        src_images = sorted(src_dir.glob(f"{cid}_*.jpg"))
        if not src_images:
            skipped_labels.append((cid, name_from_old, "no images found"))
            continue

        out_dir = OUT / class_slug
        out_dir.mkdir(parents=True, exist_ok=True)

        idx = slug_counters.get(class_slug, 1)
        if class_slug not in example_class_dirs:
            example_class_dirs.append(class_slug)

        for src_img in src_images:
            ext = src_img.suffix
            out_img = out_dir / f"{class_slug}_{idx}{ext}"
            if not out_img.exists():
                out_img.symlink_to(src_img.resolve())
            idx += 1
            n_images += 1

        slug_counters[class_slug] = idx
        n_classes_seen += 1

    print(f"classes processed: {n_classes_seen}")
    print(f"unique output class folders: {len(slug_counters)}")
    print(f"images linked: {n_images}")
    print(f"example class folders: {example_class_dirs[:5]}")
    if skipped_labels:
        print(f"skipped labels ({len(skipped_labels)}):")
        for cid, raw, reason in skipped_labels[:20]:
            print(f"  id={cid} raw={raw!r} reason={reason}")


if __name__ == "__main__":
    main()
