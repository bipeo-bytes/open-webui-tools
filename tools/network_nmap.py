"""
title: Network Nmap Scanner
author: Jacob Wolnowski
version: 0.1.0
license: MIT
description: Run nmap scans from Open WebUI with safe subprocess invocation and structured results.
"""

import shlex
import shutil
import subprocess
from typing import Optional

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        nmap_binary: str = Field(
            default="nmap",
            description="Executable name or path to the nmap binary.",
        )
        default_args: str = Field(
            default="-T4 --max-retries 1",
            description="Default arguments appended to every scan.",
        )
        timeout_seconds: int = Field(
            default=120,
            description="Scan timeout in seconds.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def _ensure_available(self):
        binary = shutil.which(self.valves.nmap_binary)
        if binary:
            return binary
        return None

    def nmap_scan(
        self,
        target: str,
        ports: Optional[str] = None,
        args: Optional[str] = None,
        aggressive: bool = False,
    ):
        """
        Run an nmap scan against a host or CIDR target.

        :param target: Host, IP, or CIDR range to scan.
        :param ports: Optional port specification, e.g. "22-80,443".
        :param args: Extra nmap arguments as a string, parsed safely with shlex.
        :param aggressive: Add -A for service/version detection and OS fingerprinting.
        :return: Dict with scan output and exit code.
        """
        if not target or not target.strip():
            return {"ok": False, "error": "A target host or CIDR is required."}

        binary = self._ensure_available()
        if not binary:
            return {
                "ok": False,
                "error": (
                    "nmap is not installed or not available in PATH. "
                    "Install it first (Linux: apt-get install nmap / yum install nmap; "
                    "macOS: brew install nmap; Windows: install Nmap and ensure nmap.exe is on PATH)."
                ),
            }

        cmd = [binary]

        default_args = self.valves.default_args.strip()
        if default_args:
            cmd.extend(shlex.split(default_args))

        if aggressive:
            cmd.append("-A")

        if ports:
            cmd.extend(["-p", ports])

        if args:
            cmd.extend(shlex.split(args))

        cmd.append(target.strip())

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.valves.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": f"nmap timed out after {self.valves.timeout_seconds} seconds.",
                "command": " ".join(cmd),
            }

        output = (completed.stdout or "") + (completed.stderr or "")
        result = {
            "ok": completed.returncode in (0, 1),
            "target": target.strip(),
            "command": " ".join(cmd),
            "return_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "output": output.strip(),
        }
        return result
