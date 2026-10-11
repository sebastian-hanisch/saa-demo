"""Permalink (Begrenzen, Einrasten), Presets und Zufalls-Seed-Buttons (Standardmuster aus dem Demo-Portfolio)."""

import random
from dataclasses import dataclass

import streamlit as st

import saa_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: type
    default: object
    lo: float | None = None
    hi: float | None = None
    step: float | None = None
    choices: tuple | None = None


SETTING_SPECS = {
    "s_slider": SettingSpec("s", int, C.DEFAULT_S, C.S_MIN, C.S_MAX, C.S_STEP),
    "sigma_slider": SettingSpec("sigma", float, C.DEFAULT_SIGMA, C.SIGMA_MIN, C.SIGMA_MAX, C.SIGMA_STEP),
    "budget_slider": SettingSpec("budget", float, C.DEFAULT_BUDGET, C.BUDGET_MIN, C.BUDGET_MAX, C.BUDGET_STEP),
    "transfer_radio": SettingSpec("transfer", str, C.DEFAULT_TRANSFER, choices=C.TRANSFER_CHOICES),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
    "draw_input": SettingSpec("draw", int, C.DEFAULT_DRAW, 0, C.DRAW_MAX),
}
PRESET_KEYS = {
    "s": "s_slider", "sigma": "sigma_slider", "budget": "budget_slider",
    "transfer": "transfer_radio", "seed": "seed_input", "draw": "draw_input",
}


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def snap(spec: SettingSpec, value):
    """Auf die Reglergrenzen begrenzen und auf den Schritt einrasten (Rundungsrauschen der Float-Schritte entfernen)."""
    if spec.choices is not None:
        return value if value in spec.choices else spec.default
    if spec.lo is not None:
        value = max(spec.lo, value)
    if spec.hi is not None:
        value = min(spec.hi, value)
    if spec.step is not None:
        snapped = spec.lo + round((value - spec.lo) / spec.step) * spec.step
        value = round(snapped, 6) if spec.caster is float else int(round(snapped))
    return value


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen, begrenzt und eingerastet."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            raw = qp[spec.url_param]
            if isinstance(raw, list):
                raw = raw[0] if raw else ""
            try:
                value = spec.caster(raw)
            except (ValueError, TypeError):
                continue
            st.session_state[state_key] = snap(spec, value)
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}; die Adresszeile spiegelt die Konfiguration."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        if key in C.PRESETS[name]:
            st.session_state[state_key] = C.PRESETS[name][key]


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)


def new_draw():
    st.session_state["draw_input"] = random.randint(0, C.DRAW_MAX)
