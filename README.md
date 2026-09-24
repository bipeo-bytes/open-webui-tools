# Open WebUI Tool Library

This workspace contains a small set of reusable Python tools for Open WebUI workflows, especially networking and troubleshooting tasks.

## Included tools


## Quick start

1. Copy the files from this workspace into the environment where you manage Open WebUI custom tools.
2. Import them as standalone Python tools or paste the functions into Open WebUI's tool editor.
3. Keep each file focused on one concept so the model can choose the right tool reliably.

## Recommended pattern

Use one file per capability and keep the function names specific and action-oriented. For example:


## Validate locally

```bash
python -m compileall .
```

## Notes

The tool implementations intentionally use only the Python standard library so they can run in a minimal Open WebUI environment without extra packages.

The Guild Wars 2 tool uses the official `api.guildwars2.com` API. Configure an API key in its Open WebUI valve to use account and character endpoints; public item, map, world, and guild details do not require a key.

The FortiGate tool only runs its fixed read-only command catalog. Configure the FortiGate host, read-only username, and password in its valves. The tool automatically accepts a new server host key and rejects changed keys by default. Password authentication requires `sshpass`; on Debian/Ubuntu containers install both clients with `apt-get update && apt-get install -y openssh-client sshpass`. SSH key authentication remains an optional alternative.

The FortiGate tool's `search_logs` method runs the fixed `execute log filter view-lines 1000` and `execute log display` commands, then filters the returned lines locally using `search_string` as a regular expression. Pass `max_logs` and optionally `case_sensitive`; the search pattern is never inserted into a FortiGate command.

The SelfNotify tool sends JSON requests to `https://self-notify.com/send`. Configure the personal token in its `token` valve; do not place the token in the Python file. It supports optional titles, subtitles, alert levels, sounds, groups, and `custom_*` fields.
