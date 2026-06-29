from dataclasses import dataclass
from typing import Any

import torch


@dataclass
class RuntimeBackend:
    name: str
    torch_device: Any
    yolo_device: Any
    use_half: bool


def resolve_backend(preferred: str = "auto") -> RuntimeBackend:
    preferred = str(preferred).lower()

    if preferred in {"directml", "dml", "amd"}:
        return _resolve_directml()
    if preferred == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but no CUDA GPU is available.")
        return RuntimeBackend(name="cuda", torch_device=torch.device("cuda:0"), yolo_device=torch.device("cuda:0"), use_half=True)
    if preferred == "cpu":
        return RuntimeBackend(name="cpu", torch_device=torch.device("cpu"), yolo_device="cpu", use_half=False)

    if torch.cuda.is_available():
        return RuntimeBackend(name="cuda", torch_device=torch.device("cuda:0"), yolo_device=torch.device("cuda:0"), use_half=True)

    try:
        return _resolve_directml()
    except Exception:
        return RuntimeBackend(name="cpu", torch_device=torch.device("cpu"), yolo_device="cpu", use_half=False)


def _resolve_directml() -> RuntimeBackend:
    try:
        import torch_directml
    except Exception as exc:
        raise RuntimeError(
            "DirectML runtime is not installed. Install it with: pip install torch-directml"
        ) from exc

    dml_device = torch_directml.device()
    return RuntimeBackend(name="directml", torch_device=dml_device, yolo_device=dml_device, use_half=False)
