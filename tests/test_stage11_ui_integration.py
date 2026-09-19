"""
Stage 11 — Advanced Dynamic UI & Control Room Integration Tests.

Validates:
1. Dynamic theme engine state calculations (CLEAR, CLOUDY, RAIN, STORM, NIGHT).
2. Web audio alert sound manager trigger conditions.
3. Headless rendering of all 10 Streamlit Control Room pages.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.database.session import init_db
from app.frontend.components.theme_manager import get_dynamic_theme, generate_theme_css
from app.frontend.components.sound_manager import trigger_alert_sound
from app.frontend.pages import (
    overview,
    live_energy,
    forecast,
    rain_prediction,
    anomaly_center,
    smart_alerts,
    simulator,
    ai_analyst,
    weather_impact,
    data_quality,
    settings_page
)


def test_dynamic_theme_generator():
    """Verify get_dynamic_theme computes correct theme states based on condition and time."""
    # Clear daytime
    t_clear = get_dynamic_theme(weather_condition="Clear", timestamp="2026-09-19T12:00:00")
    assert t_clear["name"] == "CLEAR"

    # Rain
    t_rain = get_dynamic_theme(weather_condition="Light Rain", timestamp="2026-09-19T14:00:00")
    assert t_rain["name"] == "RAIN"

    # Thunderstorm
    t_storm = get_dynamic_theme(weather_condition="Heavy Thunderstorm", timestamp="2026-09-19T14:00:00")
    assert t_storm["name"] == "STORM"

    # Overcast / Cloud
    t_cloud = get_dynamic_theme(weather_condition="Overcast Cloud", timestamp="2026-09-19T14:00:00")
    assert t_cloud["name"] == "CLOUDY"

    # Nighttime (22:00)
    t_night = get_dynamic_theme(weather_condition="Clear", timestamp="2026-09-19T22:00:00")
    assert t_night["name"] == "NIGHT"

    # CSS string generation check
    css = generate_theme_css(t_clear)
    assert "<style>" in css
    assert t_clear["bg_color"] in css


def test_sound_manager_trigger():
    """Verify sound manager respects severity filters and session deduplication."""
    mock_session = {"sound_enabled": True, "sound_volume": 0.8, "played_alerts": set()}
    with patch("streamlit.session_state", mock_session), \
         patch("streamlit.components.v1.html") as mock_html:

        # Low severity -> no sound
        trigger_alert_sound("LOW", alert_id="alt_1")
        mock_html.assert_not_called()

        # HIGH severity -> triggers sound
        trigger_alert_sound("HIGH", alert_id="alt_2")
        mock_html.assert_called_once()
        assert "alt_2" in mock_session["played_alerts"]

        # Duplicate alert_id -> no repeat sound
        mock_html.reset_mock()
        trigger_alert_sound("HIGH", alert_id="alt_2")
        mock_html.assert_not_called()


@patch("streamlit.session_state", {"current_region": "Region-North", "current_location": "London"})
@patch("streamlit.tabs")
@patch("streamlit.markdown")
@patch("streamlit.plotly_chart")
@patch("streamlit.columns")
@patch("streamlit.metric")
def test_all_pages_render_without_exception(mock_metric, mock_cols, mock_chart, mock_markdown, mock_tabs):
    """Verify that all 10 Control Room pages render cleanly without throwing exceptions."""
    init_db()
    mock_cols.side_effect = lambda n: [MagicMock() for _ in range(n if isinstance(n, int) else len(n))]
    mock_tabs.side_effect = lambda tabs_list: [MagicMock() for _ in tabs_list]

    pages = [
        overview,
        live_energy,
        forecast,
        rain_prediction,
        anomaly_center,
        smart_alerts,
        simulator,
        ai_analyst,
        weather_impact,
        data_quality,
        settings_page
    ]

    for p in pages:
        try:
            p.render()
        except Exception as e:
            pytest.fail(f"Page {p.__name__} failed to render: {str(e)}")
