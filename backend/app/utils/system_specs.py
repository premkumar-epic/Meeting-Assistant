from __future__ import annotations

import os
import torch
import functools
from typing import Any


@functools.lru_cache(maxsize=1)
def get_system_specs() -> dict[str, Any]:
    """
    Probe the host system resources (RAM, CPU, GPU) dynamically.
    Works natively on Linux without external dependencies.
    """
    ram_gb = 8.0  # Default fallback
    cpu_count = os.cpu_count() or 4
    gpu_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if gpu_available else None
    
    # Read total RAM from /proc/meminfo on Linux
    try:
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        mem_kb = int(line.split()[1])
                        ram_gb = round(mem_kb / (1024 * 1024), 2)
                        break
    except Exception:
        pass
        
    # Categorize hardware tier based on RAM
    if ram_gb < 8.0:
        recommendation_tier = "low"
    elif ram_gb < 16.0:
        recommendation_tier = "medium"
    else:
        recommendation_tier = "high"
        
    return {
        "ram_gb": ram_gb,
        "cpu_count": cpu_count,
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "recommendation_tier": recommendation_tier
    }
