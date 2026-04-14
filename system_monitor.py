import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SystemStats:
    cpu_percent: float = 0.0
    mem_percent: float = 0.0
    gpu_percent: Optional[float] = None
    gpu_mem_percent: Optional[float] = None


class SystemMonitor:
    """CPU/内存（psutil）+ 可选 NVIDIA GPU（pynvml）采集。"""

    def __init__(self) -> None:
        self._psutil = None
        self._pynvml = None
        self._gpu_handle = None
        try:
            import psutil  # type: ignore
            self._psutil = psutil
            psutil.cpu_percent(interval=None)  # 预热
        except ImportError:
            logger.warning("psutil 未安装，CPU/内存监控禁用")
        try:
            import pynvml  # type: ignore
            pynvml.nvmlInit()
            if pynvml.nvmlDeviceGetCount() > 0:
                self._pynvml = pynvml
                self._gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            self._pynvml = None

    def sample(self) -> SystemStats:
        stats = SystemStats()
        if self._psutil is not None:
            try:
                stats.cpu_percent = float(self._psutil.cpu_percent(interval=None))
                stats.mem_percent = float(self._psutil.virtual_memory().percent)
            except Exception as exc:
                logger.debug("psutil 采样失败: %s", exc)
        if self._pynvml is not None and self._gpu_handle is not None:
            try:
                util = self._pynvml.nvmlDeviceGetUtilizationRates(self._gpu_handle)
                mem = self._pynvml.nvmlDeviceGetMemoryInfo(self._gpu_handle)
                stats.gpu_percent = float(util.gpu)
                stats.gpu_mem_percent = float(mem.used) / float(mem.total) * 100.0
            except Exception as exc:
                logger.debug("pynvml 采样失败: %s", exc)
        return stats

    def format_stats(self, stats: SystemStats) -> str:
        parts = [f"CPU: {stats.cpu_percent:.0f}%", f"内存: {stats.mem_percent:.0f}%"]
        if stats.gpu_percent is not None:
            parts.append(f"GPU: {stats.gpu_percent:.0f}%")
            if stats.gpu_mem_percent is not None:
                parts.append(f"显存: {stats.gpu_mem_percent:.0f}%")
        else:
            parts.append("GPU: -")
        return " | ".join(parts)
