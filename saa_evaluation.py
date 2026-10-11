"""Kennzahlen: eine Ziehung gegen die Referenzverteilung, das Experiment über Szenarienzahlen, Verdikte.

Die Referenzverteilung besteht aus REF_SCENARIOS gleich wahrscheinlichen Szenarien; eine Stichprobe sind S Ziehungen mit Zurücklegen daraus.
Dadurch ist die Verteilung exakt bekannt, und E[z] <= f* gilt strikt (Jensen), ohne Rauschen einer zweiten Stichprobe.

Begriffe (alle in Prozent der Kosten f* des besten Plans auf der Referenzmenge):
  z        Optimalwert der Stichprobe (in-sample), das, was ein Modellierer „sieht“
  f(x_S)   wahre Kosten des Stichprobenplans, ausgewertet auf der Referenzmenge
  Lücke    f(x_S) - f*   (immer >= 0, weil x* auf der Referenzmenge optimal ist)
  Bias     f_S(x*) - z   gepaart auf DERSELBEN Stichprobe: in-sample-Optimismus ohne Stichprobenrauschen (immer >= 0)
  Planabw. |x_S - x*|_1 / sum(x*)"""

from dataclasses import dataclass
from statistics import mean

import numpy as np

import saa_algorithm as A
import saa_constants as C
from saa_rng import uniform_block
from saa_scenario import Instance, demand_scenarios, make_instance


@dataclass(frozen=True)
class Settings:
    s: int = C.DEFAULT_S
    sigma: float = C.DEFAULT_SIGMA
    budget: float = C.DEFAULT_BUDGET
    transfer: str = C.DEFAULT_TRANSFER
    seed: int = C.DEFAULT_SEED
    draw: int = C.DEFAULT_DRAW


@dataclass(frozen=True)
class Reference:
    inst: Instance
    demand: np.ndarray
    x_star: tuple[float, ...]
    f_star: float


@dataclass(frozen=True)
class Draw:
    s: int
    x: tuple[float, ...]
    z: float             # in-sample-Optimum
    f_true: float        # f(x_S) auf der Referenzmenge
    f_sample_star: float  # f_S(x*) auf der Stichprobe
    gap_pct: float
    bias_pct: float
    z_error_pct: float   # (z - f*) / f*, mit Vorzeichen
    plan_dev_pct: float


def build_instance(settings: Settings) -> Instance:
    return make_instance(
        settings.seed, sigma=settings.sigma, rho=C.RHO, budget_ratio=settings.budget,
        spot_mult=C.SPOT_MULT, transfer=settings.transfer == "an",
    )


def reference(inst: Instance) -> Reference:
    """Die „wahre“ Verteilung: REF_SCENARIOS gleich wahrscheinliche Szenarien, darauf der beste Plan x*."""
    demand, _ = demand_scenarios(inst, C.REF_SEED, count=C.REF_SCENARIOS)
    f_star, x = A.solve_grouped(inst, demand, np.zeros(len(demand), dtype=int))
    return Reference(inst, demand, tuple(float(v) for v in x[0]), float(f_star))


def draw_seed(base: int, k: int, s: int) -> int:
    """Eigener Zufallsstrom je (Ziehung, Wiederholung, Szenarienzahl); alle verschieden von REF_SEED."""
    return 1_000_003 * int(base) + 7919 * int(k) + 17 * int(s) + 11


def sample_scenarios(demand: np.ndarray, seed: int, s: int) -> np.ndarray:
    """S Ziehungen MIT Zurücklegen aus den gleich wahrscheinlichen Szenarien der Referenzverteilung (Form (s, J))."""
    idx = np.minimum((uniform_block(seed, s) * len(demand)).astype(int), len(demand) - 1)
    return demand[idx]


def one_draw(ref: Reference, s: int, seed: int) -> Draw:
    inst = ref.inst
    sample = sample_scenarios(ref.demand, seed, s)
    groups = np.zeros(s, dtype=int)
    z, x_all = A.solve_grouped(inst, sample, groups)
    x = x_all[0]
    f_true, _ = A.solve_grouped(inst, ref.demand, np.zeros(len(ref.demand), dtype=int), x_fixed=x)
    f_sample_star, _ = A.solve_grouped(inst, sample, groups, x_fixed=np.asarray(ref.x_star))
    f_star = ref.f_star
    return Draw(
        s=s, x=tuple(float(v) for v in x), z=float(z), f_true=float(f_true), f_sample_star=float(f_sample_star),
        gap_pct=100.0 * (f_true - f_star) / f_star,
        bias_pct=100.0 * (f_sample_star - z) / f_star,
        z_error_pct=100.0 * (z - f_star) / f_star,
        plan_dev_pct=100.0 * float(np.abs(x - np.asarray(ref.x_star)).sum()) / float(np.sum(ref.x_star)),
    )


def verdict_of(d: Draw) -> str:
    if d.gap_pct < C.GAP_TARGET and d.plan_dev_pct >= 3.0:
        return "plan_wackelt_kosten_kaum"
    if d.gap_pct < C.GAP_TARGET:
        return "alles_nah"
    return "teuer"


def experiment(settings: Settings, progress=None) -> list[dict]:
    """Je Szenarienzahl DRAWS unabhängige Ziehungen: Mittel und 10./90. Perzentil von Lücke, Bias, Planabweichung, in-sample-Fehler."""
    inst = build_instance(settings)
    ref = reference(inst)
    rows = []
    total = len(C.SWEEP_S) * C.DRAWS
    done = 0
    for s in C.SWEEP_S:
        draws = []
        for k in range(C.DRAWS):
            draws.append(one_draw(ref, s, draw_seed(settings.draw, k, s)))
            done += 1
            if progress is not None:
                progress(done / total)
        gaps = np.array([d.gap_pct for d in draws])
        bias = np.array([d.bias_pct for d in draws])
        zerr = np.array([d.z_error_pct for d in draws])
        dev = np.array([d.plan_dev_pct for d in draws])
        rows.append({
            "s": s, "gap": float(gaps.mean()), "gap_median": float(np.median(gaps)), "gap_p10": float(np.percentile(gaps, 10)), "gap_p90": float(np.percentile(gaps, 90)),
            "bias": float(bias.mean()), "z_sd": float(zerr.std(ddof=1)), "z_mean": float(zerr.mean()),
            "z_all": [float(v) for v in zerr], "plan_dev": float(dev.mean()), "gap_all": [float(v) for v in gaps],
        })
    return rows


def smallest_s_for_gap(rows: list[dict], target: float = C.GAP_TARGET) -> int | None:
    """Kleinste Szenarienzahl des Experiments mit mittlerer Lücke unter dem Ziel (None: keine)."""
    for r in rows:
        if r["gap"] <= target:
            return r["s"]
    return None


def lshaped_comparison(settings: Settings, size: int):
    """L-Shaped (Einzel- und Mehrfachschnitt) gegen die erweiterte Form auf einer Stichprobe der Größe `size`."""
    import time

    import saa_lshaped as L

    inst = build_instance(settings)
    sample = sample_scenarios(reference(inst).demand, draw_seed(settings.draw, 0, size), size)
    t0 = time.perf_counter()
    ext, _ = A.solve_grouped(inst, sample, np.zeros(size, dtype=int))
    t_ext = time.perf_counter() - t0
    x0 = A.expected_value_plan(inst, sample)
    single = L.l_shaped(inst, sample, multicut=False, x0=x0)
    multi = L.l_shaped(inst, sample, multicut=True, x0=x0)
    return {"extensive": ext, "t_extensive": t_ext, "single": single, "multi": multi, "size": size}
