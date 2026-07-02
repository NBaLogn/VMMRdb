# Phase 0 — build VN vehicle make/model taxonomy from Chotot marketplace.
#
# Chotot is VN's largest classifieds; ad-listing API is keyless and exposes
# structured vehicle fields. We harvest the live market (newest 10k listings
# per category, the API hard-caps `total` at 10000) and reduce to a canonical
# make -> model -> {years, fuel, count} tree, plus a flat make_model_year
# class list for image scraping in Phase 2.
#
#   cars  (cg=2010): carbrand_name, carmodel_name, fuel, mfdate   -> clean, direct
#   motos (cg=2020): motorbikebrand/model are numeric codes only; names mined
#                    from `subject`, grouped by code pair for reliable clustering
#
# Run:  uv run --with requests code/scrape_taxonomy.py [pages_per_cat]
# Out:  meta/vn_classes.json
#
# ponytail: regex-mined moto names, not a code->name dict (Chotot hides theirs).
#           Upgrade path: if Chotot exposes a brand/model config endpoint, swap
#           the mining block for a direct lookup.

import json, re, sys, time, unicodedata
from collections import Counter, defaultdict
from pathlib import Path
import requests

API = "https://gateway.chotot.com/v1/public/ad-listing"
HEADERS = {"User-Agent": "Mozilla/5.0 (research; VN vehicle taxonomy build)"}
OUT = Path(__file__).resolve().parents[1] / "meta" / "vn_classes.json"
LIMIT = 50
DELAY = 0.12
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")

# Known VN motorcycle brands (subjects are free text; we anchor on these to
# split "brand model"). Electric-only brands also drive fuel inference.
MOTO_BRANDS = [
    "Honda", "Yamaha", "Suzuki", "Piaggio", "Vespa", "SYM", "Kymco", "Kawasaki",
    "Ducati", "BMW", "Harley", "Harley-Davidson", "KTM", "Benelli", "GPX",
    "Triumph", "Aprilia", "Royal Enfield", "CFMoto", "Brixton", "Lambretta",
    "VinFast", "Yadea", "Dat Bike", "DatBike", "Pega", "Dibao", "Detech",
    "Selex", "Vinbike", "Espero", "Anbico", "Halim", "Bluera", "DK Bike",
    "DKBike", "Nijia", "Giant", "Asama", "HTC", "Osakar",
    "Harley Davidson", "Harley-Davidson", "Royal-Enfield",
]
# map matched brand text -> canonical brand name
BRAND_ALIAS = {
    "harley": "Harley-Davidson", "harley davidson": "Harley-Davidson",
    "datbike": "Dat Bike", "dkbike": "DK Bike",
    "royal enfield": "Royal Enfield", "royal-enfield": "Royal Enfield",
}
EV_BRANDS = {"vinfast", "yadea", "dat bike", "datbike", "pega", "dibao", "selex",
             "vinbike", "espero", "anbico", "halim", "bluera", "dk bike", "dkbike",
             "nijia", "osakar"}
# longest-first so "Harley-Davidson" beats "Harley", "Dat Bike" beats nothing
MOTO_BRANDS_SORTED = sorted(set(MOTO_BRANDS), key=len, reverse=True)

# Truck brands (cg=2050 has truckbrand code but no name; anchor subject on these)
TRUCK_BRANDS = [
    "Thaco", "Hyundai", "Isuzu", "Kia", "Hino", "Suzuki", "Dongben", "DongBen",
    "Veam", "VEAM", "Dongfeng", "Howo", "JAC", "Tera", "Teraco", "Forland",
    "Mercedes-Benz", "Mercedes", "Fuso", "Chenglong", "FAW", "Foton", "SRM",
    "TMT", "Chiến Thắng", "Cửu Long", "Hoa Mai", "Daehan", "Shacman", "Maz",
    "Kamaz", "Thành Công",
]
TRUCK_BRANDS_SORTED = sorted(set(TRUCK_BRANDS), key=len, reverse=True)

# Bus / passenger-van brands (cg=2080 "other"; whitelist for precision since the
# category is dominated by construction/agri machinery we must exclude)
BUS_BRANDS = [
    "Ford", "Hyundai", "Mercedes-Benz", "Mercedes", "Toyota", "Thaco", "Samco",
    "Hino", "Daewoo", "Kia", "Iveco", "GAZ", "Isuzu", "Dcar", "Tracomeco",
    "Volvo", "King Long", "Higer", "Yutong", "Universe", "Limousine",
]
BUS_BRANDS_SORTED = sorted(set(BUS_BRANDS), key=len, reverse=True)

