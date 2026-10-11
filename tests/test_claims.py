"""Jede Aussage aus README und App-Text wird hier nachgerechnet (Bänder statt exakter Werte: CI installiert die neuesten numpy/scipy;
die Mittel über 24 Ziehungen tragen einen Stichprobenfehler, geprüft werden Ordnung, Größenordnung und Struktur)."""

import numpy as np
import pytest

import saa_constants as C
import saa_evaluation as ev


@pytest.fixture(scope="module")
def runs():
    out = {}
    for name in ("Standardfall (Voreinstellung)", "Ohne Umlagerung, knappes Budget", "Hohe Streuung, weites Budget"):
        settings = ev.Settings(**C.PRESETS[name])
        rows = ev.experiment(settings)
        out[name] = {r["s"]: r for r in rows}
    return out


@pytest.fixture(scope="module")
def standard(runs):
    return runs["Standardfall (Voreinstellung)"]


def test_the_default_draw_shows_a_wobbling_plan_and_a_misleading_optimal_value():
    s = ev.Settings()
    ref = ev.reference(ev.build_instance(s))
    d = ev.one_draw(ref, s.s, ev.draw_seed(s.draw, 0, s.s))
    assert ev.verdict_of(d) == "plan_wackelt_kosten_kaum"
    assert d.gap_pct < 1.0 and d.plan_dev_pct >= 5.0
    assert abs(d.z_error_pct) >= 5.0            # der Optimalwert der Stichprobe liegt mehr als 5 % daneben


def test_the_gap_shrinks_roughly_like_one_over_s(standard):
    assert 0.4 <= standard[5]["gap"] <= 1.6
    assert standard[100]["gap"] <= 0.25
    assert standard[5]["gap"] >= 4 * standard[100]["gap"]


def test_the_paired_optimism_tracks_the_gap(standard):
    for s in (10, 20, 50, 100):
        ratio = standard[s]["bias"] / standard[s]["gap"]
        assert 0.4 <= ratio <= 2.5, (s, ratio)


def test_the_gap_is_skewed_median_below_mean_for_small_samples(standard):
    for s in (5, 10, 20):
        assert standard[s]["gap_median"] <= standard[s]["gap"]


def test_the_in_sample_optimal_value_scatters_more_than_it_is_biased(standard):
    assert standard[5]["z_sd"] >= 10.0
    assert standard[100]["z_sd"] <= 6.0
    assert standard[5]["z_sd"] > 4 * standard[5]["bias"]


def test_the_plan_moves_more_than_its_cost(standard):
    r = standard[20]
    assert r["plan_dev"] >= 5.0 and r["gap_median"] <= 1.0
    assert standard[5]["plan_dev"] >= 2 * standard[100]["plan_dev"]


def test_how_many_scenarios_are_needed_depends_on_the_setting(runs):
    needs = {n: ev.smallest_s_for_gap(sorted(r.values(), key=lambda x: x["s"])) for n, r in runs.items()}
    default, no_transfer, high = (needs["Standardfall (Voreinstellung)"], needs["Ohne Umlagerung, knappes Budget"], needs["Hohe Streuung, weites Budget"])
    assert default <= no_transfer <= high
    assert default == 5
    assert no_transfer in (10, 20)
    assert high in (20, 50)


def test_every_gap_and_bias_is_non_negative(runs):
    for rows in runs.values():
        for r in rows.values():
            assert r["gap"] >= 0 and r["bias"] >= 0 and min(r["gap_all"]) >= -1e-9


def test_l_shaped_multicut_needs_few_iterations_but_many_cuts():
    cmp_ = ev.lshaped_comparison(ev.Settings(), 100)
    single, multi = cmp_["single"], cmp_["multi"]
    assert single.converged and multi.converged
    assert single.objective == pytest.approx(cmp_["extensive"], rel=1e-5)
    assert multi.objective == pytest.approx(cmp_["extensive"], rel=1e-5)
    assert single.iterations >= 4 * multi.iterations
    assert multi.cuts >= 5 * single.cuts
    assert cmp_["t_extensive"] < multi.seconds     # die erweiterte Form ist hier der schnellste Weg
    assert cmp_["t_extensive"] < single.seconds
