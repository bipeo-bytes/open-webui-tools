# Open WebUI Tool Library

This workspace contains a small set of reusable Python tools for Open WebUI workflows, especially networking and troubleshooting tasks.

## Included tools

- `tools/network_ip.py` – IP and CIDR helpers
- `tools/network_dns.py` – DNS resolution helpers
- `tools/network_ports.py` – TCP port and HTTP checks
- `tools/network_text.py` – text extraction and log parsing
- `tools/guild_wars_2_api.py` – Guild Wars 2 account and public game data
- `tools/fortigate_readonly.py` – allowlisted read-only FortiGate SSH checks
- `tools/mac_vendor.py` – MAC address manufacturer lookup

## Quick start

1. Copy the files from this workspace into the environment where you manage Open WebUI custom tools.
2. Import them as standalone Python tools or paste the functions into Open WebUI's tool editor.
3. Keep each file focused on one concept so the model can choose the right tool reliably.

## Recommended pattern

Use one file per capability and keep the function names specific and action-oriented. For example:

- `describe_ipv4_network`
- `resolve_hostname`
- `check_tcp_port`
- `extract_ip_addresses`

## Validate locally

```bash
python -m compileall .
```

## Notes

The tool implementations intentionally use only the Python standard library so they can run in a minimal Open WebUI environment without extra packages.

The Guild Wars 2 tool uses the official `api.guildwars2.com` API. Configure an API key in its Open WebUI valve to use account and character endpoints; public item, map, world, and guild details do not require a key.

The FortiGate tool only runs its fixed read-only command catalog. Configure the FortiGate host, read-only username, and password in its valves. The tool automatically accepts a new server host key and rejects changed keys by default. Password authentication requires `sshpass`; on Debian/Ubuntu containers install both clients with `apt-get update && apt-get install -y openssh-client sshpass`. SSH key authentication remains an optional alternative.

The MAC vendor tool queries `api.macvendors.com` by default and can be pointed at another compatible lookup service through its `lookup_url` valve.
