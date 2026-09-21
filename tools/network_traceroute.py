"""
title: Network Traceroute
author: Jacob Wolnowski
version: 0.1.0
license: MIT
description: Trace a host path dynamically by invoking the operating system traceroute tool.
"""

import select
import shutil
import socket
import struct
import subprocess
import sys
import time
from typing import Optional

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        max_hops: int = Field(
            default=30,
            description="Maximum number of hops to probe.",
        )
        timeout_seconds: float = Field(
            default=2.0,
            description="Per-hop timeout in seconds.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def _run_system_traceroute(self, host: str, max_hops: int, timeout: float):
        candidates = ["tracert"] if sys.platform.startswith("win") else ["traceroute", "tracepath"]

        for candidate in candidates:
            binary = shutil.which(candidate)
            if not binary:
                continue

            try:
                if candidate == "tracert":
                    cmd = [binary, "-d", "-w", str(int(timeout * 1000)), host]
                else:
                    cmd = [binary, "-m", str(max_hops), "-w", str(timeout), host]

                completed = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=max(5, int(timeout * 5) + 1),
                    check=False,
                )
                output = completed.stdout.strip() or completed.stderr.strip()
                return {
                    "ok": True,
                    "host": host,
                    "method": candidate,
                    "output": output,
                    "return_code": completed.returncode,
                }
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                continue

        return {
            "ok": False,
            "error": "No supported traceroute utility is installed on this system.",
        }

    def _python_traceroute(self, host: str, max_hops: int, timeout: float):
        """Best-effort TTL-based traceroute using a raw ICMP listener."""
        try:
            dest_ip = socket.gethostbyname(host)
        except socket.gaierror as exc:
            return {"ok": False, "error": f"DNS lookup failed for {host}: {exc}"}

        try:
            recv_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            recv_socket.settimeout(timeout)
        except OSError as exc:
            return {
                "ok": False,
                "error": (
                    "No supported traceroute utility is installed, and raw ICMP sockets are unavailable. "
                    "Install traceroute (Linux: apt-get install traceroute / yum install traceroute; "
                    "macOS: brew install traceroute; Windows: use tracert, which is built in)."
                ),
                "details": str(exc),
            }

        results = []
        for ttl in range(1, max_hops + 1):
            tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            tx_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
            tx_socket.settimeout(timeout)

            start = time.time()
            last_addr = None
            reached_target = False

            try:
                tx_socket.sendto(b"", (dest_ip, 33434))
                while time.time() - start < timeout:
                    readable, _, _ = select.select([recv_socket], [], [], 0.2)
                    if not readable:
                        continue

                    packet, addr = recv_socket.recvfrom(512)
                    if len(packet) < 28:
                        continue

                    icmp_type, icmp_code, _, _, _ = struct.unpack("!BBHHH", packet[20:28])
                    last_addr = addr[0]

                    if icmp_type in (11, 3):
                        if icmp_type == 3:
                            reached_target = True
                        break
                    if icmp_type == 0:
                        reached_target = True
                        break
            except socket.timeout:
                last_addr = None
            except OSError:
                last_addr = None
            finally:
                tx_socket.close()

            results.append(
                {
                    "ttl": ttl,
                    "address": last_addr,
                    "reached_target": reached_target,
                    "rtt_ms": round((time.time() - start) * 1000, 2),
                }
            )

            if reached_target:
                break

        return {"ok": True, "host": host, "resolved_ip": dest_ip, "hops": results}

    def traceroute(
        self,
        host: str,
        max_hops: Optional[int] = None,
        timeout: Optional[float] = None,
    ):
        """
        Trace the network path to a hostname or IP address.

        :param host: Hostname or IP address to trace.
        :param max_hops: Optional override for the max hop count.
        :param timeout: Optional override for the timeout in seconds.
        :return: A dict with traceroute output or an error.
        """
        if not host or not host.strip():
            return {"ok": False, "error": "A hostname or IP address is required."}

        effective_max_hops = self.valves.max_hops if max_hops is None else max_hops
        effective_timeout = self.valves.timeout_seconds if timeout is None else timeout

        if effective_max_hops < 1:
            return {"ok": False, "error": "max_hops must be at least 1."}

        if effective_timeout <= 0:
            return {"ok": False, "error": "timeout must be greater than 0."}

        host = host.strip()

        try:
            socket.getaddrinfo(host, None)
        except socket.gaierror as exc:
            return {"ok": False, "error": f"DNS lookup failed for {host}: {exc}"}

        system_result = self._run_system_traceroute(
            host=host,
            max_hops=effective_max_hops,
            timeout=effective_timeout,
        )
        if system_result.get("ok"):
            return system_result

        python_result = self._python_traceroute(
            host=host,
            max_hops=effective_max_hops,
            timeout=effective_timeout,
        )
        if python_result.get("ok"):
            return python_result

        return {
            "ok": False,
            "error": (
                "No supported traceroute utility is installed on this system, and the Python fallback could not run. "
                "Install traceroute or run this tool on a host with traceroute support."
            ),
            "details": python_result.get("error"),
        }
