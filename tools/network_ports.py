"""
title: Network Port Checks
author: Jacob Wolnowski
version: 0.1.0
license: MIT
description: Check TCP reachability and HTTP status for network endpoints.
"""

import socket
import urllib.error
import urllib.request
from typing import Optional

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        default_timeout: float = Field(
            default=3.0,
            description="Default timeout used for TCP and HTTP probes.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def check_tcp_port(self, host: str, port: int, timeout: Optional[float] = None):
        """Check whether a TCP port is open on a host."""
        effective_timeout = self.valves.default_timeout if timeout is None else timeout
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(effective_timeout)
        try:
            sock.connect((host, port))
            return {"ok": True, "host": host, "port": port, "open": True}
        except OSError as exc:
            return {"ok": True, "host": host, "port": port, "open": False, "error": str(exc)}
        finally:
            sock.close()

    def check_http_status(self, url: str, timeout: Optional[float] = None):
        """Request a URL and return the HTTP status code and response summary."""
        effective_timeout = self.valves.default_timeout if timeout is None else timeout
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=effective_timeout) as response:
                status = response.getcode()
                content_type = response.headers.get("Content-Type", "")
                return {
                    "ok": True,
                    "url": url,
                    "status_code": status,
                    "content_type": content_type,
                    "open": status < 500,
                }
        except urllib.error.HTTPError as exc:
            return {
                "ok": True,
                "url": url,
                "status_code": exc.code,
                "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
                "open": exc.code < 500,
                "error": str(exc),
            }
        except Exception as exc:
            return {"ok": False, "url": url, "error": str(exc)}
