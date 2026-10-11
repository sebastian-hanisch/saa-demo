"""Messreihe für README und tests/test_claims.py (Python: _venvs/test). Gibt alle Zahlen aus, die im README stehen."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import saa_constants as C  # noqa: E402
import saa_evaluation as ev  # noqa: E402


def main():
    for name, p in C.PRESETS.items():
        settings = ev.Settings(**p)
        inst = ev.build_instance(settings)
        ref = ev.reference(inst)
        d = ev.one_draw(ref, settings.s, ev.draw_seed(settings.draw, 0, settings.s))
        print(f"== {name}: f* {ref.f_star:.1f}; eine Ziehung S={settings.s}: z {d.z:.1f} f(x_S) {d.f_true:.1f} "
              f"Lücke {d.gap_pct:.2f} % Bias {d.bias_pct:.2f} % z-Fehler {d.z_error_pct:+.1f} % Planabw. {d.plan_dev_pct:.1f} % -> {ev.verdict_of(d)}")
        t = time.time()
        rows = ev.experiment(settings)
        print(f"   Experiment {time.time() - t:.0f} s")
        for r in rows:
            print(f"   S={r['s']:>3}: Lücke {r['gap']:.2f} % (p10 {r['gap_p10']:.2f}, p90 {r['gap_p90']:.2f}) Bias {r['bias']:.2f} % "
                  f"z-Fehler Mittel {r['z_mean']:+.1f} sd {r['z_sd']:.1f} % Planabw. {r['plan_dev']:.1f} %")
        print("   kleinste S mit mittlerer Lücke <= 1 %:", ev.smallest_s_for_gap(rows), flush=True)
    print("== L-Shaped (Voreinstellung)")
    for size in C.LSHAPED_SIZES:
        c = ev.lshaped_comparison(ev.Settings(), size)
        print(f"   S={size}: erweitert {c['extensive']:.3f} ({c['t_extensive']:.2f} s) | Einzel {c['single'].objective:.3f} it {c['single'].iterations} "
              f"Schnitte {c['single'].cuts} {c['single'].seconds:.2f} s | Mehrfach {c['multi'].objective:.3f} it {c['multi'].iterations} "
              f"Schnitte {c['multi'].cuts} {c['multi'].seconds:.2f} s", flush=True)


if __name__ == "__main__":
    main()
