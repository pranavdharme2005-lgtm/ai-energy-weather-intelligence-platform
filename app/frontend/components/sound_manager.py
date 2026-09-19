"""
Sound Alert Manager for Energy Control Room UI.

Provides browser-safe audio alerts for CRITICAL and HIGH severity energy events.
Sound defaults to OFF to comply with browser autoplay security policies and can be toggled by the operator.
"""

import streamlit as st


def render_sound_controls():
    """Renders sound toggle controls in the Streamlit sidebar/toolbar."""
    if "sound_enabled" not in st.session_state:
        st.session_state["sound_enabled"] = False
    if "sound_volume" not in st.session_state:
        st.session_state["sound_volume"] = 0.8

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔊 Audio Alerts")
    
    sound_on = st.sidebar.checkbox("Enable Alert Audio", value=st.session_state.get("sound_enabled", False))
    st.session_state["sound_enabled"] = sound_on
    
    if sound_on:
        st.session_state["sound_volume"] = st.sidebar.slider(
            "Volume", min_value=0.1, max_value=1.0, value=st.session_state.get("sound_volume", 0.8), step=0.1
        )
        st.sidebar.caption("🔊 Audio alerts active for HIGH & CRITICAL events.")
    else:
        st.sidebar.caption("🔇 Audio muted. Enable to hear critical alert tones.")


def trigger_alert_sound(severity: str, alert_id: str = None):
    """
    Triggers an HTML5 browser audio tone if sound is enabled and alert severity is HIGH or CRITICAL.
    Uses session state deduplication to prevent repetitive sounds for the same alert.
    """
    if not st.session_state.get("sound_enabled", False):
        return

    sev_upper = (severity or "").upper()
    if sev_upper not in ["HIGH", "CRITICAL"]:
        return

    # Deduplicate played alerts using session state fingerprint set
    if "played_alerts" not in st.session_state:
        st.session_state["played_alerts"] = set()

    played = st.session_state["played_alerts"]
    if alert_id and alert_id in played:
        return

    if alert_id:
        played.add(alert_id)
        st.session_state["played_alerts"] = played

    # Clean web audio synthesizer via inline JS/HTML5 Audio
    vol = st.session_state.get("sound_volume", 0.8)
    freq = 880 if sev_upper == "CRITICAL" else 587.33  # High A note or D note
    
    audio_js = f"""
    <script>
    (function() {{
        try {{
            var AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            var ctx = new AudioContext();
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            
            osc.type = '{ 'sawtooth' if sev_upper == 'CRITICAL' else 'sine' }';
            osc.frequency.setValueAtTime({freq}, ctx.currentTime);
            
            gain.gain.setValueAtTime({vol}, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);
            
            osc.connect(gain);
            gain.connect(ctx.destination);
            
            osc.start();
            osc.stop(ctx.currentTime + 0.8);
        }} catch(e) {{
            console.log('Audio autoplay prevented or unsupported');
        }}
    }})();
    </script>
    """
    st.components.v1.html(audio_js, height=0)
