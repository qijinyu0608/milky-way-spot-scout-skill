#!/usr/bin/env python3
"""Rank Milky Way photography sites with moon-window gating and auditable evidence."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

DEFAULT_WEIGHTS = {
    "weather": 30.0,
    "darkness": 20.0,
    "moon": 20.0,
    "composition": 20.0,
    "logistics": 10.0,
}

IMPORTANT_FIELDS = [
    "shooting_window_start_local",
    "shooting_window_end_local",
    "weather_data_kind",
    "cloud_cover_pct",
    "milky_way_core_altitude_deg",
    "horizon_clearance_score",
    "access_score",
    "safety_score",
]

ALLOWED_WEATHER_KINDS = {"realtime", "near-realtime", "forecast"}


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def average(parts: Iterable[Tuple[float | None, float]]) -> float:
    usable = [(score, weight) for score, weight in parts if score is not None]
    if not usable:
        return 50.0
    total_weight = sum(weight for _, weight in usable)
    return sum(score * weight for score, weight in usable) / total_weight


def to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return None
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "y", "1", "pass"}:
            return True
        if lowered in {"false", "no", "n", "0", "fail"}:
            return False
    return None


def parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize_rating(value: Any) -> float | None:
    raw = to_float(value)
    if raw is None:
        return None
    if raw <= 5:
        return clamp((raw / 5.0) * 100.0)
    return clamp(raw)


def score_inverse_rating(value: Any) -> float | None:
    normalized = normalize_rating(value)
    if normalized is None:
        return None
    return clamp(100.0 - normalized)


def score_cloud(value: Any) -> float | None:
    cloud = to_float(value)
    if cloud is None:
        return None
    return clamp(100.0 - cloud * 1.15)


def score_humidity(value: Any) -> float | None:
    humidity = to_float(value)
    if humidity is None:
        return None
    if humidity <= 35:
        return 100.0
    if humidity <= 55:
        return clamp(100.0 - (humidity - 35.0) * 1.5)
    if humidity <= 80:
        return clamp(70.0 - (humidity - 55.0) * 1.8)
    return clamp(25.0 - (humidity - 80.0) * 1.25)


def score_visibility(value: Any) -> float | None:
    visibility = to_float(value)
    if visibility is None:
        return None
    return clamp((visibility - 3.0) / 27.0 * 100.0)


def score_confidence(value: Any) -> float | None:
    confidence = to_float(value)
    if confidence is None:
        return None
    if confidence <= 1.0:
        confidence *= 100.0
    return clamp(confidence)


def score_bortle(value: Any) -> float | None:
    bortle = to_float(value)
    if bortle is None:
        return None
    if bortle <= 1:
        return 100.0
    if bortle >= 9:
        return 0.0
    return clamp(100.0 - (bortle - 1.0) * 12.5)


def score_sqm(value: Any) -> float | None:
    sqm = to_float(value)
    if sqm is None:
        return None
    return clamp((sqm - 19.0) / 3.0 * 100.0)


def score_elevation(value: Any) -> float | None:
    elevation = to_float(value)
    if elevation is None:
        return None
    if elevation <= 0:
        return 35.0
    if elevation <= 800:
        return clamp(35.0 + elevation / 800.0 * 35.0)
    if elevation <= 2400:
        return clamp(70.0 + (elevation - 800.0) / 1600.0 * 25.0)
    if elevation <= 3800:
        return clamp(95.0 - (elevation - 2400.0) / 1400.0 * 15.0)
    return 75.0


def score_dark_hours(value: Any) -> float | None:
    hours = to_float(value)
    if hours is None:
        return None
    return clamp(hours / 6.0 * 100.0)


def score_core_altitude(value: Any) -> float | None:
    altitude = to_float(value)
    if altitude is None:
        return None
    if altitude <= 0:
        return 0.0
    if altitude <= 12:
        return clamp(altitude / 12.0 * 70.0)
    if altitude <= 35:
        return clamp(70.0 + (altitude - 12.0) / 23.0 * 30.0)
    if altitude <= 55:
        return clamp(100.0 - (altitude - 35.0) / 20.0 * 18.0)
    return 80.0


def score_azimuth(actual: Any, preferred: Any, tolerance: Any) -> float | None:
    azimuth = to_float(actual)
    target = to_float(preferred)
    window = to_float(tolerance)
    if azimuth is None or target is None or window is None or window <= 0:
        return None
    delta = abs((azimuth - target + 180.0) % 360.0 - 180.0)
    if delta >= window:
        return 0.0
    return clamp((1.0 - delta / window) * 100.0)


def score_drive_hours(value: Any, max_drive: Any) -> float | None:
    hours = to_float(value)
    if hours is None:
        return None
    preferred_max = to_float(max_drive)
    if preferred_max is None or preferred_max <= 0:
        preferred_max = 4.0
    if hours <= preferred_max:
        return clamp(100.0 - (hours / preferred_max) * 30.0)
    penalty_window = max(preferred_max, 1.0)
    return clamp(70.0 - ((hours - preferred_max) / penalty_window) * 55.0)


def normalize_source_entry(entry: Any) -> Dict[str, Any]:
    if isinstance(entry, dict):
        return {
            "label": entry.get("label") or entry.get("url") or "Source",
            "url": entry.get("url"),
            "retrieved_at_local": entry.get("retrieved_at_local"),
        }
    if isinstance(entry, str):
        return {"label": entry, "url": entry if entry.startswith("http") else None, "retrieved_at_local": None}
    return {"label": "Source", "url": None, "retrieved_at_local": None}


def normalize_sources_by_metric(candidate: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    raw = candidate.get("sources_by_metric") or {}
    if not isinstance(raw, dict):
        raw = {}
    normalized: Dict[str, List[Dict[str, Any]]] = {}
    for key in ["weather", "moon", "milky_way", "light_pollution", "access_safety"]:
        entries = raw.get(key) or []
        if isinstance(entries, list):
            normalized[key] = [normalize_source_entry(item) for item in entries]
        else:
            normalized[key] = [normalize_source_entry(entries)]
    return normalized


def format_source_links(entries: List[Dict[str, Any]]) -> str:
    if not entries:
        return "未记录"
    formatted = []
    for entry in entries:
        label = entry.get("label") or entry.get("url") or "Source"
        url = entry.get("url")
        stamp = entry.get("retrieved_at_local")
        if url:
            chunk = f"[{label}]({url})"
        else:
            chunk = label
        if stamp:
            chunk += f" ({stamp})"
        formatted.append(chunk)
    return "; ".join(formatted)


def render_source_line(entries: List[Dict[str, Any]], note: str | None = None) -> str:
    line = f"来源：{format_source_links(entries)}"
    if note:
        line += f"；说明：{note}"
    return line


def to_display_number(value: Any, digits: int = 1) -> str:
    numeric = to_float(value)
    if numeric is None:
        return "未知"
    if digits == 0:
        return f"{numeric:.0f}"
    if numeric.is_integer():
        return f"{numeric:.0f}"
    return f"{numeric:.{digits}f}"


def format_metric_value(value: Any, suffix: str = "", digits: int = 1) -> str:
    rendered = to_display_number(value, digits=digits)
    if rendered == "未知":
        return rendered
    return f"{rendered}{suffix}"


def format_risk_value(value: Any) -> str:
    normalized = normalize_rating(value)
    if normalized is None:
        return "未知"
    if normalized <= 20:
        return "低"
    if normalized <= 50:
        return "中"
    if normalized <= 80:
        return "高"
    return "很高"


def format_confidence_value(value: Any) -> str:
    normalized = score_confidence(value)
    if normalized is None:
        return "未知"
    return f"{normalized:.0f}%"


def format_datetime_local(value: Any) -> str:
    dt = parse_datetime(value)
    if dt is None:
        return "未知"
    return dt.strftime("%Y-%m-%d %H:%M")


def format_observation_date(candidate: Dict[str, Any]) -> str:
    start = parse_datetime(candidate.get("shooting_window_start_local"))
    if start is None:
        return "未知"
    return start.strftime("%Y-%m-%d")


def format_window_string(candidate: Dict[str, Any]) -> str:
    start, end, _ = normalized_window_datetimes(candidate)
    if start is None or end is None:
        return "未知"
    return f"{start.strftime('%Y-%m-%d %H:%M')} 至 {end.strftime('%Y-%m-%d %H:%M')}"


def format_light_pollution_value(candidate: Dict[str, Any]) -> str:
    bortle = to_float(candidate.get("light_pollution_bortle"))
    if bortle is not None:
        return f"Bortle {to_display_number(bortle, digits=0)}"
    sqm = to_float(candidate.get("sqm"))
    if sqm is not None:
        return f"SQM {to_display_number(sqm, digits=1)}"
    return "未知"


def format_optional_text(value: Any) -> str:
    if value in (None, ""):
        return "未知"
    return str(value)


def format_window_source_entries(candidate: Dict[str, Any], moon_sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if moon_sources:
        return moon_sources
    retrieved_at = candidate.get("retrieved_at_local")
    if not retrieved_at:
        return []
    return [
        {
            "label": "本次汇总记录时间",
            "url": None,
            "retrieved_at_local": retrieved_at,
        }
    ]


def moon_status_is_inferred(candidate: Dict[str, Any]) -> bool:
    explicit_status = str(candidate.get("moon_window_status") or "").strip().lower()
    return explicit_status not in {"pass", "partial", "fail"}


def build_conclusion_label(item: Dict[str, Any]) -> str:
    if item["rank"] == 1:
        return "best overall for this shooting window"
    if item["component_scores"]["darkness"] >= item["component_scores"]["logistics"]:
        return "darkest-sky backup"
    return "safer logistics backup"


def build_conclusion(item: Dict[str, Any]) -> str:
    summary = item["summary"]
    if item["moon_window_status"] == "fail":
        tail = "月亮干扰覆盖了大部分窗口，本次只适合作为兜底备选。"
    elif item["confidence_status"] in {"low", "invalid"}:
        tail = "天气置信度偏弱，出发前还需要再复核一次天气和月亮数据。"
    elif item["component_scores"]["weather"] >= 80:
        tail = "如果这次最关心能不能顺利开天，先看天气块，这里是它的主要优势。"
    else:
        tail = "整体可拍，但更适合结合你的前景偏好和路程容忍度再做取舍。"
    return f"{build_conclusion_label(item)}：{summary}。{tail}"


def collect_missing(candidate: Dict[str, Any]) -> List[str]:
    missing = []
    if candidate.get("light_pollution_bortle") in (None, "") and candidate.get("sqm") in (None, ""):
        missing.append("light_pollution_bortle_or_sqm")
    if candidate.get("moon_window_status") in (None, "") and candidate.get("moon_below_horizon_during_window") in (None, ""):
        missing.append("moon_window_status_or_moon_below_horizon_during_window")
    if not candidate.get("sources_by_metric"):
        missing.append("sources_by_metric")
    for field in IMPORTANT_FIELDS:
        if candidate.get(field) in (None, ""):
            missing.append(field)
    return missing


def determine_weather_requirement(candidate: Dict[str, Any]) -> Dict[str, str]:
    weather_kind = str(candidate.get("weather_data_kind") or "").strip().lower()
    if weather_kind in ALLOWED_WEATHER_KINDS:
        return {
            "status": "pass",
            "kind": weather_kind,
            "explanation": "Weather input is real-time, near-real-time, or forecast and can be used for ranking.",
        }
    if weather_kind == "historical":
        return {
            "status": "fail",
            "kind": weather_kind,
            "explanation": "Historical weather is not allowed for ranking in this skill.",
        }
    return {
        "status": "fail",
        "kind": weather_kind or "missing",
        "explanation": "Weather input is missing or not marked as real-time/forecast, so the candidate is not eligible.",
    }


def normalize_weights(preferences: Dict[str, Any]) -> Dict[str, float]:
    weights = DEFAULT_WEIGHTS.copy()
    overrides = preferences.get("weights", {})
    if isinstance(overrides, dict):
        for key, value in overrides.items():
            if key in weights:
                numeric = to_float(value)
                if numeric is not None and numeric >= 0:
                    weights[key] = numeric
    total = sum(weights.values()) or 1.0
    return {key: value / total * 100.0 for key, value in weights.items()}


def normalized_window_datetimes(candidate: Dict[str, Any]) -> Tuple[datetime | None, datetime | None, float | None]:
    start = parse_datetime(candidate.get("shooting_window_start_local"))
    end = parse_datetime(candidate.get("shooting_window_end_local"))
    if start is None or end is None:
        return start, end, None
    if end <= start:
        end = end + timedelta(days=1)
    return start, end, (end - start).total_seconds() / 3600.0


def intersect_hours(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> float:
    latest_start = max(start_a, start_b)
    earliest_end = min(end_a, end_b)
    seconds = (earliest_end - latest_start).total_seconds()
    return max(0.0, seconds / 3600.0)


def infer_overlap_from_events(candidate: Dict[str, Any], window_start: datetime | None, window_end: datetime | None) -> float | None:
    if window_start is None or window_end is None:
        return None

    moonrise = parse_datetime(candidate.get("moonrise_local"))
    moonset = parse_datetime(candidate.get("moonset_local"))
    if moonrise is None and moonset is None:
        return None

    overlaps: List[float] = []
    if moonrise is not None and moonset is not None:
        if moonrise <= moonset:
            overlaps.append(intersect_hours(window_start, window_end, moonrise, moonset))
        else:
            overlaps.append(intersect_hours(window_start, window_end, window_start - timedelta(days=1), moonset))
            overlaps.append(intersect_hours(window_start, window_end, moonrise, window_end + timedelta(days=1)))
    elif moonrise is not None:
        overlaps.append(intersect_hours(window_start, window_end, moonrise, window_end))
    elif moonset is not None:
        overlaps.append(intersect_hours(window_start, window_end, window_start, moonset))
    total = sum(overlaps)
    return total if total > 0 else 0.0


def determine_moon_window(candidate: Dict[str, Any]) -> Dict[str, Any]:
    explicit_status = str(candidate.get("moon_window_status") or "").strip().lower()
    overlap_ratio = to_float(candidate.get("moon_overlap_ratio"))
    overlap_hours = to_float(candidate.get("moon_overlap_hours"))
    window_start, window_end, window_hours = normalized_window_datetimes(candidate)

    moon_below = to_bool(candidate.get("moon_below_horizon_during_window"))
    if explicit_status in {"pass", "partial", "fail"}:
        status = explicit_status
    elif moon_below is True:
        status = "pass"
    else:
        if overlap_ratio is None and overlap_hours is None:
            overlap_hours = infer_overlap_from_events(candidate, window_start, window_end)
        if overlap_ratio is None and overlap_hours is not None and window_hours and window_hours > 0:
            overlap_ratio = clamp(overlap_hours / window_hours, 0.0, 1.0)
        if overlap_ratio is not None:
            if overlap_ratio <= 0:
                status = "pass"
            elif overlap_ratio < 0.6:
                status = "partial"
            else:
                status = "fail"
        elif moon_below is False:
            status = "partial"
        else:
            altitude = to_float(candidate.get("moon_altitude_deg"))
            if altitude is None:
                status = "partial"
            elif altitude <= 0:
                status = "pass"
            else:
                status = "fail"

    if status == "pass":
        base = 100.0
    elif status == "partial":
        ratio = overlap_ratio if overlap_ratio is not None else 0.35
        base = clamp(85.0 - ratio * 55.0, 35.0, 84.0)
    else:
        ratio = overlap_ratio if overlap_ratio is not None else 1.0
        base = clamp(20.0 - ratio * 10.0, 0.0, 25.0)

    dark_hours_score = score_dark_hours(candidate.get("astronomical_dark_hours"))
    moon_score = average([(base, 0.85), (dark_hours_score, 0.15)])
    explanation = {
        "pass": "Moon stays outside the shooting window or below the horizon for the usable window.",
        "partial": "Moon overlaps part of the shooting window, reducing usable shooting time.",
        "fail": "Moon overlaps most or all of the shooting window, so this site is only a fallback.",
    }[status]
    return {
        "status": status,
        "score": round(moon_score, 2),
        "overlap_ratio": round(overlap_ratio, 3) if overlap_ratio is not None else None,
        "overlap_hours": round(overlap_hours, 2) if overlap_hours is not None else None,
        "window_hours": round(window_hours, 2) if window_hours is not None else None,
        "explanation": explanation,
    }


def determine_confidence_status(candidate: Dict[str, Any], missing: List[str]) -> Tuple[str, str, float | None]:
    forecast_confidence = score_confidence(candidate.get("forecast_confidence"))
    weather_kind = str(candidate.get("weather_data_kind") or "").strip().lower()
    realtime_like = weather_kind in ALLOWED_WEATHER_KINDS
    if weather_kind not in ALLOWED_WEATHER_KINDS:
        return "invalid", "Weather input is not real-time, near-real-time, or forecast, so the candidate is not eligible.", forecast_confidence
    if forecast_confidence is not None and forecast_confidence >= 75 and realtime_like and len(missing) <= 2:
        return "high", "Real-time or forecast weather with strong confidence and limited missing fields.", forecast_confidence
    if forecast_confidence is not None and forecast_confidence >= 50 and len(missing) <= 5:
        return "medium", "Usable confidence, but some uncertainty or missing fields remain.", forecast_confidence
    return "low", "Forecast confidence is weak or too many required fields are missing.", forecast_confidence


def build_score_breakdown(
    candidate: Dict[str, Any],
    preferences: Dict[str, Any],
    moon_window: Dict[str, Any],
    sources_by_metric: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    weather_score = average(
        [
            (score_cloud(candidate.get("cloud_cover_pct")), 0.35),
            (score_humidity(candidate.get("humidity_pct")), 0.15),
            (score_visibility(candidate.get("visibility_km")), 0.15),
            (score_inverse_rating(candidate.get("smoke_risk_score")), 0.15),
            (score_inverse_rating(candidate.get("haze_risk_score")), 0.1),
            (score_confidence(candidate.get("forecast_confidence")), 0.1),
        ]
    )
    darkness_score = average(
        [
            (score_sqm(candidate.get("sqm")), 0.45),
            (score_bortle(candidate.get("light_pollution_bortle")), 0.45),
            (score_elevation(candidate.get("elevation_m")), 0.15),
            (score_inverse_rating(candidate.get("city_glow_severity_score")), 0.25),
        ]
    )
    azimuth_score = score_azimuth(
        candidate.get("milky_way_core_azimuth_deg"),
        preferences.get("preferred_azimuth_deg"),
        preferences.get("azimuth_tolerance_deg"),
    )
    composition_score = average(
        [
            (score_core_altitude(candidate.get("milky_way_core_altitude_deg")), 0.55),
            (normalize_rating(candidate.get("horizon_clearance_score")), 0.3),
            (azimuth_score, 0.15),
        ]
    )
    logistics_score = average(
        [
            (score_drive_hours(candidate.get("drive_hours"), preferences.get("max_drive_hours")), 0.25),
            (normalize_rating(candidate.get("access_score")), 0.2),
            (normalize_rating(candidate.get("safety_score")), 0.25),
            (score_inverse_rating(candidate.get("parking_risk_score")), 0.15),
            (score_inverse_rating(candidate.get("walking_risk_score")), 0.15),
        ]
    )
    return {
        "weather": {
            "score": round(weather_score, 2),
            "inputs": {
                "cloud_cover_pct": candidate.get("cloud_cover_pct"),
                "humidity_pct": candidate.get("humidity_pct"),
                "visibility_km": candidate.get("visibility_km"),
                "smoke_risk_score": candidate.get("smoke_risk_score"),
                "haze_risk_score": candidate.get("haze_risk_score"),
                "forecast_confidence": candidate.get("forecast_confidence"),
                "weather_data_kind": candidate.get("weather_data_kind"),
                "weather_requirement_status": candidate.get("weather_requirement_status"),
            },
            "explanation": "Uses cloud cover first, then humidity, visibility, smoke risk, haze risk, and forecast confidence. Only real-time, near-real-time, or forecast weather is allowed.",
            "sources": sources_by_metric["weather"],
        },
        "darkness": {
            "score": round(darkness_score, 2),
            "inputs": {
                "light_pollution_bortle": candidate.get("light_pollution_bortle"),
                "sqm": candidate.get("sqm"),
                "elevation_m": candidate.get("elevation_m"),
                "city_glow_direction": candidate.get("city_glow_direction"),
                "city_glow_severity_score": candidate.get("city_glow_severity_score"),
            },
            "explanation": "Baseline site quality from light pollution, elevation, and obvious city-glow direction/severity. This is static context, not a real-time condition.",
            "sources": sources_by_metric["light_pollution"],
        },
        "moon": {
            "score": moon_window["score"],
            "inputs": {
                "shooting_window_start_local": candidate.get("shooting_window_start_local"),
                "shooting_window_end_local": candidate.get("shooting_window_end_local"),
                "moonrise_local": candidate.get("moonrise_local"),
                "moonset_local": candidate.get("moonset_local"),
                "moon_below_horizon_during_window": candidate.get("moon_below_horizon_during_window"),
                "moon_window_status": moon_window["status"],
                "moon_overlap_ratio": moon_window["overlap_ratio"],
                "astronomical_dark_hours": candidate.get("astronomical_dark_hours"),
            },
            "explanation": moon_window["explanation"],
            "sources": sources_by_metric["moon"],
        },
        "composition": {
            "score": round(composition_score, 2),
            "inputs": {
                "milky_way_core_altitude_deg": candidate.get("milky_way_core_altitude_deg"),
                "milky_way_core_azimuth_deg": candidate.get("milky_way_core_azimuth_deg"),
                "horizon_clearance_score": candidate.get("horizon_clearance_score"),
                "preferred_azimuth_deg": preferences.get("preferred_azimuth_deg"),
                "azimuth_tolerance_deg": preferences.get("azimuth_tolerance_deg"),
            },
            "explanation": "Rewards usable Milky Way core height, a clear target horizon, and azimuth fit when the user provides a foreground direction.",
            "sources": sources_by_metric["milky_way"],
        },
        "logistics": {
            "score": round(logistics_score, 2),
            "inputs": {
                "drive_hours": candidate.get("drive_hours"),
                "max_drive_hours": preferences.get("max_drive_hours"),
                "access_score": candidate.get("access_score"),
                "safety_score": candidate.get("safety_score"),
                "parking_risk_score": candidate.get("parking_risk_score"),
                "walking_risk_score": candidate.get("walking_risk_score"),
            },
            "explanation": "Balances drive time with site access, safety, parking risk, and walking risk. A beautiful site should not win if it is unsafe or impractical.",
            "sources": sources_by_metric["access_safety"],
        },
    }


def build_summary(
    candidate: Dict[str, Any],
    total: float,
    score_breakdown: Dict[str, Dict[str, Any]],
    moon_window: Dict[str, Any],
    confidence_status: str,
    missing: List[str],
) -> str:
    positives = []
    warnings = []
    smoke_risk = normalize_rating(candidate.get("smoke_risk_score"))
    haze_risk = normalize_rating(candidate.get("haze_risk_score"))
    city_glow_risk = normalize_rating(candidate.get("city_glow_severity_score"))
    parking_risk = normalize_rating(candidate.get("parking_risk_score"))
    walking_risk = normalize_rating(candidate.get("walking_risk_score"))
    if moon_window["status"] == "pass":
        positives.append("月亮窗口干净")
    if str(candidate.get("weather_data_kind") or "").strip().lower() in ALLOWED_WEATHER_KINDS and score_breakdown["weather"]["score"] >= 80:
        positives.append("天气条件强")
    if score_breakdown["darkness"]["score"] >= 80:
        positives.append("暗空基线好")
    if score_breakdown["logistics"]["score"] >= 75:
        positives.append("交通相对稳妥")
    if smoke_risk is not None and smoke_risk >= 70:
        warnings.append("烟尘风险偏高")
    if haze_risk is not None and haze_risk >= 70:
        warnings.append("雾霾风险偏高")
    if moon_window["status"] == "partial":
        warnings.append("月亮部分压窗")
    if moon_window["status"] == "fail":
        warnings.append("月亮覆盖大部分窗口")
    if city_glow_risk is not None and city_glow_risk >= 70:
        warnings.append("城市光害方向明显")
    if (parking_risk is not None and parking_risk >= 70) or (walking_risk is not None and walking_risk >= 70):
        warnings.append("停车或步行风险高")
    if confidence_status == "invalid":
        warnings.append("天气数据不合格")
    if confidence_status == "low":
        warnings.append("天气置信度偏低")
    if missing:
        warnings.append(f"缺少 {len(missing)} 个关键字段")
    pieces = positives[:2] + warnings[:2]
    if not pieces:
        pieces.append("整体表现中性")
    summary = "，".join(pieces)
    if total >= 85:
        return f"{summary}，当前窗口竞争力很强"
    if total >= 70:
        return f"{summary}，是强候选"
    if total >= 55:
        return f"{summary}，可拍但不是绝对首选"
    return f"{summary}，更适合作为备选"


def score_candidate(candidate: Dict[str, Any], preferences: Dict[str, Any], weights: Dict[str, float]) -> Dict[str, Any]:
    sources_by_metric = normalize_sources_by_metric(candidate)
    weather_requirement = determine_weather_requirement(candidate)
    moon_window = determine_moon_window(candidate)
    score_breakdown = build_score_breakdown(candidate, preferences, moon_window, sources_by_metric)
    components = {key: item["score"] for key, item in score_breakdown.items()}
    raw_total = sum(components[key] * weights[key] / 100.0 for key in components)
    missing = collect_missing(candidate)
    uncertainty_penalty = min(len(missing) * 2.5, 12.5)
    total = clamp(raw_total - uncertainty_penalty)
    if moon_window["status"] == "fail":
        total = min(total, 44.0)
    if weather_requirement["status"] == "fail":
        total = 0.0
    confidence_status, confidence_explanation, forecast_confidence = determine_confidence_status(candidate, missing)
    summary = build_summary(candidate, total, score_breakdown, moon_window, confidence_status, missing)
    return {
        "name": candidate.get("name", "Unknown site"),
        "region": candidate.get("region"),
        "rank": None,
        "total_score": round(total, 2),
        "component_scores": {key: round(value, 2) for key, value in components.items()},
        "moon_window_status": moon_window["status"],
        "weather_requirement_status": weather_requirement["status"],
        "weather_requirement_explanation": weather_requirement["explanation"],
        "confidence_status": confidence_status,
        "confidence_explanation": confidence_explanation,
        "forecast_confidence_normalized": forecast_confidence,
        "missing_fields": missing,
        "summary": summary,
        "score_breakdown": score_breakdown,
        "evidence": sources_by_metric,
        "candidate": candidate,
    }


def load_payload(path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if path == "-":
        payload = json.load(sys.stdin)
    else:
        with Path(path).expanduser().open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

    if isinstance(payload, list):
        return payload, {}
    if isinstance(payload, dict):
        candidates = payload.get("candidates") or payload.get("sites") or []
        preferences = payload.get("preferences") or {}
        if not isinstance(candidates, list):
            raise ValueError("`candidates` must be a list.")
        if not isinstance(preferences, dict):
            raise ValueError("`preferences` must be an object.")
        return candidates, preferences
    raise ValueError("Input JSON must be a list or an object with `candidates`.")


def render_rank_table(ranked: List[Dict[str, Any]], top_n: int) -> str:
    rows = [
        "| 排名 | 地点 | 总分 | 天气分 | 云量 | 湿度 | 能见度 | 光污染 | 观测日期/窗口 | 一句话判断 |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for index, item in enumerate(ranked[:top_n], start=1):
        scores = item["component_scores"]
        candidate = item["candidate"]
        rows.append(
            "| {rank} | {name} | {total:.1f} | {weather:.1f} | {cloud} | {humidity} | {visibility} | {light_pollution} | {window} | {summary} |".format(
                rank=index,
                name=item["name"].replace("|", "/"),
                total=item["total_score"],
                weather=scores["weather"],
                cloud=format_metric_value(candidate.get("cloud_cover_pct"), suffix="%", digits=0),
                humidity=format_metric_value(candidate.get("humidity_pct"), suffix="%", digits=0),
                visibility=format_metric_value(candidate.get("visibility_km"), suffix=" km", digits=1),
                light_pollution=format_light_pollution_value(candidate),
                window=format_window_string(candidate),
                summary=item["summary"].replace("|", "/"),
            )
        )
    return "\n".join(rows)


def render_candidate_card(item: Dict[str, Any]) -> str:
    candidate = item["candidate"]
    breakdown = item["score_breakdown"]
    window_sources = format_window_source_entries(candidate, breakdown["moon"]["sources"])
    moon_note = "基于该来源推算" if moon_status_is_inferred(candidate) else None
    lines = [
        f"## {item['rank']}. {item['name']}",
        "",
        f"- 总分：`{item['total_score']:.1f}`",
        f"- 一句话判断：{item['summary']}",
        f"- 检索时间：`{candidate.get('retrieved_at_local') or '未知'}`",
        "",
        "### 观测窗口",
        f"- 观测日期/窗口：{format_window_string(candidate)}",
        render_source_line(window_sources),
        "",
        "### 天气明细",
        f"- 云量：{format_metric_value(candidate.get('cloud_cover_pct'), suffix='%', digits=0)}",
        f"- 湿度：{format_metric_value(candidate.get('humidity_pct'), suffix='%', digits=0)}",
        f"- 能见度：{format_metric_value(candidate.get('visibility_km'), suffix=' km', digits=1)}",
        f"- smoke_risk：{format_risk_value(candidate.get('smoke_risk_score'))}",
        f"- haze_risk：{format_risk_value(candidate.get('haze_risk_score'))}",
        f"- forecast_confidence：{format_confidence_value(candidate.get('forecast_confidence'))}",
        f"- 天气分：{breakdown['weather']['score']:.1f}",
        render_source_line(breakdown["weather"]["sources"]),
        "",
        "### 暗空明细",
        f"- 光污染：{format_light_pollution_value(candidate)}",
        f"- 海拔：{format_metric_value(candidate.get('elevation_m'), suffix=' m', digits=0)}",
        f"- city_glow_direction：{format_optional_text(candidate.get('city_glow_direction'))}",
        f"- city_glow_risk：{format_risk_value(candidate.get('city_glow_severity_score'))}",
        f"- 暗空分：{breakdown['darkness']['score']:.1f}",
        render_source_line(breakdown["darkness"]["sources"]),
        "",
        "### 月亮明细",
        f"- 观测日期：{format_observation_date(candidate)}",
        f"- 月落：{format_datetime_local(candidate.get('moonset_local'))}",
        f"- 月升：{format_datetime_local(candidate.get('moonrise_local'))}",
        f"- moon_window_status：{item['moon_window_status']}",
        f"- 月亮分：{breakdown['moon']['score']:.1f}",
        render_source_line(breakdown["moon"]["sources"], note=moon_note),
        "",
        "### 银河几何明细",
        f"- 银河核心高度：{format_metric_value(candidate.get('milky_way_core_altitude_deg'), suffix=' deg', digits=0)}",
        f"- 银河核心方位：{format_metric_value(candidate.get('milky_way_core_azimuth_deg'), suffix=' deg', digits=0)}",
        f"- 地平线开阔度/几何分：{format_metric_value(candidate.get('horizon_clearance_score'), digits=0)} / {breakdown['composition']['score']:.1f}",
        render_source_line(breakdown["composition"]["sources"]),
        "",
        "### 交通与安全明细",
        f"- 车程：{format_metric_value(candidate.get('drive_hours'), suffix=' h', digits=1)}",
        f"- access_score：{format_metric_value(candidate.get('access_score'), digits=0)}",
        f"- safety_score：{format_metric_value(candidate.get('safety_score'), digits=0)}",
        f"- parking_risk：{format_risk_value(candidate.get('parking_risk_score'))}",
        f"- walking_risk：{format_risk_value(candidate.get('walking_risk_score'))}",
        f"- 交通安全分：{breakdown['logistics']['score']:.1f}",
        render_source_line(breakdown["logistics"]["sources"]),
    ]
    if candidate.get("notes"):
        lines.extend(["", f"- 备注：{candidate['notes']}"])
    lines.extend(["", "### 简短结论", build_conclusion(item)])
    return "\n".join(lines)


def render_freshness_note(ranked: List[Dict[str, Any]], top_n: int) -> str:
    sampled = ranked[:top_n]
    realtime = 0
    invalid_weather = 0
    low_confidence = 0
    missing_field_candidates = 0
    for item in sampled:
        weather_kind = str(item["candidate"].get("weather_data_kind") or "").strip().lower()
        if weather_kind in ALLOWED_WEATHER_KINDS:
            realtime += 1
        else:
            invalid_weather += 1
        if item["confidence_status"] in {"low", "invalid"}:
            low_confidence += 1
        if item["missing_fields"]:
            missing_field_candidates += 1
    return "\n".join(
        [
            "## 数据新鲜度说明",
            "",
            f"- 实时/预报数据：本次 shortlist 中有 `{realtime}` 个候选使用实时、近实时或预报天气；云量、湿度、能见度和月亮时间都属于时敏数据。",
            f"- 静态基线数据：光污染与海拔用于长期基线判断，不代表当晚瞬时天空条件。",
            f"- 未解决不确定性：有 `{invalid_weather}` 个候选天气数据不合格，`{low_confidence}` 个候选置信度偏低或无效，`{missing_field_candidates}` 个候选仍缺关键字段。",
        ]
    )


def render_markdown(ranked: List[Dict[str, Any]], top_n: int) -> str:
    sections = [render_rank_table(ranked, top_n)]
    for item in ranked[:top_n]:
        sections.append(render_candidate_card(item))
    sections.append(render_freshness_note(ranked, top_n))
    return "\n\n".join(sections)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank Milky Way shooting sites from JSON.")
    parser.add_argument("input", help="JSON file path, or - to read from stdin.")
    parser.add_argument("--format", choices=["markdown", "json", "both"], default="markdown")
    parser.add_argument("--top", type=int, default=10, help="Maximum number of ranked results to print.")
    args = parser.parse_args()

    try:
        candidates, preferences = load_payload(args.input)
    except Exception as exc:
        print(f"Failed to load input: {exc}", file=sys.stderr)
        return 1

    if not candidates:
        print("No candidate sites found in input.", file=sys.stderr)
        return 1

    weights = normalize_weights(preferences)
    ranked = [score_candidate(candidate, preferences, weights) for candidate in candidates]
    ranked.sort(key=lambda item: item["total_score"], reverse=True)
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index

    markdown = render_markdown(ranked, args.top)
    structured = {
        "weights": weights,
        "preferences": preferences,
        "ranked_candidates": ranked[: args.top],
    }

    if args.format == "json":
        json.dump(structured, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    if args.format == "both":
        json.dump({"markdown": markdown, "structured": structured}, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    print(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
