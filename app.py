"""Stichprobe statt Verteilung: SAA - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import saa_constants as C
from saa_evaluation import (
    Settings,
    build_instance,
    draw_seed,
    experiment,
    lshaped_comparison,
    one_draw,
    reference,
    smallest_s_for_gap,
    verdict_of,
)
from saa_presets import (
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    new_draw,
    randomize_seed,
    sync_query_params,
)
from saa_visualization import build_costs, build_experiment, build_insample, build_lshaped, build_plans

st.set_page_config(page_title="Stichprobe statt Verteilung – Sebastian Hanisch", layout="wide")


def _de(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


@st.cache_data(show_spinner=False)
def _reference(settings_key):
    sigma, budget, transfer, seed = settings_key
    return reference(build_instance(Settings(sigma=sigma, budget=budget, transfer=transfer, seed=seed)))


@st.cache_data(show_spinner=False)
def _draw(settings, ref_key):
    ref = _reference(ref_key)
    return one_draw(ref, settings.s, draw_seed(settings.draw, 0, settings.s))


@st.cache_data(show_spinner=False)
def _experiment(settings):
    return experiment(settings)


@st.cache_data(show_spinner=False)
def _lshaped(settings, size):
    return lshaped_comparison(settings, size)


st.title("🎲 Stichprobe statt Verteilung: SAA")
st.markdown(
    """
In der Praxis kennen Sie die Nachfrage-Verteilung nicht, sondern nur **eine Stichprobe von Szenarien**. Die **Sample Average Approximation (SAA)**
optimiert den besten Plan auf genau dieser Stichprobe und hofft, dass er auch für die wirkliche Verteilung taugt. Diese Demo misst, **wie weit
das trägt**: Wie viel kostet der Stichprobenplan wirklich mehr? Wie sehr täuscht der Optimalwert der Stichprobe? Und wie viele Szenarien braucht man?

