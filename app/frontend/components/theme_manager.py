"""
Weather-Reactive Theme Manager for Energy Control Room.

Dynamically computes and applies CSS color schemes, card styling, header accents,
and plot themes based on actual meteorological conditions and current local time.
"""

from datetime import datetime
from typing import Dict, Any


def get_dynamic_theme(weather_condition: str = "Clear", timestamp: str = None) -> Dict[str, Any]:
    """
    Derives theme properties based on actual weather condition and time of day.
    
    Theme States:
    - NIGHT: Evening/night time (19:00 - 06:00)
    - STORM: Heavy rain, thunderstorm, extreme weather
    - RAIN: Light/moderate rain, drizzle, shower
    - CLOUDY: Clouds, overcast, mist, fog
    - CLEAR: Sun, clear sky (default daytime)
    """
    cond_lower = (weather_condition or "").lower()
    
    # Determine if night time based on timestamp or local hour
    is_night = False
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            is_night = dt.hour >= 19 or dt.hour < 6
        except Exception:
            pass
    if not timestamp:
        current_hour = datetime.now().hour
        is_night = current_hour >= 19 or current_hour < 6

    if is_night:
        theme_name = "NIGHT"
        bg_color = "#0B0F19"
        card_bg = "#111827"
        border_color = "#1F2937"
        text_color = "#F3F4F6"
        accent_color = "#3B82F6"
        header_gradient = "linear-gradient(135deg, #1E293B 0%, #0F172A 100%)"
        status_badge = "🌙 Night Monitoring Active"
    elif "storm" in cond_lower or "thunder" in cond_lower or "heavy" in cond_lower or "extreme" in cond_lower:
        theme_name = "STORM"
        bg_color = "#0F172A"
        card_bg = "#1E1B4B"
        border_color = "#4338CA"
        text_color = "#F8FAFC"
        accent_color = "#818CF8"
        header_gradient = "linear-gradient(135deg, #312E81 0%, #1E1B4B 100%)"
        status_badge = "⚡ Extreme Weather Advisory"
    elif "rain" in cond_lower or "drizzle" in cond_lower or "shower" in cond_lower:
        theme_name = "RAIN"
        bg_color = "#0E1A2B"
        card_bg = "#172A46"
        border_color = "#1E3A8A"
        text_color = "#E0F2FE"
        accent_color = "#0284C7"
        header_gradient = "linear-gradient(135deg, #1E3A8A 0%, #0F172A 100%)"
        status_badge = "🌧️ Precipitation Alert Mode"
    elif "cloud" in cond_lower or "overcast" in cond_lower or "fog" in cond_lower or "mist" in cond_lower:
        theme_name = "CLOUDY"
        bg_color = "#111827"
        card_bg = "#1F2937"
        border_color = "#374151"
        text_color = "#F9FAFB"
        accent_color = "#9CA3AF"
        header_gradient = "linear-gradient(135deg, #374151 0%, #1F2937 100%)"
        status_badge = "☁️ Overcast Conditions"
    else:
        theme_name = "CLEAR"
        bg_color = "#0F172A"
        card_bg = "#1E293B"
        border_color = "#334155"
        text_color = "#F8FAFC"
        accent_color = "#38BDF8"
        header_gradient = "linear-gradient(135deg, #0284C7 0%, #0369A1 100%)"
        status_badge = "☀️ Clear Operations"

    return {
        "name": theme_name,
        "bg_color": bg_color,
        "card_bg": card_bg,
        "border_color": border_color,
        "text_color": text_color,
        "accent_color": accent_color,
        "header_gradient": header_gradient,
        "status_badge": status_badge
    }


def generate_theme_css(theme: Dict[str, Any]) -> str:
    """Generates dynamic CSS string to inject into Streamlit."""
    return f"""
    <style>
    .stApp {{
        background-color: {theme['bg_color']} !important;
        color: {theme['text_color']} !important;
    }}
    .control-room-header {{
        background: {theme['header_gradient']};
        padding: 18px 24px;
        border-radius: 12px;
        border: 1px solid {theme['border_color']};
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }}
    .kpi-card {{
        background-color: {theme['card_bg']};
        border: 1px solid {theme['border_color']};
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }}
    .kpi-title {{
        color: #9CA3AF;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .kpi-value {{
        color: {theme['text_color']};
        font-size: 1.8rem;
        font-weight: 700;
        margin: 4px 0;
    }}
    .kpi-unit {{
        color: {theme['accent_color']};
        font-size: 0.9rem;
        font-weight: 500;
    }}
    .kpi-subtext {{
        color: #6B7280;
        font-size: 0.75rem;
    }}
    .status-pill {{
        display: inline-block;
        background-color: {theme['border_color']};
        color: {theme['accent_color']};
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }}
    </style>
    """
