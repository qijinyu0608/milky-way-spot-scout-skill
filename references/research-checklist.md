# Research Checklist

Use this checklist before collecting data so each candidate site is evaluated for the same shooting window and with the same evidence shape.

## Confirm First

- Departure city or travel radius
- Target date or date window
- Intended shooting window, not just the calendar date
- Whether Moon avoidance is strict
  - default for this skill: yes
- Primary preference
  - best real-time weather
  - lowest cloud cover
  - darkest sky
  - easiest access
  - strongest foreground alignment

## Data Source Priority

Use `references/data-sources.md` before browsing. The short rule is:

- Weather: `meteoblue` first, `Windy` or `Ventusky` as backup
- Moon: `timeanddate.com`
- Milky Way core geometry: `airmass.org` or `Stellarium Web`
- Light pollution: `lightpollutionmap.info`
- Access and safety: stable map or destination pages are acceptable

## Candidate JSON Shape

Collect these fields when possible:

```json
{
  "preferences": {
    "max_drive_hours": 6,
    "preferred_azimuth_deg": 150,
    "azimuth_tolerance_deg": 25,
    "weights": {
      "weather": 30,
      "darkness": 20,
      "moon": 20,
      "composition": 20,
      "logistics": 10
    }
  },
  "candidates": [
    {
      "name": "Example Ridge",
      "region": "Example Province",
      "latitude": 31.234,
      "longitude": 121.456,
      "shooting_window_start_local": "2026-05-16T22:30:00+08:00",
      "shooting_window_end_local": "2026-05-17T01:30:00+08:00",
      "moonrise_local": "2026-05-17T03:08:00+08:00",
      "moonset_local": "2026-05-16T17:10:00+08:00",
      "moon_below_horizon_during_window": true,
      "moon_window_status": "pass",
      "moon_overlap_ratio": 0.0,
      "retrieved_at_local": "2026-05-15T18:20:00+08:00",
      "weather_data_kind": "forecast",
      "weather_requirement_status": "pass",
      "cloud_cover_pct": 18,
      "humidity_pct": 42,
      "visibility_km": 28,
      "smoke_risk_score": 15,
      "haze_risk_score": 20,
      "forecast_confidence": 0.82,
      "light_pollution_bortle": 3,
      "sqm": null,
      "elevation_m": 1480,
      "city_glow_direction": "northwest",
      "city_glow_severity_score": 25,
      "milky_way_core_altitude_deg": 21,
      "milky_way_core_azimuth_deg": 156,
      "astronomical_dark_hours": 4.6,
      "horizon_clearance_score": 88,
      "drive_hours": 3.2,
      "access_score": 80,
      "safety_score": 84,
      "parking_risk_score": 20,
      "walking_risk_score": 15,
      "notes": "South-southeast horizon is open. Wind shelter is limited.",
      "sources_by_metric": {
        "weather": [
          {
            "label": "meteoblue 7-day forecast",
            "url": "https://www.meteoblue.com/",
            "retrieved_at_local": "2026-05-15T18:10:00+08:00"
          }
        ],
        "moon": [
          {
            "label": "timeanddate moonrise/moonset",
            "url": "https://www.timeanddate.com/moon/",
            "retrieved_at_local": "2026-05-15T18:12:00+08:00"
          }
        ],
        "milky_way": [
          {
            "label": "airmass planner",
            "url": "https://airmass.org/",
            "retrieved_at_local": "2026-05-15T18:14:00+08:00"
          }
        ],
        "light_pollution": [
          {
            "label": "Light Pollution Map",
            "url": "https://www.lightpollutionmap.info/",
            "retrieved_at_local": "2026-05-15T18:15:00+08:00"
          }
        ],
        "access_safety": [
          {
            "label": "Map page",
            "url": "https://example.com/",
            "retrieved_at_local": "2026-05-15T18:18:00+08:00"
          }
        ]
      }
    }
  ]
}
```

## Required Interpretation Rules

1. Shooting window
   - `shooting_window_start_local` and `shooting_window_end_local` define the only window that matters.
   - If the end time is earlier than the start time, it means the window crosses midnight.
2. Moon window
   - Prefer recording `moon_window_status` directly as `pass`, `partial`, or `fail`.
   - Also record `moon_below_horizon_during_window` for quick reading.
   - If possible, include `moon_overlap_ratio` from `0.0` to `1.0`.
3. Weather requirement
   - Set `weather_data_kind` to one of:
     - `realtime`
     - `near-realtime`
     - `forecast`
   - Do not use `historical`.
   - Set `weather_requirement_status` to `pass` only when the weather input is real-time, near-real-time, or forecast.
4. Sources
   - Every metric group must have its own source list.
   - Prefer one primary source and one backup source rather than many weak links.
   - The final answer should surface these sources directly after each metric block as `来源：...`.

## What To Research For Each Site

1. Moon gate
   - Moonrise and moonset for the actual site or nearest reliable location
   - Whether the Moon stays below the horizon during the target window
   - Whether the Moon overlaps part of the window
2. Real-time or forecast weather
   - Cloud cover
   - Humidity
   - Visibility or haze
   - Smoke if relevant
   - Forecast confidence
   - When presenting results, list cloud cover first and do not bury it inside prose
3. Milky Way geometry
   - Core altitude during the target window
   - Core azimuth during the target window
   - Whether the target horizon is open
4. Baseline site quality
   - Bortle or SQM
   - Elevation
   - City-glow direction if obvious
5. Access and safety
   - Drive time
   - Parking and walking risk

## Normalization Notes

- `forecast_confidence` may be `0-1` or `0-100`.
- `horizon_clearance_score`, `access_score`, and `safety_score` may be `0-100` or `1-5`.
- `smoke_risk_score`, `haze_risk_score`, `city_glow_severity_score`, `parking_risk_score`, and `walking_risk_score` may be `0-100` or `1-5`, where higher means worse.
- `moon_overlap_ratio` should be `0.0-1.0`.
- Keep `notes` short and actionable.
- If the site has only historical weather, do not rank it.
- Final write-up should be structured and metric-led:
  - summary table first
  - per-site weather block before darkness, moon, geometry, and logistics
  - each block followed immediately by `来源：...`
