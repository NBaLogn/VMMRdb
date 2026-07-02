#!/usr/bin/env -S uv run --script
"""Convert IDD_FGVD into a flat class-folder layout, EXTENDED variant of
idd_fgvd.py: in addition to the fine-grained "<type>_<Make>_<Model>" labels,
this variant also keeps the two generic vehicle-type labels idd_fgvd.py drops
as junk:
  - "bus"        -> its own class "bus" (no make/model in the source labels)
  - "car_Others" -> its own class "car_others" (car with unspecified make/model)

Everything else (crop logic, source layout, pooling all splits into one flat
tree, all other junk/no-model labels like "*_Others", "autorickshaw_Bajaj",
"Company_Model") is unchanged from idd_fgvd.py -- see that script for the
full label-filtering rationale.

Output:
  DATA/idd_fgvd_ext_vmmr/<class>/<class>_<sourceimgstem>_<objidx>.jpg
  (separate output dir from idd_fgvd.py's idd_fgvd_vmmr/, so both variants
  can coexist)

Usage:
  uv run code/preprocess/idd_fgvd_ext.py --sample 30
  uv run code/preprocess/idd_fgvd_ext.py
"""
import argparse
import sys
import xml.etree.ElementTree as ET

sys.path.insert(
    0,
    "/Users/logan/Developer/vibes/WORK/CLS/VMMRdb/.claude/worktrees/vmmr-multi-dataset-prep/code/preprocess",
)
from naming import slug, DATA  # noqa: E402

from PIL import Image

SRC = DATA / "IDD_FGVD"
OUT = DATA / "idd_fgvd_ext_vmmr"
SPLITS = ["train", "val", "test"]

GENERIC_CLASSES = {"bus": "bus", "car_Others": "car_others"}


def resolve_class(name):
    """Return an output class slug for `name`, or None to drop it.
    Adds the two generic type-only labels on top of idd_fgvd.py's rule."""
    if name in GENERIC_CLASSES:
        return GENERIC_CLASSES[name]
    parts = name.split("_")
    if len(parts) != 3:
        return None
    _type, make, model = parts
    if not make or not model:
        return None
    if make == "Others" or model == "Others":
        return None
    return slug(make, model)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=None,
                     help="Process only until this many total crops have been written (validation run).")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    total_crops = 0
    total_kept_objs = 0
    total_dropped_objs = 0
    classes_seen = set()
    stop = False

    for split in SPLITS:
        if stop:
            break
        anno_dir = SRC / split / "annos"
        img_dir = SRC / split / "images"
        if not anno_dir.is_dir():
            continue
        xml_files = sorted(anno_dir.glob("*.xml"))
        for xml_path in xml_files:
            if stop:
                break
            img_stem = xml_path.stem
            img_path = img_dir / f"{img_stem}.jpg"
            if not img_path.exists():
                candidates = list(img_dir.glob(f"{img_stem}.*"))
                if not candidates:
                    continue
                img_path = candidates[0]

            tree = ET.parse(xml_path)
            root = tree.getroot()
            size_el = root.find("size")
            img_w = img_h = None
            if size_el is not None:
                w_el, h_el = size_el.find("width"), size_el.find("height")
                if w_el is not None and w_el.text:
                    img_w = int(float(w_el.text))
                if h_el is not None and h_el.text:
                    img_h = int(float(h_el.text))

            objects = list(root.findall("object"))
            usable = []
            for obj_idx, obj in enumerate(objects):
                name_el = obj.find("name")
                name = name_el.text.strip() if name_el is not None and name_el.text else ""
                cls = resolve_class(name)
                if cls is None:
                    total_dropped_objs += 1
                    continue
                bnd = obj.find("bndbox")
                if bnd is None:
                    total_dropped_objs += 1
                    continue
                try:
                    xmin = float(bnd.find("xmin").text)
                    ymin = float(bnd.find("ymin").text)
                    xmax = float(bnd.find("xmax").text)
                    ymax = float(bnd.find("ymax").text)
                except (AttributeError, TypeError, ValueError):
                    total_dropped_objs += 1
                    continue
                total_kept_objs += 1
                usable.append((obj_idx, cls, (xmin, ymin, xmax, ymax)))

            if not usable:
                continue

            im = None
            for obj_idx, cls, (xmin, ymin, xmax, ymax) in usable:
                if args.sample is not None and total_crops >= args.sample:
                    stop = True
                    break

                out_dir = OUT / cls
                out_name = f"{cls}_{img_stem}_{obj_idx}.jpg"
                out_path = out_dir / out_name

                if out_path.exists():
                    classes_seen.add(cls)
                    total_crops += 1
                    continue

                if im is None:
                    im = Image.open(img_path)
                    im.load()
                    if im.mode != "RGB":
                        im = im.convert("RGB")

                w = img_w or im.width
                h = img_h or im.height
                cx0 = max(0, min(int(round(xmin)), w - 1))
                cy0 = max(0, min(int(round(ymin)), h - 1))
                cx1 = max(cx0 + 1, min(int(round(xmax)), w))
                cy1 = max(cy0 + 1, min(int(round(ymax)), h))

                crop = im.crop((cx0, cy0, cx1, cy1))
                out_dir.mkdir(parents=True, exist_ok=True)
                crop.save(out_path, "JPEG", quality=95)

                classes_seen.add(cls)
                total_crops += 1

    print(f"splits processed: {SPLITS}")
    print(f"objects kept (usable make/model+bbox, or bus/car_others): {total_kept_objs}")
    print(f"objects dropped (remaining junk/no-model/Others): {total_dropped_objs}")
    print(f"crops written (or already present): {total_crops}")
    print(f"classes: {len(classes_seen)}")
    print("example classes:", sorted(classes_seen)[:5])


if __name__ == "__main__":
    main()