# Heavy construction / agri machinery & informal vehicles to EXCLUDE (forklift,
# excavator, bulldozer, road-roller, tractor, loader, 3-wheel cargo). Truck-
# mounted cranes/mixers stay — they are road trucks.
CONSTRUCTION = re.compile(
    r"\bxe\s+nâng|nâng\s+(điện|tay|bàn)|máy\s+xúc|\bxúc\s+lật|máy\s+ủi|"
    r"máy\s+kéo|máy\s+đào|máy\s+san|máy\s+nông\s+nghiệp|máy\s+phát|"
    r"công\s+trình|ba\s+gác|\blu\b|xe\s+lu|forklift|excavator|bulldozer|"
    r"\bsd\d|shibaura|komatsu", re.I)

# Payload / body-type descriptors that pollute mined truck & bus model names.
UNIT_NOISE = re.compile(
    r"\b\d+([.,]\d+)?\s*(tấn|tan|kg|t)\b|\b\d+\s*chỗ\b|"
    r"\b(tải|thùng|mui\s+bạt|mui|bạt|đông\s+lạnh|ben|sàn|inox|nhôm|kín|"
    r"lửng|chở|chỗ|máy\s+lạnh|xe\s+khách|xe\s+tải|xe\s+van|van)\b", re.I)

NOISE = re.compile(
    r"\b(cần\s+bán|bán\s+gấp|bán|chính\s+chủ|chính\s+hãng|xe|"
    r"mới|cũ|thanh\s+lý|như\s+mới|giá\s+rẻ|nguyên\s+bản|"
    r"đẹp|zin|đời|biển\s+số|biển|lướt|odo|km|máy\s+êm|"
    r"nhật|thái|sẵn|có\s+sẵn|đa\s+dạng\s+màu|full|bao|còn|"
    r"tin|nguyên|sóc|hn|hcm|sg|tp\.?hcm|tp|đn|hà\s+nội|sài\s+gòn)\b", re.I)
# trailing Vietnamese colour words leak into mined model names
COLOR = re.compile(
    r"\b(đỏ|xanh(\s+(dương|lá|lam|ngọc|rêu))?|đen|trắng|xám|ghi|"
    r"vàng|bạc|cam|nâu|tím|hồng|kem|be|xanh)\b", re.I)
# mined "models" that are pure noise -> drop the class
JUNK_MODEL = re.compile(
    r"^(luôn|máy|đa|nhật|biển|có|còn|full|bao|odo|km|lướt|"
    r"giá|xe|chính|đẹp|zin|mới|cũ)$", re.I)


def fetch(cg, pages):
    """Yield ad dicts across `pages` offset pages for category cg."""
    seen = set()
    for p in range(pages):
        o = p * LIMIT
        url = f"{API}?cg={cg}&limit={LIMIT}&o={o}&st=s,k"
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            ads = r.json().get("ads", [])
        except Exception as e:
            print(f"  page {p} err: {e}", file=sys.stderr)
            time.sleep(DELAY)
            continue
        if not ads:
            break
        new = 0
        for ad in ads:
            lid = ad.get("list_id")
            if lid in seen:
                continue
            seen.add(lid)
            new += 1
            yield ad
        if new == 0:
            break
        time.sleep(DELAY)


def norm_year(v):
    try:
        y = int(str(v)[:4])
        return y if 1950 <= y <= 2026 else None
    except (TypeError, ValueError):
        return None


def slug(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "d")
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return s


def fuel_norm(v):
    # Chotot car `fuel` is a numeric code: 1=xăng 2=dầu 3=hybrid 4=điện
    return {1: "gas", 2: "diesel", 3: "hybrid", 4: "electric"}.get(v, "gas")


def build_cars(pages):
    tree = defaultdict(lambda: defaultdict(lambda: {"years": Counter(), "fuel": Counter(), "count": 0}))
    n = 0
    for ad in fetch(2010, pages):
        brand = (ad.get("carbrand_name") or "").strip()
        model = (ad.get("carmodel_name") or "").strip()
        if not brand or not model:
            continue
        n += 1
        rec = tree[brand][model]
        rec["count"] += 1
        y = norm_year(ad.get("mfdate"))
        if y:
            rec["years"][y] += 1
        rec["fuel"][fuel_norm(ad.get("fuel"))] += 1
    print(f"cars: {n} ads -> {len(tree)} brands")
    return tree


