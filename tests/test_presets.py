"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen; Permalink begrenzt und rastet ein."""

import pytest

import saa_constants as C
import saa_evaluation as ev
import saa_presets as P


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_inside_the_bounds_and_on_the_step_grid():
    for name, preset in C.PRESETS.items():
        for key, state_key in P.PRESET_KEYS.items():
            spec = P.SETTING_SPECS[state_key]
            value = preset[key]
            if spec.choices is not None:
                assert value in spec.choices, (name, key)
            else:
                assert spec.lo <= value <= spec.hi, (name, key)
                assert P.snap(spec, value) == pytest.approx(value), (name, key)


def test_default_preset_equals_the_default_settings():
    assert ev.Settings(**C.PRESETS["Standardfall (Voreinstellung)"]) == ev.Settings()


def test_setting_specs_cover_every_preset_key():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)


def test_snap_clamps_and_rounds_to_the_step():
    assert P.snap(P.SETTING_SPECS["s_slider"], 999) == C.S_MAX
    assert P.snap(P.SETTING_SPECS["s_slider"], 13) == 15
    assert P.snap(P.SETTING_SPECS["sigma_slider"], 0.3567) == pytest.approx(0.35)
    assert P.snap(P.SETTING_SPECS["transfer_radio"], "vielleicht") == C.DEFAULT_TRANSFER


def test_experiment_sizes_stay_below_the_reference():
    assert max(C.SWEEP_S) < C.REF_SCENARIOS and max(C.LSHAPED_SIZES) <= C.S_MAX
    assert C.S_MIN <= min(C.SWEEP_S)
