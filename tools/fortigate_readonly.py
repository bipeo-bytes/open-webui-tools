"""
title: FortiGate Read-Only SSH
author: Jacob Wolnowski
version: 0.1.0
license: MIT
description: Run an allowlisted set of read-only FortiGate CLI commands over SSH.
"""

import os
import shutil
import subprocess
from typing import Dict, Optional

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        host: str = Field(
            default="",
            description="FortiGate management IP address or hostname.",
        )
        port: int = Field(
            default=22,
            description="SSH port on the FortiGate.",
        )
        username: str = Field(
            default="",
            description="Read-only FortiGate SSH username.",
        )
        identity_file: str = Field(
            default="",
            description="Optional SSH private key path available to the Open WebUI host.",
        )
        password: str = Field(
            default="",
            description="Optional SSH password. Requires sshpass; SSH keys are preferred.",
        )
        ssh_binary: str = Field(
            default="ssh",
            description="OpenSSH client executable name or path, normally 'ssh'.",
        )
        connect_timeout_seconds: int = Field(
            default=10,
            description="SSH connection timeout in seconds.",
        )
        command_timeout_seconds: int = Field(
            default=30,
            description="Maximum time allowed for a FortiGate command.",
        )
        strict_host_key_checking: bool = Field(
            default=True,
            description="Verify the FortiGate host key using known_hosts.",
        )
        accept_new_host_key: bool = Field(
            default=True,
            description="Automatically save a new FortiGate host key; changed keys are still rejected.",
        )
        known_hosts_file: str = Field(
            default="",
            description="Optional path to the SSH known_hosts file used by the Open WebUI runtime.",
        )

    READ_COMMANDS: Dict[str, str] = {
        "system_status": "get system status",
        "interface_status": "get system interface physical",
        "interface_config": "show system interface",
        "dhcp_leases": "diagnose ip dhcp lease-list",
        "ipsec_vpn_summary": "get vpn ipsec tunnel summary",
        "ipsec_vpn_status": "diagnose vpn tunnel list",
        "ssl_vpn_status": "diagnose vpn ssl monitor",
        "link_monitors": "diagnose sys link-monitor status",
        "routing_table": "get router info routing-table all",
        "firewall_policy_summary": "diagnose firewall iprope show 100",
    }

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def _ssh_command(self, command: str):
        """Build a non-interactive SSH command from configured connection settings."""
        if not self.valves.host.strip():
            return None, "FortiGate host is not configured in the tool valves."
        if not self.valves.username.strip():
            return None, "FortiGate username is not configured in the tool valves."

        ssh_binary = shutil.which(self.valves.ssh_binary)
        if not ssh_binary and self.valves.ssh_binary.strip() == "ssh":
            for candidate in ("/usr/bin/ssh", "/bin/ssh", "/usr/local/bin/ssh"):
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    ssh_binary = candidate
                    break
        if not ssh_binary:
            return None, (
                "OpenSSH client not found in the Open WebUI runtime. "
                "Install it with 'apt-get update && apt-get install -y openssh-client' "
                "or set the ssh_binary valve to the full path of an installed ssh client."
            )

        sshpass_binary = shutil.which("sshpass")
        if not sshpass_binary and self.valves.password:
            for candidate in ("/usr/bin/sshpass", "/bin/sshpass", "/usr/local/bin/sshpass"):
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    sshpass_binary = candidate
                    break
        if self.valves.password and not sshpass_binary:
            return None, (
                "A password is configured, but sshpass is not installed in the Open WebUI runtime. "
                "Install it with 'apt-get update && apt-get install -y sshpass', "
                "or configure SSH key authentication instead."
            )

        if not self.valves.strict_host_key_checking:
            host_key_policy = "no"
        elif self.valves.accept_new_host_key:
            host_key_policy = "accept-new"
        else:
            host_key_policy = "yes"

        ssh_args = [
            ssh_binary,
            "-p",
            str(self.valves.port),
            "-o",
            f"ConnectTimeout={self.valves.connect_timeout_seconds}",
            "-o",
            "BatchMode=yes" if not self.valves.password else "BatchMode=no",
            "-o",
            f"StrictHostKeyChecking={host_key_policy}",
        ]

        if not self.valves.strict_host_key_checking:
            ssh_args.extend(["-o", "UserKnownHostsFile=/dev/null"])
        elif self.valves.known_hosts_file.strip():
            ssh_args.extend(["-o", f"UserKnownHostsFile={self.valves.known_hosts_file.strip()}"])
        if self.valves.identity_file.strip():
            ssh_args.extend(["-i", self.valves.identity_file.strip()])

        ssh_args.extend([f"{self.valves.username.strip()}@{self.valves.host.strip()}", command])
        if self.valves.password:
            ssh_args.insert(0, sshpass_binary)
            ssh_args.insert(1, "-e")

        return ssh_args, None

    def run_read_command(self, operation: str):
        """Run one allowlisted read-only FortiGate operation over SSH."""
        operation_name = (operation or "").strip().lower()
        command = self.READ_COMMANDS.get(operation_name)
        if not command:
            return {
                "ok": False,
                "error": "Unsupported operation.",
                "available_operations": sorted(self.READ_COMMANDS),
            }

        ssh_args, error = self._ssh_command(command)
        if error:
            return {"ok": False, "operation": operation_name, "error": error}

        environment = os.environ.copy()
        if self.valves.password:
            environment["SSHPASS"] = self.valves.password

        try:
            completed = subprocess.run(
                ssh_args,
                capture_output=True,
                text=True,
                timeout=self.valves.command_timeout_seconds,
                check=False,
                env=environment,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "operation": operation_name,
                "error": f"FortiGate SSH command timed out after {self.valves.command_timeout_seconds} seconds.",
            }
        except OSError as exc:
            return {"ok": False, "operation": operation_name, "error": f"SSH execution failed: {exc}"}

        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        return {
            "ok": completed.returncode == 0,
            "operation": operation_name,
            "command": command,
            "return_code": completed.returncode,
            "output": stdout,
            "error_output": stderr,
        }

    def list_read_operations(self):
        """List the read-only FortiGate operations available to the agent."""
        return {
            "ok": True,
            "operations": [
                {"name": name, "command": command}
                for name, command in sorted(self.READ_COMMANDS.items())
            ],
        }

    def get_dhcp_leases(self):
        """Return current DHCP leases from the FortiGate."""
        return self.run_read_command("dhcp_leases")

    def get_vpn_status(self):
        """Return IPsec VPN tunnel status from the FortiGate."""
        return self.run_read_command("ipsec_vpn_summary")

    def get_link_monitor_status(self):
        """Return FortiGate link-monitor status."""
        return self.run_read_command("link_monitors")

    def get_interface_status(self):
        """Return physical interface status from the FortiGate."""
        return self.run_read_command("interface_status")
