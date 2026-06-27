#!/usr/bin/env bash
# Download + unzip VMMRdb (~50GB, 9170 classes, 291752 imgs). One-time.
# ponytail: full dataset. For a quick test use the VMMRdb-3036 subset link in README instead.
set -euo pipefail
DATA_DIR="${1:-data}"
URL="https://www.dropbox.com/s/uwa7c5uz7cac7cw/VMMRdb.zip?dl=1"
mkdir -p "$DATA_DIR"
cd "$DATA_DIR"
echo "Downloading VMMRdb.zip (~50GB) -> $DATA_DIR/ ..."
curl -L -o VMMRdb.zip "$URL"
echo "Unzipping ..."
unzip -q VMMRdb.zip
echo "Done. Class folders under $DATA_DIR/"
