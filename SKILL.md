---
name: milky-way-spot-scout
description: Research, compare, and recommend Milky Way photography locations with real-time or forecast weather, moon-window gating, light-pollution baselines, Milky Way core geometry, and auditable score breakdowns. Use when Codex needs to help an astrophotography user choose where and when to shoot, compare candidate sites, check whether the Moon interferes with a specific shooting window, or produce a ranked shortlist with source links and per-metric evidence. Do not use historical weather as a ranking input. Default to a structured output that leads with weather, especially cloud cover, and place source links directly after each scored criterion.
---

# Milky Way Spot Scout

## Overview

Research candidate Milky Way photography sites for a specific shooting window, reject sites where the Moon materially interferes, and rank the remaining options with auditable per-metric evidence.

This skill requires real-time, near-real-time, or forecast weather data. Light pollution and elevation remain baseline suitability inputs, but they never override a bad moon window or poor forecast.

Default response style:
- Use a structured output, not a prose-only recommendation.
- Put the weather block before the other metric blocks.
- Show cloud cover first inside the weather block because it is the most decision-critical variable for star visibility.
- After each scored criterion or metric line, add a `来源：...` line immediately below it instead of collecting all sources at the very end.

## Reading Order

Read these references as needed:
- `references/data-sources.md`
  Use first to choose the default source stack and confirm that weather inputs are real-time or forecast, not historical.
- `references/research-checklist.md`
  Use before browsing so every candidate site is collected with the same window-aware and evidence-aware structure.
- `references/scoring-model.md`
  Use when interpreting the score or adjusting weights for a special trip.

Use this script after the raw data is collected:
- `scripts/rank_spots.py`
  Score and rank candidate-site JSON, then emit markdown, JSON, or both.

## Workflow

1. Anchor the shooting window.
   - Collect `shooting_window_start_local` and `shooting_window_end_local`.
   - Treat this as the primary decision frame. The site only needs to work for this window, not for the entire night.
2. Gate on Moon interference.
   - Check `moonrise_local`, `moonset_local`, and whether the Moon stays below the horizon during the shooting window.
   - If the Moon is outside the window, that is a strong pass even if the night is not fully moonless.
   - If the Moon overlaps most of the window, demote or reject the site before comparing dark-sky quality.
3. Collect real-time or forecast weather.
   - Prioritize cloud cover, humidity, visibility, smoke, and forecast confidence from a real-time or forecast source.
   - Do not rank sites from historical seasonality alone. If forecast weather is unavailable, stop and say the recommendation cannot yet be trusted.
4. Collect astronomy geometry and site baseline.
   - Record Milky Way core altitude and azimuth for the actual shooting window.
   - Record light pollution, elevation, horizon openness, access, and safety.
5. Normalize, score, and audit.
   - Put all candidates into the checklist JSON shape.
   - Run `python3 scripts/rank_spots.py <input.json> --format both`.
   - Review any `moon_window_status=fail`, `weather_requirement_status=fail`, or high missing-field counts before trusting the final rank.
6. Deliver the recommendation in a fixed structure.
   - One ranking table.
   - One best pick and two backups.
   - One per-site score card with structured metric blocks.
   - One data-freshness note explaining what is real-time, what is baseline, and what remains uncertain.
   - Put source links immediately after each criterion line as `来源：...`.

## Moon Rule

This skill uses a hard Moon gate by default:

- `pass`
  - The Moon remains below the horizon for the shooting window, or otherwise does not interfere with the window.
- `partial`
  - The Moon overlaps only part of the window and still permits some viable shooting time.
- `fail`
  - The Moon overlaps most or all of the shooting window. The site can still be listed for transparency, but its total score should be capped to a fallback tier.

Do not treat “longest astronomical darkness” as the main decision variable. If the Moon is outside the intended shooting window and the Milky Way core is usable, the site can still be excellent.

## Source Rules

- Prefer `meteoblue` for weather and astronomy-seeing forecasts.
- Use `Windy` or `Ventusky` as weather backups when you need a second opinion or a clearer map-based view.
- Prefer `timeanddate.com` for moonrise, moonset, and moon phase.
- Prefer `airmass.org` or `Stellarium Web` for Milky Way core altitude, azimuth, and timing.
- Prefer `lightpollutionmap.info` for Bortle or SQM baselines.
- Use stable map or destination pages for practical access and safety context when useful.
- Always record the source URL and a local retrieval timestamp in the data payload.

## Required Data Contract

For each candidate, try to capture at least:
- `name`
- `region`
- `latitude`
- `longitude`
- `shooting_window_start_local`
- `shooting_window_end_local`
- `moonrise_local`
- `moonset_local`
- `moon_below_horizon_during_window`
- `moon_window_status`
- `cloud_cover_pct`
- `humidity_pct`
- `visibility_km`
- `smoke_risk_score`
- `haze_risk_score`
- `weather_data_kind`
- `weather_requirement_status`
- `light_pollution_bortle` or `sqm`
- `elevation_m`
- `city_glow_direction`
- `city_glow_severity_score`
- `milky_way_core_altitude_deg`
- `milky_way_core_azimuth_deg`
- `horizon_clearance_score`
- `drive_hours`
- `access_score`
- `safety_score`
- `parking_risk_score`
- `walking_risk_score`
- `forecast_confidence`
- `retrieved_at_local`
- `sources_by_metric`

If some baseline fields are missing, keep going. If weather is not real-time or forecast, treat the candidate as not eligible for recommendation.

## Output Contract

Always deliver:
- a ranked summary table
- a structured score card for each shortlisted site
- retrieval timestamps
- a freshness note separating:
  - real-time or forecast weather and moon data
  - baseline static data such as light pollution and elevation
  - unresolved uncertainty

Use this response shape by default:

1. Ranked summary table
   - Include at least: `排名`, `地点`, `总分`, `天气分`, `云量`, `湿度`, `能见度`, `光污染`, `观测日期/窗口`, `一句话判断`.
2. Structured per-site card
   - `观测窗口`
     - Show date and local shooting window.
     - Add `来源：...` immediately after the line.
   - `天气明细`
     - Show `云量`, `湿度`, `能见度`, `smoke_risk`, `haze_risk`, `forecast_confidence`, `天气分`.
     - List cloud cover first.
     - After each line or tightly related mini-block, add `来源：...`.
   - `暗空明细`
     - Show `Bortle` or `SQM`, `海拔`, `city_glow_direction`, `city_glow_risk`, `暗空分`.
     - Add `来源：...` immediately after the line or mini-block.
   - `月亮明细`
     - Show `观测日期`, `月落`, `月升`, `moon_window_status`, `月亮分`.
     - Add `来源：...` immediately after the line or mini-block.
   - `银河几何明细`
     - Show `银河核心高度`, `银河核心方位`, `地平线开阔度/几何分`.
     - Add `来源：...` immediately after the line or mini-block.
   - `交通与安全明细`
     - Show `车程`, `access_score`, `safety_score`, `parking_risk`, `walking_risk`, `交通安全分`.
     - Add `来源：...` immediately after the line or mini-block.
3. Short conclusion
   - End with a brief AI judgment in 1 to 3 sentences.

Formatting rules for sources:
- Do not put all sources only in a final appendix unless the user explicitly asks for that.
- For each criterion block, place `来源：` on the next line and include the exact source link and retrieval timestamp when available.
- If two sources support the same criterion, put both in the same `来源：` line separated clearly.
- If a value is inferred rather than directly reported, say `来源：...；说明：基于该来源推算`.

When answering in prose, use labels like:
- `best overall for this shooting window`
- `darkest-sky backup`
- `safer logistics backup`
