# Phase 3 — clean the scraped image tree and emit train/val/test splits.
#
# Steps:
#   1. validate    drop corrupt / too-small images (defensive; scraper already filters)
#   2. dedup       perceptual-hash (pHash) within AND across classes:
#                    - intra-class near-dups -> keep one (listing reposts)
#                    - cross-class collisions -> drop from ALL classes (a frame that
#                      matches two make/models is ambiguous/mislabeled -> poison)
#   3. prune       drop classes with < --min-imgs after dedup (too few to learn)
#   4. split       stratified per-class train/val/test (default 70/15/15)
#                    written as a manifest + symlink-free file list; raw tree untouched
#
# Why pHash and not source-aware split: DDG gives no stable listing id, so we can't
# group-split by source. pHash dedup across the whole corpus is the defense against
# the sibling-leak failure documented in closeup-cls (near-dup in train & test ->
# inflated test acc). See memory closeup-cls-sut-leakage.
#
# Run:
#   uv run --with pillow --with imagehash code/build_dataset.py \
#       [--src data/vn_vmmr] [--min-imgs 15] [--val 0.15] [--test 0.15] [--seed 42]
# Out: meta/splits.json  (+ stats printed and embedded)

import argparse, json, random
from collections import defaultdict
from pathlib import Path

from PIL import Image
import imagehash

ROOT = Path(__file__).resolve().parents[1]
HASH_SIZE = 8          # pHash precision
NEAR = 5               # Hamming distance treated as "same image"


def phash(p):
    try:
        with Image.open(p) as im:
            return imagehash.phash(im.convert("RGB"), hash_size=HASH_SIZE)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT / "data" / "vn_vmmr"))
    ap.add_argument("--min-imgs", type=int, default=15)
    ap.add_argument("--val", type=float, default=0.15)
    ap.add_argument("--test", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    src = Path(a.src)
    rng = random.Random(a.seed)

    classes = sorted(d for d in src.iterdir() if d.is_dir())
    print(f"{len(classes)} class folders in {src}")

    # 1+2: hash everything, track which classes each hash appears in
    hashes = {}                          # path -> hash
    hash_classes = defaultdict(set)      # hash -> {class}
    bad = 0
    for d in classes:
        for p in d.glob("*.*"):
            h = phash(p)
            if h is None:
                bad += 1
                continue
            hashes[p] = h
            hash_classes[h].add(d.name)

    # cross-class poison: a hash seen in >1 class -> drop from all
    poison = {h for h, cs in hash_classes.items() if len(cs) > 1}

    # 2: intra-class near-dup collapse (greedy by bucket) + poison removal
    kept = defaultdict(list)             # class -> [paths]
    dropped_dup = dropped_poison = 0
    for d in classes:
        seen = []                        # kept hashes in this class
        for p in sorted(d.glob("*.*")):
            h = hashes.get(p)
            if h is None:
                continue
            if h in poison:
                dropped_poison += 1
                continue
            if any((h - k) <= NEAR for k in seen):
                dropped_dup += 1
                continue
            seen.append(h)
            kept[d.name].append(str(p.relative_to(src)))

    # 3: prune sparse classes
    final = {c: ps for c, ps in kept.items() if len(ps) >= a.min_imgs}
    pruned = len(kept) - len(final)

    # 4: stratified split
    splits = {"train": {}, "val": {}, "test": {}}
    tot = defaultdict(int)
    for c, ps in final.items():
        ps = ps[:]
        rng.shuffle(ps)
        n = len(ps)
        nval = int(n * a.val)
        ntest = int(n * a.test)
        parts = {"val": ps[:nval], "test": ps[nval:nval + ntest], "train": ps[nval + ntest:]}
        for sp, items in parts.items():
            if items:
                splits[sp][c] = items
                tot[sp] += len(items)

    out = {
        "src": str(src),
        "params": {"min_imgs": a.min_imgs, "val": a.val, "test": a.test, "seed": a.seed,
                   "phash_size": HASH_SIZE, "near_dist": NEAR},
        "stats": {
            "classes_in": len(classes),
            "classes_final": len(final),
            "classes_pruned_sparse": pruned,
            "corrupt_dropped": bad,
            "near_dup_dropped": dropped_dup,
            "cross_class_poison_dropped": dropped_poison,
            "images_final": sum(tot.values()),
            "train": tot["train"], "val": tot["val"], "test": tot["test"],
        },
        "splits": splits,
    }
    outpath = ROOT / "meta" / "splits.json"
    outpath.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out["stats"], indent=2))
    print("wrote", outpath)


if __name__ == "__main__":
    main()
