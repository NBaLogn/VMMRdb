"""Smoke test: fake 2-class ImageFolder -> 1 train epoch -> save -> reload like api. assert it runs."""
import subprocess, sys, tempfile, json
from pathlib import Path
from PIL import Image
import torch
from torchvision import models

d = Path(tempfile.mkdtemp())
for cls in ("ford_focus_2010", "honda_civic_2012"):
    p = d / cls; p.mkdir()
    for i in range(6):
        Image.new("RGB", (300, 300), (i * 30, cls.startswith("h") * 200, 50)).save(p / f"{i}.jpg")

out = d / "model.pt"
r = subprocess.run([sys.executable, "train.py", "--data", str(d), "--epochs", "1",
                    "--batch", "4", "--workers", "0", "--out", str(out)],
                   cwd=Path(__file__).parent, capture_output=True, text=True)
print(r.stdout[-500:]); print(r.stderr[-500:], file=sys.stderr)
assert r.returncode == 0, "train.py failed"
assert out.exists(), "no checkpoint"

ck = torch.load(out, map_location="cpu", weights_only=True)
assert ck["classes"] == ["ford_focus_2010", "honda_civic_2012"]
m = models.resnet50(num_classes=len(ck["classes"]))
m.load_state_dict(ck["state_dict"]); m.eval()
with torch.no_grad():
    y = m(torch.randn(1, 3, 224, 224))
assert y.shape == (1, 2)
print("SMOKE OK: train+save+reload+forward all pass")
