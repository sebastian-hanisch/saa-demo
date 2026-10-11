"""Plotly-Figuren: Pläne je Standort, Kosten einer Ziehung, Experiment über Szenarienzahlen, L-Shaped-Vergleich. Alle Achsen fest."""

import numpy as np
import plotly.graph_objects as go

import saa_constants as C


def _fixed(fig, height=340):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.22))
    return fig


def build_plans(mu, x_star, x_s) -> go.Figure:
    names = [f"Standort {i + 1}" for i in range(len(mu))]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=list(mu), name="mittlere Nachfrage", marker_color=C.COLOR_MEAN))
    fig.add_trace(go.Bar(x=names, y=list(x_star), name="bester Plan x* (Referenz)", marker_color=C.COLOR_BEST))
    fig.add_trace(go.Bar(x=names, y=list(x_s), name="Plan aus der Stichprobe", marker_color=C.COLOR_SAA))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Kapazität")
    return _fixed(fig)


def build_costs(z, f_true, f_star, f_sample_star) -> go.Figure:
    """Was die Stichprobe zeigt (z), was der Plan wirklich kostet, was das Beste wäre."""
    items = [
        ("Optimalwert der Stichprobe (in-sample)", z, C.COLOR_BIAS),
        ("Bester Plan x* auf der Stichprobe", f_sample_star, C.COLOR_MEAN),
        ("Stichprobenplan, wirklich (Referenz)", f_true, C.COLOR_SAA),
        ("Bester Plan x*, wirklich (Referenz)", f_star, C.COLOR_BEST),
    ]
    fig = go.Figure()
    labels = [i[0] for i in items]
    for label, value, color in items:
        fig.add_trace(go.Scatter(
            x=[value], y=[label], mode="markers+text", marker=dict(size=15, color=color), showlegend=False,
            text=[f"{value:.1f}".replace(".", ",")], textposition="middle right",
            hovertemplate=f"{label}<br>%{{x:.2f}}<extra></extra>",
        ))
    lo, hi = min(v for _, v, _ in items), max(v for _, v, _ in items)
    pad = max(hi - lo, 1.0)
    fig.update_xaxes(title="Erwartete Gesamtkosten", range=[lo - 0.6 * pad, hi + 0.8 * pad])
    fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=labels)
    return _fixed(fig, 300)


def build_experiment(rows) -> go.Figure:
    """Mittlere Lücke (mit 10.-90.-Perzentil) und gepaarter Bias über der Szenarienzahl, doppelt logarithmisch."""
    s = [r["s"] for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=s, y=[r["gap"] for r in rows], mode="lines+markers", name="Lücke des Stichprobenplans, Mittel (wahre Mehrkosten)",
        line=dict(color=C.COLOR_SAA),
        error_y=dict(type="data", symmetric=False, array=[r["gap_p90"] - r["gap"] for r in rows],
                     arrayminus=[r["gap"] - r["gap_p10"] for r in rows], thickness=1, width=3)))
    fig.add_trace(go.Scatter(
        x=s, y=[max(r["gap_median"], 1e-3) for r in rows], mode="lines+markers", name="Lücke, Median (typische Ziehung)",
        line=dict(color=C.COLOR_SAA, dash="dot"), marker=dict(symbol="diamond-open")))
    fig.add_trace(go.Scatter(
        x=s, y=[r["bias"] for r in rows], mode="lines+markers", name="Optimismus der Stichprobe (gepaart)",
        line=dict(color=C.COLOR_BIAS, dash="dash")))
    fig.add_hline(y=C.GAP_TARGET, line_dash="dot", line_color="rgba(120,120,120,0.8)", annotation_text="1 %", annotation_position="top left")
    fig.update_xaxes(title="Szenarienzahl der Stichprobe", type="log", tickvals=s, ticktext=[str(v) for v in s])
    fig.update_yaxes(title="% der Kosten des besten Plans", type="log")
    return _fixed(fig, 380)


def build_insample(rows) -> go.Figure:
    """Jede Ziehung als Punkt: in-sample-Optimalwert gegen die wahren Kosten des besten Plans (0 % = trifft zu)."""
    fig = go.Figure()
    rng = np.random.default_rng(3)
    for r in rows:
        jitter = rng.uniform(-0.12, 0.12, size=len(r["z_all"]))
        fig.add_trace(go.Scatter(
            x=np.log10(r["s"]) + jitter, y=r["z_all"], mode="markers", showlegend=False,
            marker=dict(size=6, color=C.COLOR_BIAS, opacity=0.65), hovertemplate=f"S = {r['s']}<br>%{{y:.1f}} %<extra></extra>"))
    fig.add_hline(y=0, line_color=C.COLOR_BEST, annotation_text="wahrer Wert", annotation_position="top left")
    fig.update_xaxes(title="Szenarienzahl der Stichprobe", tickvals=[np.log10(r["s"]) for r in rows], ticktext=[str(r["s"]) for r in rows])
    fig.update_yaxes(title="in-sample-Optimalwert gegen wahren Wert (%)")
    return _fixed(fig, 360)


def build_lshaped(cmp_) -> go.Figure:
    """Obere und untere Schranke je Iteration, Einzel- gegen Mehrfachschnitt."""
    fig = go.Figure()
    for name, res, color in (("Einzelschnitt", cmp_["single"], C.COLOR_SAA), ("Mehrfachschnitt", cmp_["multi"], C.COLOR_BEST)):
        its = list(range(1, len(res.history) + 1))
        fig.add_trace(go.Scatter(x=its, y=[h[0] for h in res.history], mode="lines", name=f"{name}: untere Schranke", line=dict(color=color)))
        fig.add_trace(go.Scatter(x=its, y=[h[1] for h in res.history], mode="lines", name=f"{name}: obere Schranke", line=dict(color=color, dash="dash")))
    fig.update_xaxes(title="Iteration")
    fig.update_yaxes(title="Kosten (Schranken)")
    return _fixed(fig, 340)