Anders als die Fall-Demos zeigt sie **ein** Verfahren an einem wachsenden Beispiel, mit demselben Kapazitäts-Vehikel wie die
[Wurzel der Linie](https://github.com/sebastian-hanisch/newsvendor-evpi-demo); dort waren die Szenarien die Verteilung, hier sind sie eine Ziehung daraus.
Weiter unten: das Experiment über Szenarienzahlen, **🧩 L-Shaped** als Zerlegung, **🚧 Wo die Annahmen enden** und **📐 Mathematische Formulierung**.
"""
)

with st.expander("So funktioniert SAA", expanded=True):
    st.markdown(
        """
1. **Ziehen:** S Szenarien der Nachfrage aus der Verteilung (hier: S Ziehungen mit Zurücklegen aus einer Referenzmenge von 600 gleich wahrscheinlichen Szenarien, die als „wahre“ Verteilung gilt).
2. **Optimieren:** der Plan x_S, der auf diesen S Szenarien im Mittel am billigsten ist. Sein Optimalwert z ist das, was ein Modellierer „sieht“.
3. **Prüfen:** dasselbe x_S auf der Referenzmenge ausgewertet: die **wahren Kosten**. Der Abstand zum besten Plan x* ist die **Lücke**.
4. **Gepaart messen:** Wie optimistisch z ist, misst man auf derselben Stichprobe: x* dort ausgewertet minus z. Das hat kein Stichprobenrauschen, weil
   beide Zahlen aus denselben Szenarien stammen.
        """
    )

if C.PRESETS:
    st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
    cols = st.columns(len(C.PRESETS))
    for col, name in zip(cols, C.PRESETS):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}")

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.markdown("**Stichprobe**")
    s = st.slider("Szenarienzahl S der Stichprobe", *bounds("s_slider"), step=C.S_STEP, key="s_slider",
                  help="Wie viele Szenarien der Plan sieht. Wirkt auf die einzelne Ziehung oben; das Experiment unten läuft über feste Werte.")
    draw = st.number_input("Ziehung (Zufalls-Seed der Stichprobe)", *bounds("draw_input"), key="draw_input", step=1,
                           help="Welche Stichprobe gezogen wird. Das Experiment wiederholt die Ziehung 24-mal.")
    st.button("🎲 Neue Ziehung", width="stretch", on_click=new_draw)
    st.markdown("**Nachfrage und Möglichkeiten**")
    sigma = st.slider("Streuung (Log-Streuung σ)", *bounds("sigma_slider"), step=C.SIGMA_STEP, key="sigma_slider",
                      help="Wie stark die Nachfrage um ihren Mittelwert schwankt.")
    budget = st.slider("Budget auf die Kapazität (Anteil der Gesamtnachfrage)", *bounds("budget_slider"), step=C.BUDGET_STEP, key="budget_slider",
                       help="Obergrenze für die Summe aller vorgehaltenen Kapazitäten, als Anteil der mittleren Gesamtnachfrage.")
    transfer = st.radio("Umlagerung zwischen Standorten", C.TRANSFER_CHOICES, key="transfer_radio", horizontal=True,
                        help="An: ungenutzte Kapazität eines Standorts kann den Bedarf eines anderen decken (mit Transportkosten).")
    st.markdown("**Instanz**")
    seed = st.number_input("Zufalls-Seed der Instanz", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neue Instanz generieren", width="stretch", on_click=randomize_seed)

sync_query_params({
    "s_slider": int(s), "sigma_slider": sigma, "budget_slider": budget, "transfer_radio": transfer,
    "seed_input": int(seed), "draw_input": int(draw),
})

settings = Settings(s=int(s), sigma=float(sigma), budget=float(budget), transfer=str(transfer), seed=int(seed), draw=int(draw))
ref_key = (settings.sigma, settings.budget, settings.transfer, settings.seed)
exp_key = Settings(s=C.DEFAULT_S, sigma=settings.sigma, budget=settings.budget, transfer=settings.transfer, seed=settings.seed, draw=settings.draw)

# --- Ergebnis: eine Ziehung -------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Eine Ziehung")
with st.spinner("Löse die Planungsprobleme auf der Stichprobe und der Referenzmenge …"):
    ref = _reference(ref_key)
    d = _draw(settings, ref_key)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Optimalwert der Stichprobe (z)", f"{d.z:,.0f}".replace(",", "."), delta=f"{_de(d.z_error_pct)} % gegen wahren Wert".replace("-", "−"), delta_color="off")
m2.metric("Wahre Kosten des Stichprobenplans", f"{d.f_true:,.0f}".replace(",", "."), delta=f"{_de(d.gap_pct, 2)} % über dem besten Plan", delta_color="inverse")
m3.metric("Kosten des besten Plans (x*)", f"{ref.f_star:,.0f}".replace(",", "."), delta="Referenz", delta_color="off")
m4.metric("Plan weicht ab um", f"{_de(d.plan_dev_pct)} %", delta="Summe |x_S − x*| / Summe x*", delta_color="off")
st.plotly_chart(build_costs(d.z, d.f_true, ref.f_star, d.f_sample_star), width="stretch", key="costs_chart")
st.caption(
    "Oben: was die Stichprobe zeigt. Unten: was der Plan wirklich kostet. Der Optimalwert der Stichprobe kann daneben liegen, in beide Richtungen; "
    "das sind **gepaarte** Größen auf derselben Stichprobe (siehe „So funktioniert SAA“), kein Rauschen der Referenz."
)
st.plotly_chart(build_plans(build_instance(settings).mu, ref.x_star, d.x), width="stretch", key="plans_chart")
st.caption("Der Plan aus der Stichprobe wackelt von Ziehung zu Ziehung deutlich stärker, als seine Kosten sich ändern: viele Pläne sind fast gleich gut.")

# --- Kernfrage ----------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage: Kann man dem Stichprobenplan trauen?")
verdict = verdict_of(d)
if verdict == "plan_wackelt_kosten_kaum":
    st.info(
        f"**Der Plan wackelt, die Kosten kaum:** Der Stichprobenplan weicht um {_de(d.plan_dev_pct)} % vom besten Plan ab, kostet aber nur "
        f"{_de(d.gap_pct, 2)} % mehr. Dass der Optimalwert der Stichprobe {_de(abs(d.z_error_pct))} % "
        f"{'unter' if d.z_error_pct < 0 else 'über'} dem wahren Wert liegt, ist die eigentliche Täuschung."
    )
elif verdict == "alles_nah":
    st.success(f"**Hier trägt die Stichprobe:** Plan {_de(d.plan_dev_pct)} % daneben, Mehrkosten {_de(d.gap_pct, 2)} %.")
else:
    st.warning(
        f"**Diese Ziehung ist teuer:** {_de(d.gap_pct, 2)} % Mehrkosten gegenüber dem besten Plan (Plan {_de(d.plan_dev_pct)} % daneben, "
        f"Optimalwert {_de(abs(d.z_error_pct))} % {'zu niedrig' if d.z_error_pct < 0 else 'zu hoch'}). Das Experiment unten zeigt, wie häufig das vorkommt."
    )
st.caption(
    "Das ist **eine** Ziehung. Wie typisch sie ist, zeigt das Experiment: die Lücke ist schief verteilt, der Median liegt weit unter dem Mittel."
)

st.markdown("---")

# --- Experiment ------------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment: Wie viele Szenarien braucht man?")
st.caption(
    f"Je Szenarienzahl ({', '.join(str(v) for v in C.SWEEP_S)}) {C.DRAWS} unabhängige Ziehungen, jede gegen dieselbe Referenzmenge. "
    "Die Szenarienzahl-Regler der Seitenleiste wirkt hier nicht; Streuung, Budget, Umlagerung, Instanz und Ziehung gelten."
)
if st.button("Experiment starten (ca. 30 Sekunden)", key="run_experiment"):
    st.session_state["experiment_done"] = exp_key
if st.session_state.get("experiment_done") == exp_key:
    with st.spinner(f"Rechne {len(C.SWEEP_S) * C.DRAWS} Ziehungen …"):
        rows = _experiment(exp_key)
    st.plotly_chart(build_experiment(rows), width="stretch", key="experiment_chart")
    st.caption("Beide Achsen logarithmisch. Balken: 10. bis 90. Perzentil der Lücke. Gestrichelt: Optimismus des Optimalwerts, gepaart gemessen.")
    st.plotly_chart(build_insample(rows), width="stretch", key="insample_chart")
    st.caption("Jeder Punkt eine Ziehung: Optimalwert der Stichprobe gegen den wahren Wert. Er streut stark und liegt nicht systematisch auf einer Seite.")
    table = [
        {"S": r["s"], "Lücke Mittel (%)": round(r["gap"], 2), "Lücke Median (%)": round(r["gap_median"], 2),
         "Lücke 90. Perz. (%)": round(r["gap_p90"], 2), "Optimismus gepaart (%)": round(r["bias"], 2),
         "Optimalwert streut (sd, %)": round(r["z_sd"], 1), "Plan weicht ab (%)": round(r["plan_dev"], 1)}
        for r in rows
    ]
    st.dataframe(table, hide_index=True, width="stretch")
    need = smallest_s_for_gap(rows)
    r_last = rows[-1]
    if need is None:
        st.warning(f"Selbst bei {r_last['s']} Szenarien liegt die mittlere Lücke bei {_de(r_last['gap'], 2)} %: mehr als {C.GAP_TARGET:.0f} %.")
    else:
        worst = next(r for r in rows if r["s"] == need)
        st.info(
            f"**Ab {need} Szenarien** liegt die mittlere Lücke unter {C.GAP_TARGET:.0f} %. Bei {need} Szenarien liegt das 90. Perzentil aber noch bei "
            f"{_de(worst['gap_p90'], 2)} %, und der Optimalwert der Stichprobe streut mit sd {_de(worst['z_sd'])} %. "
            "Eine feste Faustregel gibt es nicht: andere Einstellungen verlangen anderes S."
        )
else:
    st.info("Das Experiment läuft auf Knopfdruck, weil es mehr als hundert Optimierungen rechnet.")

st.markdown("---")

# --- L-Shaped -----------------------------------------------------------------------------------------------------------------------------------

st.subheader("🧩 L-Shaped: dieselbe Stichprobe, zerlegt")
st.markdown(
    "Mit vielen Szenarien wird das Planungsproblem groß. Das **L-Shaped-Verfahren** (Benders-Zerlegung für zweistufige LP) löst stattdessen "
    "einen kleinen Master für den Plan und je Szenario ein Teilproblem; die Dualpreise der Teilprobleme liefern **Schnitte**, die den Master verbessern. "
    "Der **Einzelschnitt** fasst alle Szenarien in einen Schnitt, der **Mehrfachschnitt** gibt jedem Szenario seinen eigenen. "
    "Das deterministische Gegenstück mit ganzzahligem Master steht in der "
    "[Benders-Demo](https://github.com/sebastian-hanisch/benders-demo) der Netzwerkfluss-Linie."
)
size = st.select_slider("Szenarienzahl der Stichprobe", options=C.LSHAPED_SIZES, value=C.LSHAPED_DEFAULT, key="lshaped_size")
if st.button("L-Shaped rechnen", key="run_lshaped"):
    st.session_state["lshaped_done"] = (exp_key, int(size))
if st.session_state.get("lshaped_done") == (exp_key, int(size)):
    with st.spinner("Löse mit Einzel- und Mehrfachschnitt …"):
        cmp_ = _lshaped(exp_key, int(size))
    single, multi = cmp_["single"], cmp_["multi"]
    st.dataframe(
        [
            {"Verfahren": "Erweiterte Form (ein LP)", "Iterationen": 1, "Schnitte": 0, "Zeit (s)": round(cmp_["t_extensive"], 3), "Zielwert": round(cmp_["extensive"], 3)},
            {"Verfahren": "L-Shaped, Einzelschnitt", "Iterationen": single.iterations, "Schnitte": single.cuts, "Zeit (s)": round(single.seconds, 3), "Zielwert": round(single.objective, 3)},
            {"Verfahren": "L-Shaped, Mehrfachschnitt", "Iterationen": multi.iterations, "Schnitte": multi.cuts, "Zeit (s)": round(multi.seconds, 3), "Zielwert": round(multi.objective, 3)},
        ],
        hide_index=True, width="stretch",
    )
    st.plotly_chart(build_lshaped(cmp_), width="stretch", key="lshaped_chart")
    st.info(
        f"Alle drei Wege geben denselben Zielwert. Der Mehrfachschnitt braucht {multi.iterations} statt {single.iterations} Iterationen, "
        f"dafür {multi.cuts} statt {single.cuts} Schnitte. Der Solver löst die **erweiterte Form** hier trotzdem schneller als beide Zerlegungen: "
        "Die Zerlegung zeigt die Struktur, sie gewinnt auf diesem Problem kein Tempo."
    )
    st.caption("Startpunkt ist der Plan für die mittlere Nachfrage; Abbruch, wenn obere und untere Schranke auf 1e-6 relativ zusammenliegen.")
else:
    st.info("Wählen Sie eine Szenarienzahl und starten Sie die Rechnung.")

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Die Referenzmenge (600 Szenarien) ist die wahre Verteilung** | Das ist eine Setzung, damit die Verteilung exakt bekannt ist: Die Stichprobe zieht aus genau diesen 600 Szenarien. Eine echte Verteilung hat mehr Rand als 600 Punkte; seltene Ereignisse fehlen hier. | – |
| **Stichprobe und Verteilung stimmen überein (unabhängige Ziehung)** | Bei verschobener Verteilung (Nachfrage-Trend, seltene Ereignisse fehlen in der Stichprobe) nützt mehr Szenarien aus der alten Verteilung nichts. | – |
| **Der Erwartungswert ist das Ziel** | Ein Risikomaß am Rand der Verteilung (Tail-Kosten) braucht deutlich mehr Szenarien: der Plan hängt dann an nur (1 − α) · S Szenarien. | [CVaR-Demo](https://github.com/sebastian-hanisch/cvar-demo): Risiko als Ziel, Szenarienbedarf des Risikoplans |
| **Eine Instanz, 24 Ziehungen je Szenarienzahl** | Die Mittelwerte tragen einen Stichprobenfehler, die Verteilung ist schief: ein einzelner schlechter Ziehungsausreißer verschiebt das Mittel. Der Median steht deshalb daneben. | – |
| **Kapazitäts-Vehikel mit festen Preisen** | Wie viele Szenarien man braucht, hängt an Streuung, Budget und Umlagerung (siehe die Presets) und lässt sich nicht aus einem Fall auf einen anderen übertragen. | – |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Problem.** Gesucht ist $x^\ast \in \arg\min_{x\in X} f(x)$ mit $f(x)=c^\top x+\mathbb E[Q(x,\xi)]$ (Stufe 2 wie in der Wurzel der Linie).
Die SAA ersetzt den Erwartungswert durch das Mittel über $S$ gezogene Szenarien:
$$\hat f_S(x)=c^\top x+\tfrac1S\sum_{s=1}^S Q(x,\xi_s),\qquad x_S\in\arg\min_x \hat f_S(x),\qquad z_S=\hat f_S(x_S).$$

**Drei Größen.** Die **Lücke** $f(x_S)-f(x^\ast)\ge 0$ ist der wahre Preis der Stichprobe. Der **Optimalwert** $z_S$ ist ein nach unten verzerrter Schätzer
von $f(x^\ast)$, denn $\mathbb E[z_S]=\mathbb E[\min_x \hat f_S(x)]\le \min_x \mathbb E[\hat f_S(x)]=f(x^\ast)$ (das Minimum eines Mittels liegt unter dem Mittel
des Minimums). Die **gepaarte Verzerrung** $\hat f_S(x^\ast)-z_S\ge 0$ misst genau diesen Optimismus auf derselben Stichprobe, ohne Stichprobenrauschen,
und ihr Erwartungswert ist $f(x^\ast)-\mathbb E[z_S]$.

**L-Shaped.** Das Teilproblem $Q(x,\xi_s)$ ist ein LP in $x$ als rechter Seite, also konvex in $x$; seine Dualpreise $m_s$ der Kapazitätszeilen liefern den Schnitt
$Q(x,\xi_s)\ge Q(\bar x,\xi_s)+m_s^\top(x-\bar x)$. Der Master minimiert $c^\top x+\tfrac1S\sum_s\theta_s$ unter allen bisherigen Schnitten $\theta_s\ge Q_s(\bar x)+m_s^\top(x-\bar x)$
(Mehrfachschnitt) beziehungsweise nur dem Mittel der Schnitte (Einzelschnitt). Die untere Schranke ist der Master-Wert, die obere der beste bewertete Plan.

**Literatur.** Die Verzerrung nach unten ist der elementare Jensen-Schritt oben. Konvergenz der SAA und Schätzer für die Lücke: Shapiro, Dentcheva & Ruszczyński,
*Lectures on Stochastic Programming* (SIAM, 2009), und Mak, Morton & Wood (1999); beide waren für diese Demo nicht im Volltext zugänglich, die Aussagen sind hier
**gemessen**, nicht zitiert. L-Shaped: Van Slyke & Wets (1969); Mehrfachschnitt: Birge & Louveaux (1988).
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html)."
)
