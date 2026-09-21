"""
title: Network IP Utilities
author: Jacob Wolnowski
version: 0.1.0
license: MIT
description: Validate IPv4 values, inspect CIDR ranges, and test whether an IP is inside a subnet.
"""

import ipaddress
from typing import List, Optional

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        allow_ipv6: bool = Field(
            default=False,
            description="Allow IPv6 values in validation output when present.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def validate_ipv4(self, ip_value: str):
        """Validate and describe a single IPv4 address."""
        try:
            ip_obj = ipaddress.ip_address(ip_value)
            if ip_obj.version != 4:
                return {"ok": False, "error": "Value is not IPv4."}
            return {
                "ok": True,
                "ip": str(ip_obj),
                "is_private": ip_obj.is_private,
                "is_global": ip_obj.is_global,
                "is_loopback": ip_obj.is_loopback,
                "is_multicast": ip_obj.is_multicast,
                "is_reserved": ip_obj.is_reserved,
            }
        except ValueError:
            return {"ok": False, "error": f"Invalid IPv4 address: {ip_value}"}

    def describe_cidr(self, cidr: str):
        """Describe the network, broadcast, first usable, and last usable hosts."""
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            return {"ok": False, "error": f"Invalid CIDR: {cidr}"}

        if network.version != 4:
            return {"ok": False, "error": "Only IPv4 CIDR blocks are supported."}

        addresses = list(network.hosts())
        first_host = str(addresses[0]) if addresses else None
        last_host = str(addresses[-1]) if addresses else None

        return {
            "ok": True,
            "cidr": str(network),
            "network_address": str(network.network_address),
            "broadcast_address": str(network.broadcast_address),
            "subnet_mask": str(network.netmask),
            "prefix_length": network.prefixlen,
            "total_addresses": network.num_addresses,
            "usable_hosts": len(addresses),
            "first_usable_host": first_host,
            "last_usable_host": last_host,
            "is_private": network.is_private,
        }

    def ip_in_cidr(self, ip_value: str, cidr: str):
        """Check whether an IPv4 falls inside a CIDR block."""
        try:
            ip_obj = ipaddress.ip_address(ip_value)
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        if ip_obj.version != network.version:
            return {"ok": False, "error": "IP version does not match the CIDR version."}

        return {
            "ok": True,
            "ip": str(ip_obj),
            "cidr": str(network),
            "in_network": ip_obj in network,
        }

    def cidr_summary(self, ip_list: List[str]):
        """Generate a simple summary for a list of IPv4 addresses."""
        results = []
        for ip in ip_list:
            results.append(self.validate_ipv4(ip))
        return {"ok": True, "items": results}
