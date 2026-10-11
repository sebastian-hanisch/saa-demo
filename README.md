# Stichprobe statt Verteilung: SAA – Streamlit-Demo

Zweites Stück der **Optimierung-unter-Unsicherheit-Linie** der „Konzepte“-Reihe für die Website „Sebastian Hanisch – Operations Research und Machine Learning“.
Anders als die Fall-Demos (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt sie **ein** Verfahren, die **Sample Average Approximation (SAA)**, an einem wachsenden Beispiel.
**Kante in der Linie:** Sie behebt eine Annahme der Wurzel [newsvendor-evpi-demo](https://github.com/sebastian-hanisch/newsvendor-evpi-demo): Dort sind die Szenarien die Verteilung,
hier sind sie eine **Ziehung** daraus. Das Vehikel ist dasselbe: Kapazitätsvorhaltung mit Zukauf, Umlagerung und Fehlmenge, sechs Standorte, als lineares Programm.

## Warum dieses Problem

Wer unter Unsicherheit optimiert, hat fast nie die Verteilung, sondern eine Stichprobe von Szenarien, und optimiert auf genau dieser. Das wirft drei Fragen auf, die sich leicht
vermischen: **Wie viel kostet der Stichprobenplan wirklich mehr als der beste Plan?** (die Lücke), **Wie sehr täuscht sein Optimalwert?** (der Optimalwert, den der Modellierer „sieht“,
ist ein anderer als die wahren Kosten) und **Wie viele Szenarien braucht man?** Die Demo misst alle drei gegen eine Referenzverteilung, die sie exakt kennt.

## Modell

Dasselbe Modell wie in der Wurzel (Stufe 1 Kapazität zu 1 je Einheit, Stufe 2 Umlagerung, Zukauf bis 50 % der Nachfrage, Fehlmenge dreifach bestraft; Streuung, Budget und Umlagerung
einstellbar). **Die Verteilung** besteht aus 600 gleich wahrscheinlichen Szenarien (lognormal, ein gemeinsamer Faktor); eine **Stichprobe** sind S Ziehungen mit Zurücklegen daraus.
Dadurch ist die Verteilung exakt bekannt, und der Plan x* ist der beste für sie. Formeln im 📐-Expander der App.

## Methodik

- **Ziehen und optimieren:** S Szenarien, der beste Plan x_S dafür, sein Optimalwert z (ein LP über die Stichprobe).
- **Prüfen:** x_S auf den 600 Szenarien ausgewertet, die **wahren Kosten**; die **Lücke** ist der Abstand zum besten Plan.
- **Gepaart messen:** der Optimismus des Optimalwerts als x* auf derselben Stichprobe minus z; beide Zahlen hängen an denselben Szenarien und tragen kein Stichprobenrauschen.
- **Experiment:** je Szenarienzahl (5, 10, 20, 50, 100) 24 unabhängige Ziehungen, Mittel, Median und 10./90. Perzentil.
- **L-Shaped (Abschnitt):** dieselbe Stichprobe mit Einzel- und Mehrfachschnitt zerlegt, gegen die erweiterte Form.

## Befunde (gemessen, keine Behauptungen)

Mittel über 24 Ziehungen mit der Voreinstellung (Seed 7), in Prozent der Kosten des besten Plans; jede Aussage in `tests/test_claims.py` als Band belegt. Der Stichprobenfehler der Mittel
ist erheblich, weil die Lücke schief verteilt ist; deshalb stehen Median und 90. Perzentil daneben.

| Frage | Befund |
|---|---|
| **Wie groß ist die Lücke?** | Mittel 0,8 % bei 5 Szenarien, 0,5 % bei 10, 0,2 % bei 20, 0,16 % bei 50, 0,09 % bei 100 (90. Perzentil 1,0 / 1,4 / 0,3 / 0,5 / 0,3 %). Sie fällt etwa wie 1/S. |
| **Wie sehr täuscht der Optimalwert?** | Er streut mit sd 15 % bei 5 Szenarien, 11 % bei 10, 7 % bei 20, 4,5 % bei 50, 3,9 % bei 100, in **beide** Richtungen. Der systematische Optimismus ist mit 0,85 / 0,45 / 0,23 / 0,14 / 0,09 % klein dagegen: Der „Fluch“ ist vor allem Streuung, nicht Verzerrung. |
| **Wackelt der Plan oder die Kosten?** | Der Plan: bei 20 Szenarien weicht er im Mittel um 7 % vom besten ab, bei 5 um 15 %. Die Kosten kaum: Median der Lücke unter 1 %. Viele Pläne sind fast gleich gut. |
| **Wie viele Szenarien für 1 % mittlere Lücke?** | Voreinstellung 5, ohne Umlagerung und mit Budget 0,85 etwa 10, bei Streuung 50 % und weitem Budget etwa 20. Eine feste Faustregel gibt es nicht (Faktor 4 zwischen den Fällen). |
| **L-Shaped gegen erweiterte Form** | Bei 100 Szenarien: Einzelschnitt rund 70 Iterationen (je ein Schnitt), Mehrfachschnitt rund 9 Iterationen mit insgesamt rund 900 Schnitten, beide denselben Zielwert wie die erweiterte Form (relative Abweichung unter 1e-5). Die erweiterte Form ist mit einem LP in 0,05 s die schnellste. |

## Ehrliche Grenzen

- **Die Referenz ist gesetzt, nicht gefunden.** Die 600 Szenarien sind die Verteilung; eine echte Verteilung hat mehr Rand. Die Aussagen gelten für diese Verteilung.
- **Eine Instanz, 24 Ziehungen je Szenarienzahl.** Die Mittel tragen Stichprobenfehler (die Lücke ist schief, wenige schlechte Ziehungen bewegen das Mittel). Die Ordnung und die Größenordnung sind belastbar, einzelne Prozentzahlen nicht auf die zweite Stelle.
- **Nur der Erwartungswert.** Ein Risikomaß am Rand braucht mehr Szenarien; das ist nicht gemessen.
- **Nur unabhängige Ziehungen aus einer festen Verteilung.** Ein Trend oder fehlende seltene Ereignisse in der Stichprobe sind nicht abgebildet.
- **L-Shaped zeigt Struktur, nicht Tempo.** Auf diesem Problem schlägt die erweiterte Form beide Zerlegungen; wer den Gewinn der Zerlegung sucht, braucht deutlich größere oder ganzzahlige Probleme.

## Verifikation

- **Kern:** Stufe-2-Dualpreise an der Mini-Instanz von Hand gerechnet und gegen finite Differenzen, Ziehung deterministisch, Lücke und Optimismus nie negativ, volle Referenz gibt Lücke null.
- **Orakel (`tests/test_oracle_saa.py`):** dasselbe Modell als eigenes LP in OR-Tools (GLOP) für Stichprobenpläne mit und ohne Umlagerung (1e-7); ein Standort gegen das empirische Quantil (Sortieren statt LP);
  L-Shaped gegen GLOP und die erweiterte Form; Jensen: der mittlere Optimalwert liegt unter den Kosten des besten Plans.
- **Claims (`tests/test_claims.py`):** Rate, Optimismus gegen Lücke, Schiefe, Streuung des Optimalwerts, Plan gegen Kosten, Szenarienbedarf je Fall, L-Shaped-Kennzahlen.
- **Oberfläche:** AppTest-Rauchtest (jeder Button, jeder Regler am Minimum und Maximum), Experiment- und L-Shaped-Knopf, Footer.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `app.py` | Streamlit-App |
| `saa_rng.py` | SplitMix64, Standardnormale per Inversion |
| `saa_scenario.py` | Instanz und Nachfrage-Szenarien (wie in der Wurzel) |
| `saa_algorithm.py` | Kern: Stufe-2-Block, ein LP je Informationsstruktur |
| `saa_lshaped.py` | L-Shaped, Einzel- und Mehrfachschnitt |
| `saa_evaluation.py` | Referenz, Ziehung, Experiment, Verdikt |
| `saa_constants.py` | Regler-Grenzen, feste Annahmen, Farben, Presets |
| `saa_presets.py` | Permalink (Begrenzen, Einrasten), Presets, Zufalls-Seed-Buttons |
| `saa_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `tools/measure_stueck2.py` | Messreihe für README und Claims |
| `tests/` | Mini-Instanz, Orakel, Claims, Presets, AppTest-Smoke-Test, Footer |

## Bewusst nicht umgesetzt

- **Obergrenzen-Schätzer der Lücke** (Mak, Morton & Wood): würde zeigen, wie man die Lücke ohne Referenz abschätzt; hier ist die Referenz bekannt, deshalb wird die Lücke direkt gemessen.
- **Verteilungsrobuste Varianten** und **Risikomaße:** andere Fragen als die nach der Stichprobengröße.
- **Varianzreduktion** (antithetische Ziehungen, geschichtete Stichproben): senkt die Streuung bei gleicher Szenarienzahl, ist ein eigenes Thema.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, NumPy und SciPy.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [Unsicherheit: von EVPI bis rollierend](https://sebastianhanisch.net/konzepte-optimierung-unsicherheit.html).
