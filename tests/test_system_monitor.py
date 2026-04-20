import unittest

from core.system_monitor import SystemMonitor, SystemStats


class TestSystemMonitor(unittest.TestCase):
    def test_sample_returns_stats(self):
        mon = SystemMonitor()
        stats = mon.sample()
        self.assertIsInstance(stats, SystemStats)
        self.assertGreaterEqual(stats.cpu_percent, 0.0)
        self.assertGreaterEqual(stats.mem_percent, 0.0)

    def test_format_stats_includes_labels(self):
        mon = SystemMonitor()
        text = mon.format_stats(SystemStats(cpu_percent=12.0, mem_percent=34.0))
        self.assertIn("CPU", text)
        self.assertIn("内存", text)
        self.assertIn("GPU", text)


if __name__ == "__main__":
    unittest.main()
