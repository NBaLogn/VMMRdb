# /// script
# dependencies = ["scipy"]
# ///
"""Convert stanford-cars-dataset into a flat VMMRdb-style class tree.

Source:
  DATA/stanford-cars-dataset/car_devkit/devkit/cars_meta.mat
      -> cell array 'class_names', 196 entries like "AM General Hummer SUV 2000"
         or "Acura RL Sedan 2012". Inspected all 196 names: the year is ALWAYS
         the LAST whitespace token (a 19xx/20xx 4-digit number). The remaining
         tokens are "<Make> <Model...>", where a handful of makes are two
         words (AM General, Aston Martin, Land Rover) -- everything else is
         a single-word make. Note the final slug is a straight concatenation
         of all non-year tokens in order, so the make/model split point does
         not actually change the output path; it's kept only for a readable
         report.
  DATA/stanford-cars-dataset/car_devkit/devkit/cars_train_annos.mat
      -> struct array 'annotations': bbox_x1/y1/x2/y2, class (1-indexed into
         class_names), fname (filename in cars_train/cars_train/).
  DATA/stanford-cars-dataset/car_devkit/devkit/cars_test_annos.mat
      -> SAME struct shape but WITHOUT a 'class' field (classic Stanford Cars
         test-set labels are withheld) -> cars_test is skipped entirely.
  DATA/stanford-cars-dataset/cars_train/cars_train/*.jpg -- whole car photos,
      already car-centric like VMMRdb. bbox annotations exist but are NOT
      used for cropping (whole image is symlinked, matching VMMRdb style).

Output:
  DATA/stanfordcars_vmmr/<slug>/<slug>_<idx>.jpg  (symlinks to originals)

Usage:
  uv run code/preprocess/stanfordcars.py --sample 30
  uv run code/preprocess/stanfordcars.py            # full run (not run by this agent)
"""
import argparse
import re
import sys

sys.path.insert(
    0,
    "/Users/logan/Developer/vibes/WORK/CLS/VMMRdb/.claude/worktrees/vmmr-multi-dataset-prep/code/preprocess",
)
from naming import slug, DATA

SRC = DATA / "stanford-cars-dataset"
DEVKIT = SRC / "car_devkit" / "devkit"
TRAIN_IMAGES = SRC / "cars_train" / "cars_train"
OUT = DATA / "stanfordcars_vmmr"

YEAR_RE = re.compile(r"^(18|19|20)\d{2}$")
TWO_WORD_MAKES = {"AM General", "Aston Martin", "Land Rover"}


def parse_class_name(name: str):
    """'AM General Hummer SUV 2000' -> ('AM General', 'Hummer SUV', '2000')."""
    tokens = name.split()
    year_idx = None
    for i, tok in enumerate(tokens):
        if YEAR_RE.match(tok):
            year_idx = i
    if year_idx is None:
        return None
    year = tokens[year_idx]
    rest = tokens[:year_idx] + tokens[year_idx + 1:]
    if not rest:
        return None

    if year_idx == len(tokens) - 1:
        # "Make Model... Year" -- make is adjacent on the left.
        two_word = " ".join(rest[:2])
        if two_word in TWO_WORD_MAKES and len(rest) > 2:
            make, model = two_word, " ".join(rest[2:])
        else:
            make, model = rest[0], " ".join(rest[1:])
    else:
        # "Year Make Model..." -- make is adjacent on the right.
        two_word = " ".join(rest[:2])
        if two_word in TWO_WORD_MAKES and len(rest) > 2:
            make, model = two_word, " ".join(rest[2:])
        else:
            make, model = rest[0], " ".join(rest[1:])

    if not make or not model:
        return None
    return make, model, year


def load_mat(path):
    from scipy.io import loadmat

    return loadmat(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=None, help="process only first N images")
    args = ap.parse_args()

    meta = load_mat(DEVKIT / "cars_meta.mat")
    class_names = [str(x[0]) for x in meta["class_names"][0]]

    class_slugs = {}
    skipped_classes = []
    for i, name in enumerate(class_names, start=1):
        parsed = parse_class_name(name)
        if parsed is None:
            skipped_classes.append((i, name, "could not detect year token"))
            continue
        make, model, year = parsed
        class_slugs[i] = slug(make, model, year)

    train = load_mat(DEVKIT / "cars_train_annos.mat")
    ann = train["annotations"][0]

    test = load_mat(DEVKIT / "cars_test_annos.mat")
    test_has_class = "class" in (test["annotations"].dtype.names or ())

    records = []
    for row in ann:
        fname = str(row["fname"].item())
        cls_id = int(row["class"].item())
        records.append((fname, cls_id))
    records.sort(key=lambda r: r[0])  # deterministic order for resumable idx assignment

    if args.sample:
        records = records[: args.sample]

    OUT.mkdir(parents=True, exist_ok=True)

    n_images = 0
    skipped_images = []
    example_class_dirs = []
    slug_counters = {}  # slug -> next output index

    for fname, cls_id in records:
        class_slug = class_slugs.get(cls_id)
        if class_slug is None:
            skipped_images.append((fname, cls_id, "unmapped class id"))
            continue

        src_img = TRAIN_IMAGES / fname
        if not src_img.is_file():
            skipped_images.append((fname, cls_id, f"missing source file {src_img}"))
            continue

        out_dir = OUT / class_slug
        out_dir.mkdir(parents=True, exist_ok=True)

        idx = slug_counters.get(class_slug, 1)
        if class_slug not in example_class_dirs:
            example_class_dirs.append(class_slug)

        ext = src_img.suffix
        out_img = out_dir / f"{class_slug}_{idx}{ext}"
        if not out_img.exists():
            out_img.symlink_to(src_img.resolve())
        idx += 1
        n_images += 1

        slug_counters[class_slug] = idx

    print(f"images processed: {n_images}")
    print(f"unique output class folders: {len(slug_counters)}")
    print(f"example class folders: {sorted(example_class_dirs)[:5]}")
    print(f"cars_test: skipped entirely (test annotations has no 'class' field: "
          f"test_has_class={test_has_class}, {len(test['annotations'][0])} images unlabeled)")
    if skipped_classes:
        print(f"skipped class labels ({len(skipped_classes)}):")
        for cid, raw, reason in skipped_classes[:20]:
            print(f"  id={cid} raw={raw!r} reason={reason}")
    if skipped_images:
        print(f"skipped images ({len(skipped_images)}):")
        for fname, cid, reason in skipped_images[:20]:
            print(f"  fname={fname} class_id={cid} reason={reason}")


if __name__ == "__main__":
    main()
