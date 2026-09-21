"""
title: Metasploit Nmap Scan Tool
author: Jacob Wolnowski
version: 0.1.0
license: MIT
description: Run a Metasploit db_nmap session as the msfuser account against a target IP passed by the agent.
"""

# ---------------------------------------------------------------------------
# 1) Imports
# ---------------------------------------------------------------------------
# We only need the standard library and pydantic for config fields.
import shlex
import subprocess
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 2) Tool class definition
# ---------------------------------------------------------------------------
class Tools:
    # -------------------------------------------------------------------
    # 2a) Valves
    # -------------------------------------------------------------------
    # These settings can be adjusted in Open WebUI for the user or environment.
    class Valves(BaseModel):
        msf_user: str = Field(
            default="msfuser",
            description="Linux user account used to run the Metasploit command.",
        )
        timeout_seconds: int = Field(
            default=180,
            description="Timeout for the msfconsole command.",
        )

    # -------------------------------------------------------------------
    # 2b) Constructor
    # -------------------------------------------------------------------
    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    # -------------------------------------------------------------------
    # 3) Internal helper methods
    # -------------------------------------------------------------------
    def _build_command(self, target_ip: str) -> str:
        """Build the shell command to initialize the Metasploit DB and then scan the target."""
        escaped_ip = shlex.quote(target_ip)
        command = (
            f"su - {self.valves.msf_user} -c "
            f'"msfdb init >/dev/null 2>&1 || true; msfdb start && msfconsole -q -n -x \'db_connect; db_nmap -sV -O {escaped_ip}; exit\'"'
        )
        return command

    # -------------------------------------------------------------------
    # 4) Public tool methods
    # -------------------------------------------------------------------
    def run_msf_nmap_scan(self, target_ip: str, timeout_seconds: Optional[int] = None):
        """
        Run a Metasploit db_nmap scan against a target IP.

        Example:
            run_msf_nmap_scan("192.168.1.50")

        This initializes the local Metasploit database and then connects before running:
            su - msfuser -c "msfdb init >/dev/null 2>&1 || true; msfdb start && msfconsole -q -n -x 'db_connect; db_nmap -sV -O 192.168.1.50; exit'"

        :param target_ip: The host IP to scan.
        :param timeout_seconds: Optional override for the command timeout.
        :return: A dict with the command, exit code, stdout, stderr, and errors.
        """
        if not target_ip or not target_ip.strip():
            return {"ok": False, "error": "target_ip is required."}

        cleaned_ip = target_ip.strip()
        effective_timeout = self.valves.timeout_seconds if timeout_seconds is None else timeout_seconds

        command = self._build_command(cleaned_ip)

        try:
            completed = subprocess.run(
                ["bash", "-lc", command],
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": f"Metasploit scan timed out after {effective_timeout} seconds.",
                "command": command,
                "target_ip": cleaned_ip,
            }

        output = (completed.stdout or "") + (completed.stderr or "")
        output_text = output.strip()
        lower_output = output_text.lower()

        if "no database driver installed" in lower_output or "database not connected" in lower_output:
            return {
                "ok": False,
                "target_ip": cleaned_ip,
                "command": command,
                "return_code": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
                "output": output_text,
                "error": (
                    "Metasploit is installed, but its database driver / PostgreSQL support is not configured. "
                    "Run the Metasploit DB setup on the host: 'msfdb reinit' or install the PostgreSQL driver and "
                    "ensure the database service is running before using db_nmap."
                ),
            }

        return {
            "ok": completed.returncode == 0,
            "target_ip": cleaned_ip,
            "command": command,
            "return_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "output": output_text,
        }
