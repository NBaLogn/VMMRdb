#!/usr/bin/env -S uv run --script
"""Convert IDD_FGVD (Indian Driving Dataset - Fine Grained Vehicle Detection)
into the VMMRdb flat-class-folder layout.

Source layout:
    data/IDD_FGVD/{train,val,test}/images/<id>.jpg
    data/IDD_FGVD/{train,val,test}/annos/<id>.xml   (Pascal-VOC style, multiple <object> per file)

Each XML can contain multiple <object> entries (multiple vehicles per driving-scene
photo), so unlike the other VMMR source datasets this one is CROPPED per bounding
box -- real re-encoded JPEG bytes are written, not symlinks.

<object><name> is one of:
  - "<type>_<Make>_<Model>"  e.g. "car_Honda_City" -> keep, make=Make, model=Model
  - "<type>_<Make>"          e.g. "autorickshaw_Bajaj" -> DROP (no model)
  - junk: "bus", "car_Others", "*_Others", "Company_Model", "Give Reason for Other",
    "Is model new?", or anything not matching the 3-part pattern with non-"Others"
    Make/Model -> DROP

All three splits (train/val/test) are pooled into one flat output tree; the
train/val/test split from this source dataset is NOT preserved (re-splitting
happens later, separately, across the whole VMMRdb pool).
"""
import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(
    0,
    "/Users/logan/Developer/vibes/WORK/CLS/VMMRdb/.claude/worktrees/vmmr-multi-dataset-prep/code/preprocess",
)
from naming import slug, DATA  # noqa: E402

from PIL import Image

SRC = DATA / "IDD_FGVD"
OUT = DATA / "idd_fgvd_vmmr"
SPLITS = ["train", "val", "test"]


def parse_object_name(name):
    """Return (make, model) if `name` is a usable 3-part '<type>_<Make>_<Model>'
    label, else None (junk / no-model / *_Others)."""
    parts = name.split("_")
    if len(parts) != 3:
        return None
    _type, make, model = parts
    if not make or not model:
        return None
    if make == "Others" or model == "Others":
        return None
    return make, model


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
                # try other common extensions
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
                parsed = parse_object_name(name)
                if parsed is None:
                    total_dropped_objs += 1
                    continue
                make, model = parsed
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
                usable.append((obj_idx, make, model, (xmin, ymin, xmax, ymax)))

            if not usable:
                continue

            im = None
            for obj_idx, make, model, (xmin, ymin, xmax, ymax) in usable:
                if args.sample is not None and total_crops >= args.sample:
                    stop = True
                    break

                cls = slug(make, model)
                out_dir = OUT / cls
                out_name = f"{cls}_{img_stem}_{obj_idx}.jpg"
                out_path = out_dir / out_name

                if out_path.exists():
                    # idempotent/resumable: skip already-produced crops
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
    print(f"objects kept (usable make/model+bbox): {total_kept_objs}")
    print(f"objects dropped (junk/no-model/Others): {total_dropped_objs}")
    print(f"crops written (or already present): {total_crops}")
    print(f"classes: {len(classes_seen)}")
    print("example classes:", sorted(classes_seen)[:5])


if __name__ == "__main__":
    main()