def parse_named(subject, brands_sorted, extra=None):
    """Mine (brand, model) from a free-text subject anchored on a brand list."""
    s = subject.strip()
    for b in brands_sorted:
        m = re.search(re.escape(b), s, re.I)
        if not m:
            continue
        brand = BRAND_ALIAS.get(b.lower(), b)
        rest = s[m.end():]
        rest = YEAR_RE.split(rest)[0]          # cut at first year
        rest = NOISE.sub(" ", rest)
        rest = COLOR.sub(" ", rest)
        if extra:                              # strip units (e.g. "6.5 tấn") before
            rest = extra.sub(" ", rest)        # the punctuation cut, so decimals survive
        rest = re.split(r"[,\(\)\|/]", rest)[0]
        rest = re.sub(r"\s+", " ", rest).strip(" -_")
        # model = meaningful tokens; drop colour leftovers and odo/price (>=1000)
        toks = []
        for t in rest.split():
            if t.isdigit() and int(t) >= 1000:   # odometer / price, not displacement
                continue
            if len(t) > 1 or t.isdigit():
                toks.append(t)
        model = " ".join(toks[:3]).strip()
        if not model or JUNK_MODEL.match(model):
            return brand, None
        return brand, model
    return None, None


def parse_moto(subject):
    return parse_named(subject, MOTO_BRANDS_SORTED)


def build_motos(pages):
    # group by (brandcode, modelcode) to cluster identical models, then pick the
    # modal mined (brand, model) string per cluster.
    clusters = defaultdict(lambda: {"names": Counter(), "years": Counter(),
                                     "ev": 0, "count": 0})
    n = 0
    for ad in fetch(2020, pages):
        subj = ad.get("subject") or ""
        brand, model = parse_moto(subj)
        if not brand or not model:
            continue
        n += 1
        key = (ad.get("motorbikebrand"), ad.get("motorbikemodel"))
        c = clusters[key]
        c["names"][(brand, model)] += 1
        c["count"] += 1
        y = norm_year(ad.get("regdate"))
        if y:
            c["years"][y] += 1
        if brand.lower() in EV_BRANDS or "điện" in subj.lower():
            c["ev"] += 1

    tree = defaultdict(lambda: defaultdict(lambda: {"years": Counter(), "fuel": Counter(), "count": 0}))
    for c in clusters.values():
        if not c["names"]:
            continue
        (brand, model), _ = c["names"].most_common(1)[0]
        rec = tree[brand][model]
        rec["count"] += c["count"]
        rec["years"].update(c["years"])
        fuel = "electric" if c["ev"] * 2 >= c["count"] else "gas"
        rec["fuel"][fuel] += c["count"]
    print(f"motos: {n} ads -> {len(tree)} brands")
    return tree


def build_trucks(pages):
    # cg=2050 has truckbrand code (no model); cluster by (code, mined-model).
    clusters = defaultdict(lambda: {"names": Counter(), "years": Counter(),
                                    "fuel": Counter(), "count": 0})
    n = skipped = 0
    for ad in fetch(2050, pages):
        subj = ad.get("subject") or ""
        if CONSTRUCTION.search(subj):
            skipped += 1
            continue
        brand, model = parse_named(subj, TRUCK_BRANDS_SORTED, UNIT_NOISE)
        if not brand or not model:
            continue
        n += 1
        c = clusters[(ad.get("truckbrand"), model.lower())]
        c["names"][(brand, model)] += 1
        c["count"] += 1
        y = norm_year(ad.get("mfdate"))
        if y:
            c["years"][y] += 1
        c["fuel"][fuel_norm(ad.get("fuel"))] += 1

    tree = defaultdict(lambda: defaultdict(lambda: {"years": Counter(), "fuel": Counter(), "count": 0}))
    for c in clusters.values():
        (brand, model), _ = c["names"].most_common(1)[0]
        rec = tree[brand][model]
        rec["count"] += c["count"]
        rec["years"].update(c["years"])
        rec["fuel"].update(c["fuel"])
    print(f"trucks: {n} ads ({skipped} construction skipped) -> {len(tree)} brands")
    return tree


def build_buses(pages):
    # cg=2080 "other vehicles": no brand field, dominated by machinery -> mine
    # against a bus/van whitelist and drop construction/agri/3-wheel subjects.
    tree = defaultdict(lambda: defaultdict(lambda: {"years": Counter(), "fuel": Counter(), "count": 0}))
    n = skipped = 0
    for ad in fetch(2080, pages):
        subj = ad.get("subject") or ""
        if CONSTRUCTION.search(subj):
            skipped += 1
            continue
        brand, model = parse_named(subj, BUS_BRANDS_SORTED, UNIT_NOISE)
        if not brand or not model:
            continue
        n += 1
        rec = tree[brand][model]
        rec["count"] += 1
        y = norm_year(ad.get("mfdate"))
        if y:
            rec["years"][y] += 1
        rec["fuel"][fuel_norm(ad.get("fuel"))] += 1
    print(f"buses/vans: {n} ads ({skipped} construction skipped) -> {len(tree)} brands")
    return tree


