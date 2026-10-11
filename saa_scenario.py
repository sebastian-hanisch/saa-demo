"""Vehikel: J Standorte mit zufälliger Nachfrage; Instanz und Szenarien deterministisch aus Zufalls-Seeds (SplitMix64)."""

from dataclasses import dataclass

import numpy as np

import saa_constants as C
from saa_rng import normal_block, uniform_block


@dataclass(frozen=True)
class Instance:
    """Alle Größen als Tupel (hashbar für st.cache_data). `transfer` False: Umlagerung nicht erlaubt."""
    mu: tuple[float, ...]
    cap_cost: float
    spot: tuple[float, ...]
    unmet: float
    spot_limit: tuple[float, ...]
    transfer_cost: tuple[tuple[float, ...], ...]
    transfer: bool
    budget: float            # Obergrenze auf die Summe der Kapazitäten
    sigma: float
    rho: float

    @property
    def n(self) -> int:
        return len(self.mu)


def make_instance(seed: int, sigma: float, rho: float, budget_ratio: float, spot_mult: float, transfer: bool) -> Instance:
    """Deterministisch aus den Argumenten: gleiche Eingabe, gleiche Instanz."""
    j = C.J
    u = uniform_block(seed, 4 * j)
    mu = np.round(C.MU_LOW + (C.MU_HIGH - C.MU_LOW) * u[:j])
    spot = spot_mult * (1.0 - C.SPOT_JITTER + 2 * C.SPOT_JITTER * u[j:2 * j])
    pos = u[2 * j:4 * j].reshape(j, 2)
    dist = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=2)
    tc = C.TRANSFER_SCALE * (C.TRANSFER_BASE + dist)
    np.fill_diagonal(tc, 0.0)
    return Instance(
        mu=tuple(float(m) for m in mu),
        cap_cost=C.CAP_COST,
        spot=tuple(float(s) for s in spot),
        unmet=C.UNMET_MULT * C.CAP_COST,
        spot_limit=tuple(float(C.SPOT_LIMIT * m) for m in mu),
        transfer_cost=tuple(tuple(float(v) for v in row) for row in tc),
        transfer=bool(transfer),
        budget=float(budget_ratio * mu.sum()),
        sigma=float(sigma),
        rho=float(rho),
    )


def demand_scenarios(inst: Instance, seed: int, count: int = C.SCENARIOS):
    """`count` gleich wahrscheinliche Nachfrage-Szenarien (count, J) und der gemeinsame Faktor z0 je Szenario (count,).

    D_j = mu_j * exp(sigma * (sqrt(rho) z0 + sqrt(1 - rho) z_j) - sigma^2 / 2): lognormal, Erwartungswert mu_j."""
    j = inst.n
    z = normal_block(seed + C.SCENARIO_SEED_OFFSET, count * (j + 1)).reshape(count, j + 1)
    z0, zj = z[:, 0], z[:, 1:]
    g = np.sqrt(inst.rho) * z0[:, None] + np.sqrt(1.0 - inst.rho) * zj
    d = np.asarray(inst.mu) * np.exp(inst.sigma * g - 0.5 * inst.sigma ** 2)
    return d, z0
