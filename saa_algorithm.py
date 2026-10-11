"""Kern: zweistufiges Kapazitätsproblem als LP, getrennt nach Informationsstand (HiGHS über scipy).

Einheiten (je eine Regel, DEMO-PLAYBOOK §1b):
  stage2_block        Nebenbedingungen und Kosten EINES Szenarios nach der Nachfrage (Flüsse, Zukauf, Fehlmenge)
  solve_grouped       ein LP für eine Informationsstruktur: Szenarien einer Gruppe teilen sich EINEN Plan x
  expected_value_plan Plan für die mittlere Nachfrage
  analyse_information Erwartungswert-Plan, Plan unter Unsicherheit, Teilinformation, Hellseher
Gruppen: alle Szenarien in einer Gruppe = Plan unter Unsicherheit (RP); jede in eigener Gruppe = Hellseher (WS);
Gruppen nach Stufen von z0 = Teilinformation."""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import block_diag, coo_matrix, csr_matrix, hstack, vstack

import saa_constants as C
from saa_scenario import Instance


def stage2_block(inst: Instance):
    """(cost, A_cap, A_dem, upper): Variablen je Szenario = Fluss y[j,k] (J*J), Zukauf u[k] (J), Fehlmenge w[k] (J).

    A_cap  (J x nb): Summe_k y[j,k] <= x_j   (Kapazität von j wird verteilt)
    A_dem  (J x nb): Summe_j y[j,k] + u[k] + w[k] = D_k   (Nachfrage von k ist gedeckt)
    upper: Obergrenzen; ohne Umlagerung sind alle Flüsse j != k gesperrt, Zukauf ist begrenzt."""
    j = inst.n
    nb = j * j + 2 * j
    tc = np.asarray(inst.transfer_cost)
    cost = np.concatenate([tc.reshape(-1), np.asarray(inst.spot), np.full(j, inst.unmet)])
    a_cap = np.zeros((j, nb))
    a_dem = np.zeros((j, nb))
    for a in range(j):
        a_cap[a, a * j:(a + 1) * j] = 1.0
        a_dem[a, a:j * j:j] = 1.0
        a_dem[a, j * j + a] = 1.0
        a_dem[a, j * j + j + a] = 1.0
    upper = np.full(nb, np.inf)
    if not inst.transfer:
        off = ~np.eye(j, dtype=bool)
        upper[:j * j][off.reshape(-1)] = 0.0
    upper[j * j:j * j + j] = np.asarray(inst.spot_limit)
    return cost, a_cap, a_dem, upper


def solve_grouped(inst: Instance, demand: np.ndarray, groups: np.ndarray, x_fixed: np.ndarray | None = None):
    """Minimiere Summe_g P_g c.x_g + Summe_s (1/S) Kosten_s(x_g(s)); je Gruppe ein Plan x_g mit Summe x_g <= Budget.

    `x_fixed` (J,): Plan für alle Gruppen fest (Auswertung eines gegebenen Plans). Rückgabe: (Zielwert, x (G, J))."""
    s_count, j = demand.shape
    groups = np.asarray(groups)
    labels, gid = np.unique(groups, return_inverse=True)
    g_count = len(labels)
    cost, a_cap, a_dem, upper = stage2_block(inst)
    nb = cost.size
    w = 1.0 / s_count
    p_group = np.bincount(gid, minlength=g_count) * w

    # Variablen: erst x_g (G*J), dann je Szenario ein Block (nb)
    c_vec = np.concatenate([np.repeat(p_group, j) * inst.cap_cost, np.tile(cost * w, s_count)])
    rows_x = np.arange(s_count * j)
    cols_x = np.repeat(gid, j) * j + np.tile(np.arange(j), s_count)
    cap_x = coo_matrix((-np.ones(s_count * j), (rows_x, cols_x)), shape=(s_count * j, g_count * j)).tocsr()
    a_ub = hstack([cap_x, block_diag([csr_matrix(a_cap)] * s_count)])
    b_ub = np.zeros(s_count * j)
    budget_rows = coo_matrix(
        (np.ones(g_count * j), (np.repeat(np.arange(g_count), j), np.arange(g_count * j))),
        shape=(g_count, g_count * j + s_count * nb),
    )
    a_ub = vstack([a_ub, budget_rows.tocsr()])
    b_ub = np.concatenate([b_ub, np.full(g_count, inst.budget)])
    a_eq = hstack([csr_matrix((s_count * j, g_count * j)), block_diag([csr_matrix(a_dem)] * s_count)])
    b_eq = demand.reshape(-1)
    bounds = [(0.0, None)] * (g_count * j) + [(0.0, None if np.isinf(u) else float(u)) for u in upper] * s_count
    if x_fixed is not None:
        for g in range(g_count):
            for a in range(j):
                bounds[g * j + a] = (float(x_fixed[a]), float(x_fixed[a]))
    res = linprog(c_vec, A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if res.status != 0:
        raise RuntimeError(f"LP nicht lösbar: {res.message}")
    return float(res.fun), res.x[:g_count * j].reshape(g_count, j)


def expected_value_plan(inst: Instance, demand: np.ndarray) -> np.ndarray:
    """Plan für die mittlere Nachfrage (ein Szenario: der Erwartungswert der Verteilung)."""
    _, x = solve_grouped(inst, demand.mean(axis=0, keepdims=True), np.zeros(1, dtype=int))
    return x[0]


@dataclass(frozen=True)
class Information:
    """Kosten je Informationsstand (Erwartung über die Szenarien) und die zugehörigen Pläne."""
    eev: float        # Plan für den Durchschnittsfall, ausgewertet über alle Szenarien
    rp: float         # Plan unter Unsicherheit (kennt die Verteilung)
    partial: float    # Plan je Stufe des gemeinsamen Faktors z0 (Teilinformation)
    ws: float         # Hellseher: kennt jedes Szenario vor der Entscheidung
    x_ev: tuple[float, ...]
    x_rp: tuple[float, ...]

    @property
    def evpi(self) -> float:
        return self.rp - self.ws

    @property
    def vss(self) -> float:
        return self.eev - self.rp


def z0_groups(z0: np.ndarray, bins: int = C.Z0_BINS) -> np.ndarray:
    """Stufe 0 bis bins-1 nach Rang von z0 (gleich große Gruppen, Gleichstände nach Index)."""
    order = np.argsort(z0, kind="stable")
    g = np.empty(len(z0), dtype=int)
    g[order] = (np.arange(len(z0)) * bins) // len(z0)
    return g


def analyse_information(inst: Instance, demand: np.ndarray, z0: np.ndarray) -> Information:
    s_count = demand.shape[0]
    x_ev = expected_value_plan(inst, demand)
    eev, _ = solve_grouped(inst, demand, np.zeros(s_count, dtype=int), x_fixed=x_ev)
    rp, x_rp = solve_grouped(inst, demand, np.zeros(s_count, dtype=int))
    partial, _ = solve_grouped(inst, demand, z0_groups(z0))
    ws, _ = solve_grouped(inst, demand, np.arange(s_count))
    return Information(eev, rp, partial, ws, tuple(float(v) for v in x_ev), tuple(float(v) for v in x_rp[0]))
