# Vehicle Make/Model Datasets — Reference for TRUCK / SUV / MOTORCYCLE (+ car)

Research compiled 2026-06-27. 6 parallel web searches → 31 datasets verified (URL/access checked) → ranked.

## 1. Comparison table

| Dataset | Types | Task | Granularity | Size | Access |
|---|---|---|---|---|---|
| [VMMRdb](https://github.com/faezetta/VMMRdb) | US cars, light trucks, some SUVs; no motorcycles | classification | make+model+year | 291,752 img / 9,170 cls | Public (Dropbox/GitHub; [Kaggle mirror](https://www.kaggle.com/datasets/abhishektyagi001/vehicle-make-model-recognition-dataset-vmmrdb)); MIT |
| [Stanford Cars-196](https://www.kaggle.com/datasets/eduardo4jesus/stanford-cars-dataset) | cars only (SUV/pickup body styles, not labeled separately) | both | make+model+year | 16,185 img / 196 cls | Kaggle / [HF](https://huggingface.co/datasets/tanganke/stanford_cars); orig Stanford URL dead; research-use |
| [CompCars](https://mmlab.ie.cuhk.edu.hk/datasets/comp_cars/) | cars only | both | make+model | ~214K img / 1,716 mdl / 163 mk | Request (password file on page); non-commercial |
| [BoxCars116k](https://github.com/JakubSochor/BoxCars) | EU surveillance cars only | both (pre-cropped) | make+model+submodel+year | 116,286 img / 693 cls | Torrent/[GDrive](https://drive.google.com/file/d/19LHLOmmVyUS1R4ypwByfrV8KQWnz2GDT/view); primary host down; non-commercial |
| [Car-1000](https://github.com/toggle1995/Car-1000) | cars: sedan/**SUV**/**truck**/sports/van/MPV/bus; no motorcycles | classification | make+model | 140,267 img / 1,000 cls / 166 mk | Public (GDrive/Baidu in README); CC BY 4.0 |
| [kingjosephm VMM](https://github.com/kingjosephm/vehicle_make_model_dataset) | US cars, **SUVs**, **pickup trucks**; no motorcycles | classification | make+model (574) / +year (5,287) | 664,678 img / 574 cls / 40 mk | Request (email author); no license |
| [FGVD](https://zenodo.org/records/7488960) | cars, **motorcycles**/scooters, **trucks**, buses, autorickshaws (India) | detection | make+model (3-lvl) | 5,502 img / 24,450 boxes / ~217 cls | Public Zenodo (2.8 GB); CC BY 4.0 / BSD-3 code |
| [Pakistan Traffic](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2025.1561899/full) | cars, **motorcycles**, vans, buses, **trucks** (S. Asia) | classification | make+model+generation | 129,000 img / 94 cls | Request (author contact); CC BY |
| [Motorcycle Tech Specs](https://www.kaggle.com/datasets/emmanuelfwerr/motorcycle-technical-specifications-19702022) | **motorcycles** only — TABULAR, 0 images | (taxonomy ref) | make+model+year | 38,472 rows / 600+ brands | Kaggle (free acct) |
| [leogodin217 moto-cls](https://github.com/leogodin217/motorcycle_classification) | **motorcycles** only | classification | make+model+year | ~2,800 img / 366 cls (scrape-yourself) | Public repo, no data (Bing API + Azure key) |
| [DVM-CAR](https://deepvisualmarketing.github.io/) | UK cars only | classification | make+model+year+colour+trim | 1,451,784 img / 899 mdl | Figshare; CC BY-NC 4.0 |
| [car_models_3887](https://huggingface.co/datasets/Unit293/car_models_3887) | cars only | classification | make+model+year | ~193K img / 3,778 cls | HF (no login); license "other" |
| [Mendeley Vehicle Images](https://data.mendeley.com/datasets/hj3vvx5946/1) | cars-dominant | classification | make+model | 3,847 img / 48 cls | Public; CC BY 4.0 |
| [Roboflow Car MMY](https://universe.roboflow.com/senior-design-mzwsh/car-make-model-year) | cars (= Stanford Cars rehost) | classification | make+model+year | ~10,111 img / 196 cls | Roboflow (free acct) |
| [VeRi-Wild](https://github.com/PKU-IMRE/VERI-Wild) / [VeRi-776](https://github.com/JDAI-CV/VeRidataset) | cars (incl. SUV/pickup/truck *type*) | Re-ID / detection | **make only** | 416K / 50K img | Request (email); non-commercial |
| [Vehicles-OpenImages](https://public.roboflow.com/object-detection/vehicles-openimages) | cars, buses, motorcycles, trucks, ambulances | detection | **coarse type only** | 627 img / 5 cls | Roboflow public; CC BY 4.0 |
| [DAWN](https://ieee-dataport.org/documents/dawn-vehicle-detection-adverse-weather-nature) | cars, buses, trucks, motorcycles, bicycles | detection | **coarse type only** | 1,000 img / 6 cls | Mendeley/IEEE; CC BY 4.0 |
| [I24-3D](https://i24motion.org/data) | sedan/SUV/van/pickup/semi/truck (highway) | detection | **coarse type only** | 877K 3D boxes / 720 veh | Request (free acct); academic+commercial |

## 2. Best coverage for the UNDER-served types

**TRUCK (pickup/light) + SUV — make/model:**
- **[kingjosephm VMM](https://github.com/kingjosephm/vehicle_make_model_dataset)** — strongest. 664K US images with first-class pickups (F-Series, RAM, Silverado, Sierra, Tacoma, Tundra) and SUVs/crossovers. Email for images; no license.
- **[Car-1000](https://github.com/toggle1995/Car-1000)** — SUV and truck are primary body types among 1,000 make/model classes; CC BY 4.0, good post-2020 recency, public download.
- **[VMMRdb](https://github.com/faezetta/VMMRdb)** — light trucks/SUVs present but not broken out as types; already local.

**MOTORCYCLE — make/model (the hardest gap):**
- **[FGVD](https://zenodo.org/records/7488960)** — only solid *image* dataset with fine-grained two-wheeler make/model, but **Indian brands only** (Hero, Bajaj, TVS…), detection boxes, no Western OEMs, no year.
- **[Pakistan Traffic](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2025.1561899/full)** — S. Asian motorcycle make/model+generation; request-only, no boxes.
- **[leogodin217](https://github.com/leogodin217/motorcycle_classification)** — Western bikes but you must re-scrape (~2,800 img, Bing API); pipeline template, not a dataset.
- **[Motorcycle Tech Specs](https://www.kaggle.com/datasets/emmanuelfwerr/motorcycle-technical-specifications-19702022)** — taxonomy/label list only, zero images.

**Trucks/SUV/moto detection (coarse, for a detect→crop→classify pipeline):** [Vehicles-OpenImages](https://public.roboflow.com/object-detection/vehicles-openimages), [DAWN](https://ieee-dataport.org/documents/dawn-vehicle-detection-adverse-weather-nature), [I24-3D](https://i24motion.org/data) — type-level only, no make/model.

## 3. Recommended combination (all four types, make/model labels)

Western/US-market target:
1. **Cars** — [VMMRdb](https://github.com/faezetta/VMMRdb) (already local) + [Stanford Cars](https://www.kaggle.com/datasets/eduardo4jesus/stanford-cars-dataset) for boxes/baseline.
2. **Trucks + SUVs** — [kingjosephm VMM](https://github.com/kingjosephm/vehicle_make_model_dataset) (primary) and/or [Car-1000](https://github.com/toggle1995/Car-1000) (open license, recent).
3. **Motorcycles** — no good Western make/model image set exists → bootstrap [leogodin217](https://github.com/leogodin217/motorcycle_classification) scraper using [Motorcycle Tech Specs](https://www.kaggle.com/datasets/emmanuelfwerr/motorcycle-technical-specifications-19702022) as the label taxonomy; or accept S. Asian coverage via [FGVD](https://zenodo.org/records/7488960).
4. **Detection front-end** (if needed) — [Vehicles-OpenImages](https://public.roboflow.com/object-detection/vehicles-openimages) / [DAWN](https://ieee-dataport.org/documents/dawn-vehicle-detection-adverse-weather-nature) for coarse box proposals, then route crops to the classifiers above.

If S. Asian market is acceptable, **[Pakistan Traffic](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2025.1561899/full)** + **[FGVD](https://zenodo.org/records/7488960)** alone cover all four types with make/model in one domain.

## 4. Gaps

- **Western motorcycle make/model imagery does not exist as a ready dataset** — every image source is either Indian/Pakistani (FGVD, Pakistan), scrape-yourself (leogodin217), or tabular-only (Tech Specs). This is the binding constraint; budget for scraping.
- **Heavy/commercial trucks (semis): no make/model anywhere** — only coarse "truck/semi" type labels (I24-3D, DAWN). Make/model truck coverage = pickups only.
- **No single dataset spans all four types with Western make/model+year** — you must combine domains; expect domain shift (web vs. CCTV vs. dashcam, US vs. India).
- **License mixing:** CompCars/BoxCars/VeRi/DVM-CAR are non-commercial; kingjosephm and leogodin217 have no license (redistribution risk). Commercial-safe make/model sets = Car-1000 (CC BY) and FGVD (CC BY).
- **SUV is rarely a labeled dimension** — in most car sets it's a body style folded into make/model, not a separate type (explicit only in Car-1000, kingjosephm).
