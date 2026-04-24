"""Tests for core.network_scanner."""

import pytest

from core.network_scanner import get_local_ip, get_subnet_prefix, _check_port


class TestNetworkScanner:
    def test_get_local_ip(self):
        ip = get_local_ip()
        # Should return a valid IP or None
        if ip:
            parts = ip.split(".")
            assert len(parts) == 4

    def test_get_subnet_prefix(self):
        assert get_subnet_prefix("192.168.1.100") == "192.168.1"
        assert get_subnet_prefix("10.0.0.5") == "10.0.0"

    def test_check_port_closed(self):
        # Port on a non-routable IP should be closed
        result = _check_port("192.0.2.1", 99999, timeout=0.2)
        assert result is False

    def test_check_port_invalid_host(self):
        result = _check_port("999.999.999.999", 80, timeout=0.2)
        assert result is False
