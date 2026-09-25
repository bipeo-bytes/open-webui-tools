# Open WebUI Tool Library

This workspace contains a small library of Python tools designed for Open WebUI custom tool integration. Each file follows the standard Open WebUI pattern: a `Tools` class with a nested `Valves` model and callable methods that the model can invoke.

## Included tools

The current workspace includes these tool files in `tools/`:

- `fortigate_readonly.py` — read-only FortiGate access over SSH. Includes safe command allowlisting, DHCP lease checks, VPN summary, interface and ARP status, switch inventory, NIC information, and log searching.
- `mac_vendor.py` — look up a vendor for a MAC address using a public lookup service.
- `network_dns.py` — hostname resolution and reverse DNS lookups.
- `network_ip.py` — IPv4 validation, CIDR checks, and summary helpers.
- `network_nmap.py` — scan a target with nmap via subprocess.
- `network_ports.py` — TCP port and HTTP status checks.
- `network_text.py` — log/text extraction helpers for IPs, domains, and summarized log lines.
- `network_traceroute.py` — traceroute wrapper using system tooling with a Python fallback.
- `self_notify.py` — send notifications through the SelfNotify API.
- `template_tool.py` — starter template with inline comments describing each section of the tool pattern.

There is no Guild Wars 2 API tool in the current `tools/` directory.

## Quick start

1. Copy the tools you want into the environment where you manage Open WebUI custom tools.
2. Import each file as a standalone Python custom tool.
3. Configure the required valves in Open WebUI.
4. Keep secrets such as tokens, passwords, and private keys in valves rather than inside the Python file.

## FortiGate tool

The FortiGate tool is intentionally restricted to a read-only allowlist. It supports commands such as:

- `get system status`
- `get system interface physical`
- `get system arp`
- `execute dhcp lease-list`
- `get vpn ipsec tunnel summary`
- `diagnose sys link-monitor status`
- `get switch-controller managed-switch`
- `show firewall policy`
- `get hardware nic`

### SSH and host key behavior

- `host`, `port`, `username`, and either `password` or `identity_file` are required.
- Password auth requires `sshpass` in the Open WebUI runtime.
- On Debian/Ubuntu-based runtimes, install the required clients with:

```bash
apt-get update && apt-get install -y openssh-client sshpass
```

- Host key verification is enabled by default. With the default `accept_new_host_key=True`, SSH uses `StrictHostKeyChecking=accept-new`: new keys are saved automatically and changed keys are rejected.
- Set `accept_new_host_key=False` to require a key already present in `known_hosts`.
- Setting `strict_host_key_checking=False` disables verification; avoid this outside disposable test environments.
- `known_hosts_file` can be set to a custom known_hosts path if needed.

### Log searching

`search_logs()` uses a fixed log query flow:

1. Optional `category_id` is mapped to `execute log filter category <id>`.
2. It runs `execute log filter view-lines 1000`.
3. It runs `execute log display`.
4. It applies your `search_string` as a Python regular expression locally.

The regex is never inserted into the FortiGate CLI. This keeps the tool safer and easier to reason about.

Supported category IDs are:

- `0` traffic
- `1` event
- `2` antivirus
- `3` web filter
- `4` IPS
- `5` application control
- `7` email filter
- `8` DLP
- `9` vulnerability scan
- `11` VoIP
- `12` WAF

Use patterns like `error|failed|denied` and optionally pass `case_sensitive=False` to make the search case-insensitive.

## SelfNotify tool

The SelfNotify tool sends JSON payloads to `https://self-notify.com/send` using a configured token. Keep the token in the Open WebUI valve, not directly in the Python file.

Supported options include:

- `title`
- `subtitle`
- `alert_level` (`active`, `passive`, `time-sensitive`, `critical`)
- `sound`
- `group`
- `custom_*` fields

## Template tool

`template_tool.py` is intentionally commented so it can be used as a starter kit for new custom tools. It demonstrates:

- imports
- `Tools` class definition
- `Valves` configuration
- constructor setup
- private helper methods
- public callable methods
- input validation and JSON-friendly return payloads

## Runtime requirements

- Python and Pydantic are required by the Open WebUI tool runtime.
- `network_nmap.py` requires the `nmap` executable installed and available on `PATH`.
- `network_traceroute.py` uses the system `tracert`, `traceroute`, or `tracepath` executable when available. Its raw-ICMP fallback may require elevated privileges and may be unavailable in containers.
- `fortigate_readonly.py` requires OpenSSH. Password authentication additionally requires `sshpass`; SSH key authentication can be used instead.
- `mac_vendor.py` and `self_notify.py` require network access to their configured HTTP endpoints. SelfNotify also requires a token configured in its valve.

## Recommended validation

From the workspace root, run:

```bash
python -m compileall .
python -m py_compile tools/*.py
```

This checks the project for syntax errors without requiring the external tools or a live Open WebUI runtime.

## Notes

- The tools use the Python standard library for HTTP, networking, and subprocess work wherever practical, with Pydantic for Open WebUI valve configuration.
- Tools are intentionally narrow in scope and should be treated as allowlisted wrappers rather than unrestricted shell access.
- Store credentials and tokens in Open WebUI valves; do not hardcode them into tool files.
- A tool is only as safe as the command list and validation it enforces — the FortiGate and other wrappers in this workspace are designed with that principle in mind.
