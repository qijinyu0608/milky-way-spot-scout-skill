# Scoring Model

Use this reference to explain why one site outranks another and to keep the ranking aligned with actual Milky Way shooting decisions.

## Default Weight Split

- Weather: `30`
- Darkness baseline: `20`
- Moon window: `20`
- Composition geometry: `20`
- Logistics and safety: `10`

These weights sum to `100`.

## Order Of Operations

1. Evaluate the Moon window first.
2. Validate the weather requirement.
3. Score all five categories.
4. If `moon_window_status=fail`, cap the final total to a fallback tier even if the site is otherwise strong.
5. If weather is not real-time, near-real-time, or forecast, mark the candidate ineligible and do not recommend it.

## Category Intent

### Weather

Favor:
- lower cloud cover
- lower humidity
- better visibility
- lower smoke risk
- lower haze risk
- higher forecast confidence
- real-time, near-real-time, or forecast data only

This category should dominate short-term trip recommendations.
In the final write-up, show this category first and put `cloud_cover_pct` before the other weather fields.

### Darkness Baseline

Favor:
- lower Bortle class
- higher SQM
- useful elevation
- less intrusive city-glow in the shooting direction

This category measures permanent site quality. It never overrides a bad Moon window.

### Moon Window

This category is window-based, not night-length-based.

Favor:
- `pass`: the Moon stays out of the shooting window
- `partial`: the Moon overlaps only a limited part of the window
- `fail`: the Moon overlaps most or all of the window

`astronomical_dark_hours` is only a secondary context input here.

### Composition Geometry

Favor:
- usable Milky Way core altitude in the target window
- useful azimuth for the intended foreground
- open target horizon

Do not judge azimuth in the abstract. It only matters relative to the user's framing goal.

### Logistics And Safety

Favor:
- practical drive time
- safer parking and walking conditions

This category should stop impractical or unsafe sites from winning by darkness alone.

## Moon Gate Defaults

- `pass`
  - Moon score should remain high.
  - Final total is uncapped.
- `partial`
  - Moon score should drop materially based on overlap ratio when available.
  - Final total remains uncapped, but the explanation must state the overlap.
- `fail`
  - Moon score should fall to the bottom tier.
  - Final total should be capped to a fallback range, even if the site is dark and accessible.

Recommended cap for `fail`: final score `<= 44`.

## Confidence Status

Use these default labels:

- `high`
  - real-time, near-real-time, or forecast weather
  - strong forecast confidence
  - low missing-field count
- `medium`
  - some uncertainty or a few missing fields
- `low`
  - weak forecast confidence or too many missing fields
- `invalid`
  - weather is historical or otherwise does not satisfy the weather requirement

## Interpreting Totals

- `85-100`: excellent for the stated shooting window
- `70-84`: strong candidate with manageable tradeoffs
- `55-69`: usable, but not a clear first choice
- below `55`: backup only or reject

The score is a decision aid, not ground truth. Always explain major hidden risks such as crowds, wind exposure, or intrusive site lighting.

## Presentation Rule

- The final answer must be structured, not just a totals list.
- Put the weather block before the other scoring blocks.
- After each criterion line or tightly related metric mini-block, add `来源：...`.
- If the user cares most about whether the sky will actually open, say so explicitly and point to cloud cover first before discussing darkness.