def finalize(tree, min_count):
    """Counter -> sorted lists; drop ultra-rare (likely-noise) models."""
    out = {}
    for brand in sorted(tree):
        if "khác" in brand.lower():            # "Hãng khác" = other brand
            continue
        models = {}
        for model in sorted(tree[brand]):
            r = tree[brand][model]
            if r["count"] < min_count:
                continue
            if "khác" in model.lower():         # "Dòng khác" = other model
                continue
            models[model] = {
                "count": r["count"],
                "years": sorted(r["years"]),
                "fuel": [f for f, _ in r["fuel"].most_common()],
            }
        if models:
            out[brand] = models
    return out


def flat_classes(*trees):
    classes = []
    for tree in trees:
        for brand, models in tree.items():
            for model, r in models.items():
                for y in r["years"]:
                    classes.append(f"{slug(brand)}_{slug(model)}_{y}")
    return sorted(set(classes))


def selftest():
    cases = {
        "Honda Win 100 Đỏ 2020 chính chủ": ("Honda", "Win 100"),
        "Cần bán Yamaha Exciter 150 odo 5000 km": ("Yamaha", "Exciter 150"),
        "Harley Davidson 48 biển đẹp": ("Harley-Davidson", "48"),
        "Dat Bike Quantum S3 Xám": ("Dat Bike", "Quantum S3"),
        "Brixton luôn có sẵn": ("Brixton", None),
        "Pega Đen 35000 km": ("Pega", None),
    }
    for subj, exp in cases.items():
        got = parse_moto(subj)
        assert got == exp, f"{subj!r}: got {got}, want {exp}"
    assert fuel_norm(4) == "electric" and fuel_norm(1) == "gas"

    # trucks: payload/body descriptors stripped from model
    assert parse_named("Thaco Ollin 500B 4995 kg máy lạnh mui bạt",
                       TRUCK_BRANDS_SORTED, UNIT_NOISE) == ("Thaco", "Ollin 500B")
    assert parse_named("Hyundai HD99 6.5 tấn 2016 Thùng nhôm",
                       TRUCK_BRANDS_SORTED, UNIT_NOISE) == ("Hyundai", "HD99")
    # buses/vans whitelist
    assert parse_named("Xe khách Ford Transit LX 2015 16 chỗ",
                       BUS_BRANDS_SORTED, UNIT_NOISE) == ("Ford", "Transit LX")
    # construction/agri excluded
    for s in ["Xe nâng Komatsu 1.5 Tấn", "Máy xúc Hyundai Vàng",
              "Máy ủi Komatsu D50P", "Xe ba gác Xanh", "Máy kéo nông nghiệp"]:
        assert CONSTRUCTION.search(s), f"should exclude: {s}"
    assert not CONSTRUCTION.search("Thaco Ollin 500B 2 tấn"), "truck wrongly excluded"
    print("selftest ok")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        selftest()
        return
    pages = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    print(f"harvesting up to {pages*LIMIT} ads/category ...")
    cars = finalize(build_cars(pages), min_count=2)
    motos = finalize(build_motos(pages), min_count=3)
    trucks = finalize(build_trucks(pages), min_count=3)
    buses = finalize(build_buses(pages), min_count=2)   # buses scarce on classifieds
    classes = flat_classes(cars, motos, trucks, buses)

    def nmodels(t):
        return sum(len(m) for m in t.values())
    doc = {
        "source": "chotot.com ad-listing API "
                   "(cg=2010 cars, 2020 motorbikes, 2050 trucks, 2080 buses/vans)",
        "built": time.strftime("%Y-%m-%d"),
        "note": "construction/agri machinery (forklift, excavator, etc.) excluded",
        "stats": {
            "car_brands": len(cars), "car_models": nmodels(cars),
            "moto_brands": len(motos), "moto_models": nmodels(motos),
            "truck_brands": len(trucks), "truck_models": nmodels(trucks),
            "bus_brands": len(buses), "bus_models": nmodels(buses),
            "flat_classes": len(classes),
        },
        "cars": cars,
        "motorbikes": motos,
        "trucks": trucks,
        "buses": buses,
        "classes": classes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(doc["stats"], indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
