"""Einheiten: Stichprobe, Ziehung gegen Referenz, L-Shaped-Teile an der Mini-Instanz (zwei Standorte), von Hand gerechnet."""

import numpy as np
import pytest

import saa_algorithm as A
import saa_constants as C
import saa_evaluation as ev
import saa_lshaped as L


def test_sample_scenarios_are_deterministic_rows_of_the_reference():
    demand = np.arange(30, dtype=float).reshape(10, 3)
    a = ev.sample_scenarios(demand, seed=5, s=7)
    b = ev.sample_scenarios(demand, seed=5, s=7)
    assert np.array_equal(a, b) and a.shape == (7, 3)
    assert all(any(np.array_equal(row, ref_row) for ref_row in demand) for row in a)
    assert not np.array_equal(a, ev.sample_scenarios(demand, seed=6, s=7))


def test_draw_seeds_are_distinct_across_draws_repetitions_and_sizes():
    seeds = {ev.draw_seed(b, k, s) for b in range(5) for k in range(5) for s in (5, 10, 20)}
    assert len(seeds) == 75 and C.REF_SEED not in seeds


def test_stage2_batch_hand_values(mini, mini_no_transfer):
    d = np.array([[100.0, 50.0]])
    q, m = L.stage2_batch(mini, d, np.array([80.0, 80.0]))
    # Standort 2 hat 30 Einheiten übrig und gibt 20 an Standort 1 ab (0,5 je Einheit): Stufe 2 kostet 10.
    # Eine Einheit mehr bei Standort 1 ersetzt eine Umlagerung und spart 0,5; bei Standort 2 ändert mehr Kapazität nichts.
    assert q[0] == pytest.approx(10.0)
    assert m[0, 0] == pytest.approx(-0.5)
    assert m[0, 1] == pytest.approx(0.0)
    q2, m2 = L.stage2_batch(mini_no_transfer, d, np.array([80.0, 80.0]))
    # ohne Umlagerung 20 Einheiten Zukauf zu 2; mehr Kapazität bei Standort 1 spart 2 je Einheit
    assert q2[0] == pytest.approx(40.0)
    assert m2[0, 0] == pytest.approx(-2.0)
    assert m2[0, 1] == pytest.approx(0.0)


def test_duals_are_the_derivative_of_the_stage2_cost(mini):
    d = np.array([[100.0, 50.0], [70.0, 90.0]])
    x = np.array([65.0, 55.0])   # kein Knickpunkt: sonst ist der Dualpreis nur ein Subgradient
    q, m = L.stage2_batch(mini, d, x)
    for j in range(2):
        xp = x.copy()
        xp[j] += 0.01
        qp, _ = L.stage2_batch(mini, d, xp)
        assert (qp - q) / 0.01 == pytest.approx(m[:, j], abs=1e-6)


@pytest.mark.parametrize("multicut", [False, True])
def test_l_shaped_reaches_the_extensive_form_optimum(mini, multicut):
    d = np.array([[100.0, 50.0], [70.0, 90.0], [120.0, 40.0], [60.0, 60.0]])
    ext, _ = A.solve_grouped(mini, d, np.zeros(4, dtype=int))
    res = L.l_shaped(mini, d, multicut=multicut)
    assert res.converged
    assert res.objective == pytest.approx(ext, rel=1e-5)
    lo, up = res.history[-1]
    assert lo <= up + 1e-9


def test_multicut_needs_fewer_iterations_and_more_cuts(mini):
    d = np.array([[100.0, 50.0], [70.0, 90.0], [120.0, 40.0], [60.0, 60.0], [90.0, 30.0], [50.0, 80.0]])
    single, multi = L.l_shaped(mini, d, False), L.l_shaped(mini, d, True)
    assert multi.iterations <= single.iterations
    assert multi.cuts == multi.iterations * len(d) and single.cuts == single.iterations


def test_lower_bounds_never_exceed_the_upper_bounds(mini):
    d = np.array([[100.0, 50.0], [70.0, 90.0], [120.0, 40.0]])
    for multi in (False, True):
        res = L.l_shaped(mini, d, multi)
        assert all(lo <= up + 1e-7 for lo, up in res.history)


def test_one_draw_invariants_gap_and_bias_are_nonnegative():
    settings = ev.Settings()
    ref = ev.reference(ev.build_instance(settings))
    for k in range(6):
        d = ev.one_draw(ref, 10, ev.draw_seed(1, k, 10))
        assert d.gap_pct >= -1e-9
        assert d.bias_pct >= -1e-9
        assert d.f_true >= ref.f_star - 1e-6
        assert d.z <= d.f_sample_star + 1e-6


def test_the_full_reference_sample_has_no_gap():
    # S = REF_SCENARIOS mit allen Szenarien genau einmal: derselbe Plan wie der Referenzplan, Lücke und Bias 0
    inst = ev.build_instance(ev.Settings())
    ref = ev.reference(inst)
    z, x = A.solve_grouped(inst, ref.demand, np.zeros(len(ref.demand), dtype=int))
    assert z == pytest.approx(ref.f_star)
    assert np.allclose(x[0], ref.x_star)
