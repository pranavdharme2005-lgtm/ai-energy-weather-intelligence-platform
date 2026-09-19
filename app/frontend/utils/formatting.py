"""
Formatting and Display Standardizer for Energy Control Room UI.

Provides consistent formatting functions for energy units (MW), temperatures (°C),
percentages (%), pressure (hPa), timestamps, and status badges across all UI components.
"""

from datetime import datetime
from typing import Union, Optional


def format_mw(val: Union[int, float, None], decimals: int = 1) -> str:
    """Format energy demand value in Megawatts (MW) with comma thousands separator."""
    if val is None:
        return "N/A"
    try:
        val_float = float(val)
        return f"{val_float:,.{decimals}f} MW"
    except (ValueError, TypeError):
        return "N/A"


def format_temp(val: Union[int, float, None], decimals: int = 1) -> str:
    """Format temperature in degrees Celsius (°C)."""
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.{decimals}f} °C"
    except (ValueError, TypeError):
        return "N/A"


def format_percent(val: Union[int, float, None], decimals: int = 1) -> str:
    """Format percentage value (%)."""
    if val is None:
        return "N/A"
    try:
        val_float = float(val)
        # Handle decimal percentages (0.85 -> 85%) vs whole percentages (85 -> 85%)
        if 0.0 <= val_float <= 1.0 and decimals == 1:
            val_float = val_float * 100.0
        return f"{val_float:.{decimals}f}%"
    except (ValueError, TypeError):
        return "N/A"


def format_pressure(val: Union[int, float, None]) -> str:
    """Format atmospheric pressure in hectopascals (hPa)."""
    if val is None:
        return "N/A"
    try:
        return f"{float(val):,.1f} hPa"
    except (ValueError, TypeError):
        return "N/A"


def format_wind_speed(val: Union[int, float, None]) -> str:
    """Format wind speed in meters per second (m/s)."""
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.1f} m/s"
    except (ValueError, TypeError):
        return "N/A"


def format_precipitation(val: Union[int, float, None]) -> str:
    """Format precipitation in millimeters (mm)."""
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.1f} mm"
    except (ValueError, TypeError):
        return "N/A"


def format_timestamp(ts: Union[datetime, str, None], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Standardize timestamp representation."""
    if ts is None:
        return "N/A"
    if isinstance(ts, datetime):
        return ts.strftime(fmt)
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.strftime(fmt)
    except Exception:
        return str(ts)


def format_status_badge(status: str) -> str:
    """Returns a visual badge representation for system or alert status."""
    status_upper = str(status).upper()
    badges = {
        "ONLINE": "🟢 ONLINE",
        "HEALTHY": "🟢 HEALTHY",
        "ACTIVE": "🔴 ACTIVE",
        "ACKNOWLEDGED": "🟡 ACKNOWLEDGED",
        "RESOLVED": "🟢 RESOLVED",
        "DEGRADED": "🟠 DEGRADED",
        "UNAVAILABLE": "🔴 UNAVAILABLE",
        "CRITICAL": "🔴 CRITICAL",
        "HIGH": "🟠 HIGH",
        "MEDIUM": "🟡 MEDIUM",
        "LOW": "🔵 LOW",
    }
    return badges.get(status_upper, f"⚪ {status_upper}")
