"""
title: Network Text Utilities
author: Jacob Wolnowski
version: 0.1.0
license: MIT
description: Extract IP addresses, domains, and summarize log text for network troubleshooting.
"""

import ipaddress
import re
from typing import List

from pydantic import BaseModel


class Tools:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def extract_ip_addresses(self, text: str):
        """Extract IPv4 and IPv6 addresses from a blob of text."""
        pattern = r"(?:\d{1,3}\.){3}\d{1,3}|(?:[0-9a-fA-F:]+)"
        matches = re.findall(pattern, text)
        valid = []
        for item in matches:
            try:
                ip = ipaddress.ip_address(item)
                valid.append(str(ip))
            except ValueError:
                continue
        unique = sorted(set(valid))
        return {"ok": True, "count": len(unique), "addresses": unique}

    def extract_domains(self, text: str):
        """Extract hostnames/domains from text using a conservative regex."""
        pattern = r"(?i)\b(?:[a-z0-9-]+\.)+[a-z]{2,63}\b"
        matches = re.findall(pattern, text)
        unique = sorted(set(matches))
        return {"ok": True, "count": len(unique), "domains": unique}

    def summarize_log_lines(self, lines: List[str]):
        """Produce a simple summarization of log lines: counts, IPs, and domains."""
        cleaned = [line.strip() for line in lines if line and line.strip()]
        ip_summary = self.extract_ip_addresses("\n".join(cleaned))
        domain_summary = self.extract_domains("\n".join(cleaned))
        return {
            "ok": True,
            "line_count": len(cleaned),
            "non_empty_line_count": len(cleaned),
            "ip_count": ip_summary["count"],
            "ip_addresses": ip_summary["addresses"],
            "domain_count": domain_summary["count"],
            "domains": domain_summary["domains"],
        }
