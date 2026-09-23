"""
title: SelfNotify Messages
author: Jacob Wolnowski
version: 0.1.0
license: MIT
description: Send personal push notifications through the SelfNotify API.
"""

import json
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        token: str = Field(
            default="",
            description="SelfNotify personal token. Keep this secret and configure it in Open WebUI valves.",
        )
        endpoint: str = Field(
            default="https://self-notify.com/send",
            description="SelfNotify notification endpoint.",
        )
        timeout_seconds: int = Field(
            default=10,
            description="HTTP request timeout in seconds.",
        )

    VALID_ALERT_LEVELS = {"active", "passive", "time-sensitive", "critical"}
    ALERT_LEVEL_ALIASES = {"info": "active"}
    VALID_SOUNDS = {f"snd{number:02d}" for number in range(1, 17)}

    def __init__(self):
        self.valves = self.Valves()
        self.citation = True

    def send_notification(
        self,
        message: str,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        alert_level: str = "active",
        sound: Optional[str] = None,
        group: Optional[str] = None,
        custom_fields: Optional[Dict[str, str]] = None,
    ):
        """Send a push notification to the devices registered with SelfNotify."""
        token = self.valves.token.strip()
        if not token:
            return {"ok": False, "error": "SelfNotify token is not configured in the tool valves."}
        if not message or not message.strip():
            return {"ok": False, "error": "message is required."}
        if len(message.strip()) > 500:
            return {"ok": False, "error": "message must be 500 characters or fewer."}

        normalized_alert_level = (alert_level or "active").strip().lower()
        normalized_alert_level = self.ALERT_LEVEL_ALIASES.get(
            normalized_alert_level,
            normalized_alert_level,
        )
        if normalized_alert_level not in self.VALID_ALERT_LEVELS:
            return {
                "ok": False,
                "error": "Invalid alert_level.",
                "allowed_alert_levels": sorted(self.VALID_ALERT_LEVELS),
            }

        normalized_sound = sound.strip() if sound else None
        if normalized_sound and normalized_sound not in self.VALID_SOUNDS and not normalized_sound.startswith("cs"):
            return {
                "ok": False,
                "error": "Invalid sound. Use snd01 through snd16 or a custom sound such as cs1.",
            }

        payload: Dict[str, Any] = {
            "token": token,
            "message": message.strip(),
            "alert_level": normalized_alert_level,
        }
        optional_values = {
            "title": title,
            "subtitle": subtitle,
            "sound": normalized_sound,
            "group": group,
        }
        for field_name, value in optional_values.items():
            if value is not None and value.strip():
                payload[field_name] = value.strip()

        if custom_fields:
            for field_name, value in custom_fields.items():
                if not field_name.startswith("custom_"):
                    return {
                        "ok": False,
                        "error": f"Custom field '{field_name}' must start with 'custom_'.",
                    }
                if not isinstance(value, str):
                    return {"ok": False, "error": f"Custom field '{field_name}' must be a string."}
                payload[field_name] = value

        request = Request(
            self.valves.endpoint.strip(),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json, text/plain",
                "Content-Type": "application/json",
                "User-Agent": "OpenWebUI-SelfNotify-Tool/0.1",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.valves.timeout_seconds) as response:
                response_body = response.read().decode("utf-8").strip()
                status_code = response.status
        except HTTPError as exc:
            try:
                response_body = exc.read().decode("utf-8").strip()
            except Exception:
                response_body = str(exc.reason)
            return {
                "ok": False,
                "status_code": exc.code,
                "response": response_body,
                "error": self._status_error(exc.code),
            }
        except URLError as exc:
            return {"ok": False, "error": f"SelfNotify connection failed: {exc.reason}"}
        except TimeoutError:
            return {
                "ok": False,
                "error": f"SelfNotify request timed out after {self.valves.timeout_seconds} seconds.",
            }

        try:
            parsed_response: Any = json.loads(response_body)
        except json.JSONDecodeError:
            parsed_response = response_body

        return {
            "ok": status_code in (200, 202),
            "status_code": status_code,
            "response": parsed_response,
            "message_sent": status_code in (200, 202),
        }

    def _status_error(self, status_code: int) -> str:
        status_errors = {
            400: "SelfNotify rejected the request. Check that message and token are valid.",
            401: "SelfNotify rejected the token. Check the token in the tool valves.",
            403: "SelfNotify denied the request. Check the token and account permissions.",
            406: "SelfNotify daily notification limit was reached.",
            429: "SelfNotify rate-limited the request. Try again later.",
        }
        return status_errors.get(status_code, f"SelfNotify returned HTTP {status_code}.")
