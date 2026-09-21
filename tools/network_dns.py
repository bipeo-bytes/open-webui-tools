"""
title: Network DNS Utilities
author: Jacob Wolnowski
version: 0.1.0
license: MIT
description: Resolve hostnames, perform reverse lookups, and summarize DNS results.
"""

import socket
from typing import List, Optional

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        default_family: str = Field(
            default="inet",
            description="Default address family for hostname resolution: inet or inet6.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def resolve_hostname(self, hostname: str, family: Optional[str] = None):
        """Resolve a hostname to IPv4 or IPv6 addresses."""
        family_name = (self.valves.default_family if family is None else family).lower()
        try:
            if family_name == "inet":
                infos = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
            elif family_name in {"inet6", "ipv6"}:
                infos = socket.getaddrinfo(hostname, None, socket.AF_INET6, socket.SOCK_STREAM)
            else:
                return {"ok": False, "error": "Unsupported family. Use 'inet' or 'inet6'."}
        except socket.gaierror as exc:
            return {"ok": False, "error": f"DNS resolution failed: {exc}"}

        addresses = sorted({info[4][0] for info in infos})
        return {"ok": True, "hostname": hostname, "family": family_name, "addresses": addresses}

    def reverse_lookup(self, ip_address: str):
        """Perform a reverse DNS lookup for a single IP address."""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip_address)
            return {"ok": True, "ip": ip_address, "hostname": hostname}
        except socket.herror as exc:
            return {"ok": False, "error": f"Reverse lookup failed for {ip_address}: {exc}"}

    def dns_record_summary(self, hostnames: List[str]):
        """Resolve a list of hostnames and return a compact summary."""
        results = []
        for hostname in hostnames:
            results.append(self.resolve_hostname(hostname))
        return {"ok": True, "results": results}
