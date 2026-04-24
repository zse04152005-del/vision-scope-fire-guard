"""局域网摄像头设备扫描 — 扫描本地子网中开放 RTSP/HTTP 端口的设备。"""

import logging
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

# 常见 IP 摄像头端口
RTSP_PORTS = [554, 8554]
HTTP_PORTS = [80, 8080, 8000]
ALL_PORTS = RTSP_PORTS + HTTP_PORTS


def get_local_ip() -> Optional[str]:
    """获取本机局域网 IP 地址。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def get_subnet_prefix(ip: str) -> str:
    """从 IP 地址提取子网前缀（假设 /24 子网）。"""
    parts = ip.split(".")
    return ".".join(parts[:3])


def _check_port(ip: str, port: int, timeout: float = 0.5) -> bool:
    """检测指定 IP:port 是否开放。"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _scan_host(ip: str, ports: list[int], timeout: float = 0.5) -> Optional[dict]:
    """扫描单台主机上的端口。"""
    open_ports = []
    for port in ports:
        if _check_port(ip, port, timeout):
            open_ports.append(port)
    if open_ports:
        return {"ip": ip, "ports": open_ports}
    return None


def scan_subnet(
    subnet_prefix: str = "",
    ports: list[int] = None,
    timeout: float = 0.5,
    max_workers: int = 50,
    progress_callback=None,
) -> list[dict]:
    """扫描整个子网，返回有开放摄像头端口的设备列表。

    Parameters
    ----------
    subnet_prefix : 子网前缀，如 "192.168.1"。为空则自动获取。
    ports : 要扫描的端口列表。默认 [554, 8554, 80, 8080, 8000]。
    timeout : 每个端口连接超时（秒）。
    max_workers : 并发线程数。
    progress_callback : 进度回调 fn(scanned, total)。

    Returns
    -------
    [{"ip": "192.168.1.xx", "ports": [554], "hostname": "..."}, ...]
    """
    if not subnet_prefix:
        local_ip = get_local_ip()
        if not local_ip:
            logger.warning("无法获取本机 IP，跳过网络扫描")
            return []
        subnet_prefix = get_subnet_prefix(local_ip)

    if ports is None:
        ports = ALL_PORTS

    targets = [f"{subnet_prefix}.{i}" for i in range(1, 255)]
    # 排除本机
    local_ip = get_local_ip()
    if local_ip in targets:
        targets.remove(local_ip)

    found = []
    total = len(targets)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_scan_host, ip, ports, timeout): ip for ip in targets
        }
        for i, future in enumerate(as_completed(futures)):
            if progress_callback:
                progress_callback(i + 1, total)
            result = future.result()
            if result:
                # 尝试反向 DNS 查找主机名
                try:
                    hostname = socket.gethostbyaddr(result["ip"])[0]
                except Exception:
                    hostname = ""
                result["hostname"] = hostname

                # 判断可能的协议
                protocols = []
                for p in result["ports"]:
                    if p in RTSP_PORTS:
                        protocols.append(f"rtsp://{result['ip']}:{p}")
                    else:
                        protocols.append(f"http://{result['ip']}:{p}")
                result["urls"] = protocols
                found.append(result)

    found.sort(key=lambda x: x["ip"])
    logger.info("子网扫描完成: %s.0/24，发现 %d 个设备", subnet_prefix, len(found))
    return found
