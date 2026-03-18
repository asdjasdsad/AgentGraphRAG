from __future__ import annotations

import importlib
import shutil
import subprocess
import sys


def main() -> int:
    print(f"python={sys.version.split()[0]}")
    required = ["torch", "transformers", "datasets", "peft", "bitsandbytes", "trl"]
    failed = False
    for name in required:
        try:
            module = importlib.import_module(name)
            print(f"{name}={getattr(module, '__version__', 'unknown')}")
        except Exception as exc:
            failed = True
            print(f"{name}=ERROR:{exc}")
    try:
        import torch

        print(f"cuda_available={torch.cuda.is_available()}")
        print(f"cuda_count={torch.cuda.device_count()}")
        for idx in range(torch.cuda.device_count()):
            print(f"gpu[{idx}]={torch.cuda.get_device_name(idx)}")
    except Exception as exc:
        failed = True
        print(f"torch_cuda=ERROR:{exc}")
    if shutil.which("nvidia-smi"):
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=False,
        )
        print("nvidia_smi:")
        print(result.stdout.strip() or result.stderr.strip())
        if result.returncode != 0:
            failed = True
    else:
        print("nvidia-smi not found")
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
