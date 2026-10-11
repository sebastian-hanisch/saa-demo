"""L-Shaped-Verfahren (Benders-Zerlegung für zweistufige LP) mit Einzel- und Mehrfachschnitt.

Einheiten (je eine Regel, DEMO-PLAYBOOK §1b):
  stage2_batch   Kosten und Dualpreise der Kapazitäten für ALLE Szenarien bei festem Plan x (ein Block-LP)
  master_solve   Master-LP über x und die Schätzer theta der Stufe-2-Kosten, gegeben die bisherigen Schnitte
  l_shaped       die Schleife: Master lösen, Teilprobleme lösen, Schnitte ergänzen, bis die Schranken zusammenlaufen
Optimalitätsschnitt je Szenario s im Punkt xbar:  Q_s(x) >= Q_s(xbar) + m_s . (x - xbar), m_s = Dualpreise der Kapazitätszeilen
(<= 0: mehr Kapazität senkt die Kosten). Das Teilproblem hat vollständigen Recourse (Fehlmenge ist frei), es gibt keine Zulässigkeitsschnitte."""

import time
from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import block_diag, csr_matrix

import saa_algorithm as A
import saa_constants as C
from saa_scenario import Instance


def stage2_batch(inst: Instance, demand: np.ndarray, x: np.ndarray):
    """(q (S,), m (S, J)): Stufe-2-Kosten je Szenario und Dualpreise der Kapazitätszeilen (Ableitung nach x)."""
    s_count, j = demand.shape
    cost, a_cap, a_dem, upper = A.stage2_block(inst)
    nb = cost.size
    a_ub = block_diag([csr_matrix(a_cap)] * s_count)
    a_eq = block_diag([csr_matrix(a_dem)] * s_count)
    bounds = [(0.0, None if np.isinf(u) else float(u)) for u in upper] * s_count
    res = linprog(np.tile(cost, s_count), A_ub=a_ub, b_ub=np.tile(np.asarray(x, dtype=float), s_count),
                  A_eq=a_eq, b_eq=demand.reshape(-1), bounds=bounds, method="highs")
    if res.status != 0:
        raise RuntimeError(f"Teilproblem nicht lösbar: {res.message}")
    q = (res.x.reshape(s_count, nb) @ cost)
    return q, np.asarray(res.ineqlin.marginals).reshape(s_count, j)


def master_solve(inst: Instance, cuts_m: list, cuts_rhs: list, multicut: bool, s_count: int):
    """min c.x + (Mittel der theta) u. d. N. Budget und Schnitte; Rückgabe (x, Zielwert = untere Schranke).

    Schnitt der Form  m . x - theta_k <= rhs  (Einzelschnitt: ein theta; Mehrfachschnitt: ein theta_s je Szenario)."""
    j = inst.n
    n_theta = s_count if multicut else 1
    nvar = j + n_theta
    c = np.concatenate([np.full(j, inst.cap_cost), np.full(n_theta, 1.0 / s_count if multicut else 1.0)])
    rows, rhs = [], []
    budget = np.zeros(nvar)
    budget[:j] = 1.0
    rows.append(budget)
    rhs.append(inst.budget)
    for (k, m), r in zip(cuts_m, cuts_rhs):
        row = np.zeros(nvar)
        row[:j] = m
        row[j + (k if multicut else 0)] = -1.0
        rows.append(row)
        rhs.append(r)
    res = linprog(c, A_ub=np.array(rows), b_ub=np.array(rhs), bounds=[(0, None)] * nvar, method="highs")
    if res.status != 0:
        raise RuntimeError(f"Master nicht lösbar: {res.message}")
    return res.x[:j], float(res.fun)


@dataclass(frozen=True)
class LShapedResult:
    x: tuple[float, ...]
    objective: float
    iterations: int
    cuts: int
    seconds: float
    history: tuple[tuple[float, float], ...]   # (untere, obere Schranke) je Iteration
    converged: bool


def l_shaped(inst: Instance, demand: np.ndarray, multicut: bool, tol: float = C.LSHAPED_TOL,
             max_iter: int = C.LSHAPED_MAX_ITER, x0: np.ndarray | None = None) -> LShapedResult:
    """Startpunkt: Plan für die mittlere Nachfrage (`x0`), sonst derselbe berechnet."""
    t0 = time.perf_counter()
    s_count = demand.shape[0]
    w = 1.0 / s_count
    x = A.expected_value_plan(inst, demand) if x0 is None else np.asarray(x0, dtype=float)
    cuts_m, cuts_rhs, history = [], [], []
    best_upper = np.inf
    best_x = x
    lower = -np.inf
    converged = False
    for it in range(1, max_iter + 1):
        q, m = stage2_batch(inst, demand, x)
        upper = inst.cap_cost * float(x.sum()) + w * float(q.sum())
        if upper < best_upper:
            best_upper, best_x = upper, x.copy()
        if multicut:
            for s in range(s_count):
                cuts_m.append((s, m[s]))
                cuts_rhs.append(float(m[s] @ x - q[s]))
        else:
            m_bar = w * m.sum(axis=0)
            q_bar = w * float(q.sum())
            cuts_m.append((0, m_bar))
            cuts_rhs.append(float(m_bar @ x - q_bar))
        x_new, lower = master_solve(inst, cuts_m, cuts_rhs, multicut, s_count)
        history.append((lower, best_upper))
        if best_upper - lower <= tol * max(abs(best_upper), 1.0):
            converged = True
            break
        x = x_new
    return LShapedResult(tuple(float(v) for v in best_x), float(best_upper), len(history), len(cuts_rhs),
                         time.perf_counter() - t0, tuple(history), converged)
