# Default Data Sources

Use this source stack by default. Prefer these sites because they are stable, broadly accessible, and practical for browser-based research.

## Weather And Cloud Cover

- Primary: [meteoblue](https://www.meteoblue.com/)
  - Use the 7-day forecast and Astronomy Seeing views when available.
  - Best for cloud cover, humidity, visibility proxies, and astronomy-specific sky conditions in the next 1 to 7 days.
- Backups:
  - [Windy](https://www.windy.com/)
  - [Ventusky](https://www.ventusky.com/cloud-base-map)

Rules:
- Prefer real-time, near-real-time, or forecast weather for the target night.
- Do not use historical seasonality as a ranking input.
- If the target date is too far away to have forecast weather, stop and say the skill cannot yet produce a reliable recommendation.
- When sources disagree, keep the primary source, mention the backup disagreement, and lower confidence if needed.

## Moonrise, Moonset, Moon Phase

- Primary: [timeanddate.com Moon](https://www.timeanddate.com/moon/)

Rules:
- Use the target site or the nearest reliable location.
- Record moonrise, moonset, moon phase, and the retrieval timestamp.
- Convert the result into `moon_window_status` for the actual shooting window.

## Milky Way Core Geometry

- Primary: [airmass.org](https://airmass.org/)
- Backup: [Stellarium Web](https://stellarium-web.org/)
- Project homepage for Stellarium: [stellarium.org](https://stellarium.org/)

Rules:
- Always bind altitude and azimuth to a specific place and time.
- Do not use vague seasonal heuristics like “spring faces southeast.”
- Record the exact shooting window used to derive the geometry.

## Light Pollution

- Primary: [Light Pollution Map](https://www.lightpollutionmap.info/)

Rules:
- Record Bortle or SQM.
- Mark this as baseline static data, not real-time data.
- If the local horizon has obvious city glow in one direction, mention it in notes.

## Safety And Practical Access

- Suggested sources: stable map services and destination pages

Rules:
- Use sources that are stable and easy to verify.
- Treat this as practical context, not a hard compliance workflow.

## Retrieval And Citation Rules

- Store links by metric group in `sources_by_metric`.
- Every source entry should include:
  - `label`
  - `url`
  - `retrieved_at_local`
- If weather is not real-time or forecast, do not continue to rank the site.
