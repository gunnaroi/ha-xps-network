"""Minimal GraphQL client for the XPS Network app (app.xpsnetwork.com).

Reverse-engineered from the XPS Network 2.0 web app's own traffic and its
minified JS bundle. There is no public API or documentation for this
service.

Unlike Sportabler, XPS Network authenticates with a plain username/password
GraphQL mutation (`authenticate2022`) that returns a `sessionId`. That
sessionId is not a cookie - it's passed as an explicit variable on every
subsequent query/mutation, and it eventually expires, at which point we
just log in again with the stored credentials.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import aiohttp

from .const import GRAPHQL_URL

_LOGGER = logging.getLogger(__name__)

FRAGMENT_SESSION_FIELDS = """
  id
  groupId
  label
  notes
  location
  xtraLocation
  start
  durationMinutes
  cancelled
  teamName
  attendance {
    athleteGuid
    athleteName
    attendance
    athleteComment
  }
"""

MUTATION_AUTHENTICATE = """
mutation authenticate2022($username: String!, $password: String!, $app: String, $appVersion: String) {
  authenticate2022(username: $username, password: $password, app: $app, appVersion: $appVersion) {
    sessionId
    userFriendlyRejection
    result
  }
}
"""

QUERY_FAMILY_MEMBERS = """
query getMyFamilyMemberAthletes($sessionId: String!) {
  UserProfile(sessionId: $sessionId) {
    id
    family {
      membersOfFamily {
        ... on XpsUser {
          id
          name
          firstName
          lastName
          thumb
        }
      }
    }
  }
}
"""

QUERY_AGENDA = (
    """
query agenda($sessionId: ID, $from: Long, $first: Int, $timezone: String) {
  agenda(sessionId: $sessionId, from: $from, first: $first, timezone: $timezone) {
    edges {
      node {
        __typename
        ... on Practice {
"""
    + FRAGMENT_SESSION_FIELDS
    + """
        }
        ... on Game {
"""
    + FRAGMENT_SESSION_FIELDS
    + """
        }
        ... on Event {
"""
    + FRAGMENT_SESSION_FIELDS
    + """
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""
)

MUTATION_UPDATE_ATTENDANCE = """
mutation updateAttendance2($sessionId: ID, $inputs: [AttendanceInput]!) {
  updateAttendance2(sessionId: $sessionId, inputs: $inputs) {
    athleteGuid
    attendance
    comment
  }
}
"""


class XpsApiError(Exception):
    """Generic XPS Network API error."""


class XpsAuthError(XpsApiError):
    """The username/password were rejected, or the session expired."""


class XpsApiClient:
    """Talks to www4.xpsnetwork.com/xpsweb using a `sessionId` GraphQL variable."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self.session_id: str | None = None

    async def _post(
        self, operation_name: str, query: str, variables: dict[str, Any]
    ) -> dict[str, Any]:
        url = f"{GRAPHQL_URL}?opname={operation_name}&operation=graphql"
        async with self._session.post(
            url,
            json={
                "operationName": operation_name,
                "query": query,
                "variables": variables,
            },
            headers={"content-type": "application/json"},
        ) as resp:
            resp.raise_for_status()
            body = await resp.json()

        if body.get("errors"):
            errors = body["errors"]
            _LOGGER.error("XPS Network GraphQL error for %s: %s", operation_name, errors)
            if resp.status == 401 or any(
                "not authenticated" in str(e).lower()
                or "invalid session" in str(e).lower()
                or "session expired" in str(e).lower()
                for e in errors
            ):
                raise XpsAuthError(str(errors))
            raise XpsApiError(f"{operation_name}: {errors}")
        return body["data"]

    async def async_login(self) -> str:
        """Authenticate with the stored username/password and cache the sessionId."""
        data = await self._post(
            "authenticate2022",
            MUTATION_AUTHENTICATE,
            {
                "username": self._username,
                "password": self._password,
                "app": "xpsweb",
                "appVersion": "1.0.0",
            },
        )
        result = data["authenticate2022"]
        session_id = result.get("sessionId")
        if not session_id:
            raise XpsAuthError(
                result.get("userFriendlyRejection") or "Login rejected by XPS Network"
            )
        self.session_id = session_id
        return session_id

    async def _authed_post(
        self, operation_name: str, query: str, variables: dict[str, Any]
    ) -> dict[str, Any]:
        if not self.session_id:
            await self.async_login()
        variables = {"sessionId": self.session_id, **variables}
        try:
            return await self._post(operation_name, query, variables)
        except XpsAuthError:
            await self.async_login()
            variables["sessionId"] = self.session_id
            return await self._post(operation_name, query, variables)

    async def async_get_family_members(self) -> list[dict[str, Any]]:
        data = await self._authed_post("getMyFamilyMemberAthletes", QUERY_FAMILY_MEMBERS, {})
        profile = data.get("UserProfile") or {}
        family = profile.get("family") or {}
        return [m for m in (family.get("membersOfFamily") or []) if m]

    async def async_get_agenda(
        self, from_epoch_ms: int, first: int = 200
    ) -> list[dict[str, Any]]:
        """Fetch a page of the agenda starting at `from_epoch_ms`.

        Returns a flat list of session dicts (practices/games/events merged),
        each tagged with a `session_type` key.
        """
        data = await self._authed_post(
            "agenda",
            QUERY_AGENDA,
            {"from": from_epoch_ms, "first": first, "timezone": _local_timezone()},
        )
        edges = data.get("agenda", {}).get("edges") or []
        sessions: list[dict[str, Any]] = []
        for edge in edges:
            node = edge.get("node") or {}
            if not node.get("id"):
                continue
            node = dict(node)
            node["session_type"] = (node.pop("__typename", None) or "session").lower()
            sessions.append(node)
        return sessions

    async def async_set_attendance(
        self, session_id: str, athlete_id: str, status: str, comment: str = ""
    ) -> dict[str, Any]:
        data = await self._authed_post(
            "updateAttendance2",
            MUTATION_UPDATE_ATTENDANCE,
            {
                "inputs": [
                    {
                        "practiceGuid": session_id,
                        "athleteGuid": athlete_id,
                        "attendance": status,
                        "athleteComment": comment,
                        "comment": "",
                    }
                ]
            },
        )
        return data["updateAttendance2"]


def _local_timezone() -> str:
    return time.strftime("%Z") or "UTC"
