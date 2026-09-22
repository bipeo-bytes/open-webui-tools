"""
title: MAC Address Vendor Lookup
author: Jacob Wolnowski
version: 0.1.0
license: MIT
description: Look up the manufacturer associated with a MAC address.
"""

import json
import re
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        lookup_url: str = Field(
            default="https://api.macvendors.com",
            description="MAC vendor lookup service URL.",
        )
        timeout_seconds: int = Field(
            default=10,
            description="HTTP request timeout in seconds.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def _normalize_mac(self, mac_address: str):
        """Validate a MAC address and return its compact uppercase form."""
        compact = re.sub(r"[^0-9A-Fa-f]", "", mac_address or "")
        if len(compact) != 12 or not re.fullmatch(r"[0-9A-Fa-f]{12}", compact):
            return None
        return compact.upper()

    def lookup_mac_vendor(self, mac_address: str):
        """Look up the manufacturer for a MAC address."""
        normalized_mac = self._normalize_mac(mac_address)
        if not normalized_mac:
            return {
                "ok": False,
                "error": "Invalid MAC address. Use a 12-digit address such as 00:11:22:33:44:55.",
            }

        url = f"{self.valves.lookup_url.rstrip('/')}/{normalized_mac}"
        request = Request(
            url,
            headers={
                "Accept": "application/json, text/plain",
                "User-Agent": "OpenWebUI-MAC-Vendor-Tool/0.1",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.valves.timeout_seconds) as response:
                body = response.read().decode("utf-8").strip()
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8").strip()
            except Exception:
                detail = str(exc.reason)
            return {
                "ok": False,
                "mac_address": normalized_mac,
                "status_code": exc.code,
                "error": detail or f"Vendor lookup returned HTTP {exc.code}.",
            }
        except URLError as exc:
            return {
                "ok": False,
                "mac_address": normalized_mac,
                "error": f"Vendor lookup connection failed: {exc.reason}",
            }
        except TimeoutError:
            return {
                "ok": False,
                "mac_address": normalized_mac,
                "error": f"Vendor lookup timed out after {self.valves.timeout_seconds} seconds.",
            }

        try:
            parsed: Any = json.loads(body)
        except json.JSONDecodeError:
            parsed = body

        if isinstance(parsed, dict):
            vendor = parsed.get("vendor") or parsed.get("company") or parsed.get("organization")
        else:
            vendor = parsed

        return {
            "ok": bool(vendor),
            "mac_address": normalized_mac,
            "vendor": vendor,
            "raw_response": parsed,
        }
