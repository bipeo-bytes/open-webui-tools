"""
title: Guild Wars 2 API
author: Jacob Wolnowski
version: 0.1.0
license: MIT
description: Read Guild Wars 2 account and public game data through the official API.
"""

import json
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        api_key: str = Field(
            default="",
            description="Optional Guild Wars 2 API key. Required for account endpoints.",
        )
        base_url: str = Field(
            default="https://api.guildwars2.com/v2",
            description="Guild Wars 2 API base URL.",
        )
        timeout_seconds: int = Field(
            default=20,
            description="HTTP request timeout in seconds.",
        )

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def _request(
        self,
        endpoint: str,
        requires_key: bool = False,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Request one fixed API endpoint and return a structured result."""
        configured_key = self.valves.api_key.strip()
        effective_key = configured_key if api_key is None else api_key.strip()
        if requires_key and not effective_key:
            return {
                "ok": False,
                "error": "This endpoint requires a Guild Wars 2 API key configured in the tool valves.",
            }

        url = f"{self.valves.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        if effective_key:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}access_token={quote(effective_key, safe='')}"

        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "OpenWebUI-GW2-Tool/0.1"},
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.valves.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
                data = json.loads(raw_body)
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8")
            except Exception:
                detail = str(exc.reason)
            return {
                "ok": False,
                "status_code": exc.code,
                "endpoint": endpoint,
                "error": detail or f"Guild Wars 2 API returned HTTP {exc.code}.",
            }
        except URLError as exc:
            return {"ok": False, "endpoint": endpoint, "error": f"GW2 API connection failed: {exc.reason}"}
        except TimeoutError:
            return {
                "ok": False,
                "endpoint": endpoint,
                "error": f"GW2 API request timed out after {self.valves.timeout_seconds} seconds.",
            }
        except json.JSONDecodeError:
            return {"ok": False, "endpoint": endpoint, "error": "GW2 API returned invalid JSON."}

        return {"ok": True, "endpoint": endpoint, "data": data}

    def get_account(self, api_key: Optional[str] = None):
        """Get the authenticated Guild Wars 2 account summary."""
        return self._request("account", requires_key=True, api_key=api_key)

    def get_account_characters(self, api_key: Optional[str] = None):
        """List character names on the authenticated account."""
        return self._request("account/characters", requires_key=True, api_key=api_key)

    def get_account_bank(self, api_key: Optional[str] = None):
        """Get bank slots and item contents for the authenticated account."""
        return self._request("account/bank", requires_key=True, api_key=api_key)

    def get_character(self, character_name: str, api_key: Optional[str] = None):
        """Get details for one authenticated account character."""
        if not character_name or not character_name.strip():
            return {"ok": False, "error": "character_name is required."}
        encoded_name = quote(character_name.strip(), safe="")
        return self._request(f"characters/{encoded_name}", requires_key=True, api_key=api_key)

    def get_item(self, item_id: int):
        """Get public item data by item ID."""
        if item_id <= 0:
            return {"ok": False, "error": "item_id must be a positive integer."}
        return self._request(f"items/{item_id}")

    def get_items(self, item_ids: str):
        """Get public item data for comma-separated item IDs."""
        if not item_ids or not item_ids.strip():
            return {"ok": False, "error": "item_ids is required, for example '19699,19700'."}
        ids = [value.strip() for value in item_ids.split(",") if value.strip()]
        if not ids or any(not value.isdigit() or int(value) <= 0 for value in ids):
            return {"ok": False, "error": "item_ids must contain only positive integer IDs."}
        return self._request(f"items?ids={quote(','.join(ids), safe=',')}")

    def get_map(self, map_id: int):
        """Get public map data by map ID."""
        if map_id <= 0:
            return {"ok": False, "error": "map_id must be a positive integer."}
        return self._request(f"maps/{map_id}")

    def get_world(self, world_id: int):
        """Get public world data by world ID."""
        if world_id <= 0:
            return {"ok": False, "error": "world_id must be a positive integer."}
        return self._request(f"worlds/{world_id}")

    def get_guild(self, guild_id: str, api_key: Optional[str] = None):
        """Get guild details by GUID; a key may be required by the API."""
        if not guild_id or not guild_id.strip():
            return {"ok": False, "error": "guild_id is required."}
        encoded_id = quote(guild_id.strip(), safe="")
        return self._request(f"guild/{encoded_id}", api_key=api_key)

    def get_guild_members(self, guild_id: str, api_key: Optional[str] = None):
        """Get members for a guild when the configured API key has permission."""
        if not guild_id or not guild_id.strip():
            return {"ok": False, "error": "guild_id is required."}
        encoded_id = quote(guild_id.strip(), safe="")
        return self._request(f"guild/{encoded_id}/members", requires_key=True, api_key=api_key)
