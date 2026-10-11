"""Orakel-Tests (DEMO-PLAYBOOK §12): anderer Rechenweg als der Kern.

1. Dasselbe zweistufige Modell als eigenes LP in OR-Tools (GLOP, Schleifen statt Blockmatrizen) für die SAA-Pläne.
2. Ein Standort ohne Zukaufgrenze und mit großer Fehlmenge-Strafe: der SAA-Plan ist das empirische Quantil (sortieren statt LP).
3. L-Shaped (eigene Implementierung der Zerlegung) gegen die erweiterte Form und gegen GLOP.
4. Jensen: der mittlere Optimalwert der Stichproben liegt unter dem besten Plan der Verteilung, exakt, weil die Verteilung diskret bekannt ist."""

import dataclasses

import numpy as np
import pytest

import saa_algorithm as A
import saa_evaluation as ev
import saa_lshaped as L
import saa_scenario as S
from saa_scenario import Instance

pywraplp = pytest.importorskip("ortools.linear_solver.pywraplp")


def _glop_value(inst: Instance, demand: np.ndarray) -> float:
    j_count, s_count = inst.n, demand.shape[0]
    solver = pywraplp.Solver.CreateSolver("GLOP")
    inf = solver.infinity()
    x = [solver.NumVar(0, inf, f"x{j}") for j in range(j_count)]
    obj = solver.Objective()
    solver.Add(sum(x) <= inst.budget)
    for j in range(j_count):
        obj.SetCoefficient(x[j], inst.cap_cost)
    for s in range(s_count):
        y = {}
        for j in range(j_count):
            for k in range(j_count):
                y[j, k] = solver.NumVar(0, inf if (inst.transfer or j == k) else 0.0, f"y{s}_{j}_{k}")
                obj.SetCoefficient(y[j, k], inst.transfer_cost[j][k] / s_count)
        for k in range(j_count):
            u = solver.NumVar(0, inst.spot_limit[k], f"u{s}_{k}")
            w = solver.NumVar(0, inf, f"w{s}_{k}")
            obj.SetCoefficient(u, inst.spot[k] / s_count)
            obj.SetCoefficient(w, inst.unmet / s_count)
            solver.Add(sum(y[j, k] for j in range(j_count)) + u + w == float(demand[s, k]))
        for j in range(j_count):
            solver.Add(sum(y[j, k] for k in range(j_count)) <= x[j])
    obj.SetMinimization()
    assert solver.Solve() == pywraplp.Solver.OPTIMAL
    return obj.Value()


@pytest.mark.parametrize("transfer", [True, False])
def test_saa_plan_value_matches_independent_glop_model(transfer):
    inst = dataclasses.replace(
        S.make_instance(31, sigma=0.4, rho=0.4, budget_ratio=0.9, spot_mult=1.6, transfer=transfer),
        mu=(80.0, 120.0, 100.0), spot=(1.7, 1.5, 1.9), spot_limit=(40.0, 60.0, 50.0),
        transfer_cost=((0.0, 0.3, 0.5), (0.3, 0.0, 0.4), (0.5, 0.4, 0.0)), budget=270.0,
    )
    ref = ev.reference(inst)
    for seed in (1, 2, 3):
        sample = ev.sample_scenarios(ref.demand, seed, 9)
        value, _ = A.solve_grouped(inst, sample, np.zeros(9, dtype=int))
        assert value == pytest.approx(_glop_value(inst, sample), rel=1e-7)


def test_l_shaped_matches_glop_and_extensive_form():
    inst = S.make_instance(13, sigma=0.35, rho=0.4, budget_ratio=0.95, spot_mult=1.9, transfer=True)
    ref = ev.reference(inst)
    sample = ev.sample_scenarios(ref.demand, 4, 15)
    glop = _glop_value(inst, sample)
    ext, _ = A.solve_grouped(inst, sample, np.zeros(15, dtype=int))
    assert ext == pytest.approx(glop, rel=1e-7)
    for multicut in (False, True):
        res = L.l_shaped(inst, sample, multicut)
        assert res.converged
        assert res.objective == pytest.approx(glop, rel=1e-5)


def test_single_location_saa_plan_is_the_empirical_quantile():
    # ohne Zukaufgrenze und mit sehr hoher Fehlmenge-Strafe: x* = kleinstes x mit F_S(x) >= (s - c) / s
    spot = 1.9
    inst = Instance(
        mu=(100.0,), cap_cost=1.0, spot=(spot,), unmet=1e4, spot_limit=(1e9,), transfer_cost=((0.0,),),
        transfer=True, budget=1e9, sigma=0.35, rho=0.0,
    )
    demand, _ = S.demand_scenarios(inst, 5, count=61)
    value, x = A.solve_grouped(inst, demand, np.zeros(61, dtype=int))
    d = np.sort(demand[:, 0])
    k = int(np.ceil(61 * (spot - 1.0) / spot))   # Ordnungsstatistik Nummer k
    assert x[0, 0] == pytest.approx(d[k - 1], rel=1e-7)
    # Kosten des Quantils von Hand: c x + s mean((D - x)+)
    assert value == pytest.approx(x[0, 0] + spot * np.mean(np.maximum(d - x[0, 0], 0.0)), rel=1e-7)


def test_jensen_mean_optimal_value_lies_below_the_best_plan_of_the_distribution():
    settings = ev.Settings()
    ref = ev.reference(ev.build_instance(settings))
    zs = [ev.one_draw(ref, 10, ev.draw_seed(2, k, 10)).z for k in range(60)]
    se = np.std(zs, ddof=1) / np.sqrt(len(zs))
    assert np.mean(zs) <= ref.f_star + 2.0 * se   # E[z] <= f*: bis auf Rauschen von zwei Standardfehlern
    # und jedes einzelne z liegt unter den Kosten desselben Plans auf derselben Stichprobe, f_S(x*) >= z
    d = ev.one_draw(ref, 10, ev.draw_seed(2, 0, 10))
    assert d.f_sample_star >= d.z - 1e-9
