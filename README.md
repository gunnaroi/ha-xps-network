# XPS Network for Home Assistant

Unofficial integration for [XPS Network](https://app.xpsnetwork.com), reverse-engineered
from the app's own network traffic and JS bundle — there is no public API.

## What it gives you

- One **device per athlete/child**, with:
  - A `calendar.<athlete>` entity listing their upcoming sessions (practices, games,
    and other team events)
  - A `sensor.<athlete>_next_session` entity with the next session's time, location,
    team, and your current attendance response as attributes
- An `xps_network.set_attendance` service to set an athlete's attendance
  (`Attended` / `Sick` / `Injured` / `Other`) for a session from an automation or
  dashboard button (fields: `athlete_id`, `session_id`, `status`, optional `comment` —
  ids are visible in the sensor's `session_id` attribute and the device's identifiers)

## Install via HACS

1. In Home Assistant: **HACS → Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/gunnaroi/ha-xps-network`, category **Integration**
3. Find "XPS Network" in HACS and install it, then restart Home Assistant

## Setup

1. **Settings → Devices & Services → Add Integration → XPS Network**
2. Enter the username/email and password you normally use at
   [app.xpsnetwork.com](https://app.xpsnetwork.com)

Unlike some sports-club apps, XPS Network's login is a plain username/password
GraphQL call, so no cookie or token capture is needed — the integration logs in
itself and re-authenticates automatically if the session expires.

## Notes / limitations

- This talks to XPS Network's internal GraphQL API (`www4.xpsnetwork.com/xpsweb`),
  which is undocumented and can change without notice.
- The agenda query looks back 1 day and ahead 30 days on each poll (every 15 minutes).
- Practices, games, and events are all pulled in as calendar sessions; other session
  types the app may expose (workouts, questionnaires) are not yet included.
- This has not yet been exercised against a live account end-to-end — the GraphQL
  query/mutation shapes come from the app's own JS bundle rather than a captured live
  response. If something doesn't work, please open an issue with the error from the
  Home Assistant log.
