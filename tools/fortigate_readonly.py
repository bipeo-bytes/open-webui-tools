"""
title: FortiGate Read-Only SSH
author: Jacob Wolnowski
version: 0.1.0
license: MIT
description: Run an allowlisted set of read-only FortiGate CLI commands over SSH.
"""

import os
import re
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
        pager_space_count: int = Field(
            default=4096,
            description="Number of spaces sent to advance through FortiOS --More-- prompts.",
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
        "arp_table": "get system arp",
        "dhcp_leases": "execute dhcp lease-list",
        "ipsec_vpn_summary": "get vpn ipsec tunnel summary",
        "ipsec_vpn_status": "diagnose vpn tunnel list",
        "ssl_vpn_status": "diagnose vpn ssl monitor",
        "link_monitors": "diagnose sys link-monitor status",
        "routing_table": "get router info routing-table all",
        "list_switches": "get switch-controller managed-switch",
        "show_firewall_policies": "show firewall policy",
        "list_nics": "get hardware nic",

    }

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def _ssh_command(self, command: str, allocate_tty: bool = False):
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
        if allocate_tty:
            ssh_args.append("-tt")

        if not self.valves.strict_host_key_checking:
            ssh_args.extend(["-o", "UserKnownHostsFile=/dev/null"])
        elif self.valves.known_hosts_file.strip():
            ssh_args.extend(["-o", f"UserKnownHostsFile={self.valves.known_hosts_file.strip()}"])
        if self.valves.identity_file.strip():
            ssh_args.extend(["-i", self.valves.identity_file.strip()])

        ssh_args.append(f"{self.valves.username.strip()}@{self.valves.host.strip()}")
        if command:
            ssh_args.append(command)
        if self.valves.password:
            ssh_args.insert(0, sshpass_binary)
            ssh_args.insert(1, "-e")

        return ssh_args, None

    def _execute_commands(self, operation_name: str, commands):
        """Execute multiple FortiOS commands in one interactive SSH session."""
        ssh_args, error = self._ssh_command("", allocate_tty=True)
        if error:
            return {"ok": False, "operation": operation_name, "error": error}

        environment = os.environ.copy()
        if self.valves.password:
            environment["SSHPASS"] = self.valves.password

        pager_space_count = getattr(self.valves, "pager_space_count", 4096)
        input_text = "\n".join(commands) + "\n" + " " * max(0, pager_space_count) + "\nexit\n"
        try:
            completed = subprocess.run(
                ssh_args,
                capture_output=True,
                text=True,
                timeout=self.valves.command_timeout_seconds,
                check=False,
                env=environment,
                input=input_text,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "operation": operation_name,
                "error": f"FortiGate SSH command timed out after {self.valves.command_timeout_seconds} seconds.",
            }
        except OSError as exc:
            return {"ok": False, "operation": operation_name, "error": f"SSH execution failed: {exc}"}

        return {
            "ok": completed.returncode == 0,
            "operation": operation_name,
            "command": "; ".join(commands),
            "return_code": completed.returncode,
            "output": (completed.stdout or "").strip(),
            "error_output": (completed.stderr or "").strip(),
        }

    def _execute_command(self, operation_name: str, command: str):
        """Execute one validated FortiGate read-only command over SSH."""
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
                input=" " * max(0, self.valves.pager_space_count),
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

        return self._execute_command(operation_name, command)

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

    def get_arp_table(self):
        """Return the FortiGate ARP table."""
        return self.run_read_command("arp_table")

    def list_switches(self):
        """Return the list of managed switches."""
        return self.run_read_command("list_switches")

    def show_firewall_policies(self):
        """Return the configuration of firewall policies."""
        return self.run_read_command("show_firewall_policies")

    def list_nics(self):
        """Return the list of network interfaces."""
        return self.run_read_command("list_nics")

    def search_logs(
        self,
        search_string: str,
        max_logs: Optional[int] = 100,
        case_sensitive: bool = False,
        all_terms: bool = False,
        category_id: Optional[int] = None,
    ):
        """Search FortiOS logs and return only matching log lines.

        Provide whitespace-separated search terms. By default, a line is returned
        when it contains any term. Set all_terms to true only when every term must
        appear on the same line; this commonly returns no results for a long list
        of unrelated alert words. max_logs limits the number of returned lines.
        Optionally set category_id to filter the FortiOS log category first:
        0 traffic, 1 event, 2 antivirus, 3 web filter, 4 IPS, 5 application
        control, 7 email filter, 8 DLP, 9 vulnerability scan, 11 VoIP, or 12 WAF.
        """
        cleaned_search = (search_string or "").strip()
        if not cleaned_search:
            return {"ok": False, "error": "search_string is required."}

        if max_logs is not None and max_logs < 1:
            return {"ok": False, "error": "max_logs must be at least 1 or null for no limit."}

        valid_categories = {0, 1, 2, 3, 4, 5, 7, 8, 9, 11, 12}
        if category_id is not None and category_id not in valid_categories:
            return {
                "ok": False,
                "error": "Unsupported category_id.",
                "allowed_category_ids": sorted(valid_categories),
            }

        commands = []
        if category_id is not None:
            commands.append(f"execute log filter category {category_id}")
        commands.extend(["execute log filter view-lines 1000", "execute log display"])
        result = self._execute_commands(
            "search_logs",
            commands,
        )
        if not result.get("ok"):
            return result

        search_terms = cleaned_search.split()
        output = result.get("output", "")
        matching_lines = []
        for line in output.splitlines():
            comparison_line = line if case_sensitive else line.casefold()
            comparison_terms = search_terms if case_sensitive else [term.casefold() for term in search_terms]
            matches = all(term in comparison_line for term in comparison_terms) if all_terms else any(
                term in comparison_line for term in comparison_terms
            )
            if matches:
                matching_lines.append(line)

        total_matches = len(matching_lines)
        limited = max_logs is not None and total_matches > max_logs
        if max_logs is not None:
            matching_lines = matching_lines[:max_logs]

        return {
            "ok": True,
            "search_string": cleaned_search,
            "search_terms": search_terms,
            "case_sensitive": case_sensitive,
            "all_terms": all_terms,
            "category_id": category_id,
            "max_logs": max_logs,
            "total_matches": total_matches,
            "returned_matches": len(matching_lines),
            "truncated": limited,
            "logs": matching_lines,
        }

    def get_nic_status(self, nic: str):
        """Return status details for one NIC by name."""
        cleaned_nic = (nic or "").strip()
        if not cleaned_nic:
            return {"ok": False, "error": "nic is required."}
        if not re.fullmatch(r"[A-Za-z0-9._:-]+", cleaned_nic):
            return {"ok": False, "error": "nic contains unsupported characters."}

        command = f"get hardware nic {cleaned_nic}"
        return self._execute_command("nic_status", command)

    def get_switch_configuration(self, switch_id: str):
        """Return the configuration for one managed switch by ID or serial number."""
        cleaned_id = (switch_id or "").strip()
        if not cleaned_id:
            return {"ok": False, "error": "switch_id is required."}
        if not re.fullmatch(r"[A-Za-z0-9._:-]+", cleaned_id):
            return {
                "ok": False,
                "error": "switch_id contains unsupported characters.",
            }

        command = f"show switch-controller managed-switch {cleaned_id}"
        return self._execute_command("switch_configuration", command)

