"""Konstanten: Vehikel (wie in der Wurzel der Linie), Regler-Grenzen, Experiment, Farben und Presets."""

# --- Vehikel: Kapazitätsvorhaltung mit Zukauf, Umlagerung und Fehlmenge (identisch zur Wurzel der Linie) --------------------------------------
J = 6
MU_LOW, MU_HIGH = 60, 140
CAP_COST = 1.0
SPOT_JITTER = 0.1
UNMET_MULT = 3.0
SPOT_LIMIT = 0.5
TRANSFER_BASE, TRANSFER_SCALE = 0.3, 0.35
Z0_BINS = 5                     # nur für die Kopie des Kerns (Teilinformation wird hier nicht gezeigt)
SCENARIOS = 200                 # Vorgabe von `demand_scenarios`, hier unbenutzt
RHO = 0.4                       # fester gemeinsamer Faktor
SPOT_MULT = 1.9                 # fester Zukaufpreis
SCENARIO_SEED_OFFSET = 7_000_003

# --- Die „wahre“ Verteilung: eine große Referenzmenge (die Demo misst nur gegen sie) ---------------------------------------------------------
REF_SCENARIOS = 600
REF_SEED = 900_001

# --- Regler --------------------------------------------------------------------------------------------------------------------------------
S_MIN, S_MAX, S_STEP, DEFAULT_S = 5, 200, 5, 10
SIGMA_MIN, SIGMA_MAX, SIGMA_STEP, DEFAULT_SIGMA = 0.10, 0.60, 0.05, 0.35
BUDGET_MIN, BUDGET_MAX, BUDGET_STEP, DEFAULT_BUDGET = 0.70, 1.30, 0.05, 0.95
TRANSFER_CHOICES = ("an", "aus")
DEFAULT_TRANSFER = "an"
SEED_MAX, DEFAULT_SEED = 999999, 7
DRAW_MAX, DEFAULT_DRAW = 999, 4

# --- Experiment ----------------------------------------------------------------------------------------------------------------------------
SWEEP_S = (5, 10, 20, 50, 100)  # Szenarienzahlen des Experiments
DRAWS = 24                      # unabhängige Ziehungen je Szenarienzahl
LSHAPED_SIZES = (10, 50, 100, 200)
LSHAPED_DEFAULT = 50
LSHAPED_TOL = 1e-6
LSHAPED_MAX_ITER = 500
GAP_TARGET = 1.0                # Prozent der Kosten des besten Plans

# --- Farben --------------------------------------------------------------------------------------------------------------------------------
COLOR_BEST = "#2F6B65"
COLOR_SAA = "#B5651D"
COLOR_BIAS = "#4c78a8"
COLOR_MEAN = "rgba(150,150,150,0.75)"

PRESETS = {
    "Standardfall (Voreinstellung)": {
        "s": DEFAULT_S, "sigma": DEFAULT_SIGMA, "budget": DEFAULT_BUDGET, "transfer": DEFAULT_TRANSFER,
        "seed": DEFAULT_SEED, "draw": DEFAULT_DRAW,
    },
    "Wenige Szenarien": {
        "s": 5, "sigma": DEFAULT_SIGMA, "budget": DEFAULT_BUDGET, "transfer": DEFAULT_TRANSFER,
        "seed": DEFAULT_SEED, "draw": DEFAULT_DRAW,
    },
    "Ohne Umlagerung, knappes Budget": {
        "s": DEFAULT_S, "sigma": DEFAULT_SIGMA, "budget": 0.85, "transfer": "aus",
        "seed": DEFAULT_SEED, "draw": DEFAULT_DRAW,
    },
    "Hohe Streuung, weites Budget": {
        "s": DEFAULT_S, "sigma": 0.50, "budget": 1.30, "transfer": "an",
        "seed": DEFAULT_SEED, "draw": DEFAULT_DRAW,
    },
}
PRESET_HELP = {
    "Standardfall (Voreinstellung)": "Zehn Szenarien, Streuung 35 %, Umlagerung an, Budget 95 % der mittleren Nachfrage.",
    "Wenige Szenarien": "Nur fünf Szenarien: der Plan wackelt am stärksten, und die Stichprobe täuscht am meisten.",
    "Ohne Umlagerung, knappes Budget": "Keine Umlagerung, Budget 85 %: der Plan reagiert empfindlicher auf die Stichprobe.",
    "Hohe Streuung, weites Budget": "Streuung 50 % bei weitem Budget: viel Nachfrage-Rand, den zehn Szenarien kaum treffen.",
}
