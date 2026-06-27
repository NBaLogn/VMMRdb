import torch
from torchvision import datasets
new = set(datasets.ImageFolder("data", allow_empty=True).classes)
old = set(torch.load("model.pt", map_location="cpu", weights_only=True)["classes"])
print("removed:", old - new)
print("added:", new - old)
