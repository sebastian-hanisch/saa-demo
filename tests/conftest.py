"""Gemeinsame Fixtures: die Mini-Instanz, an der jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from saa_scenario import Instance  # noqa: E402


def make_mini(transfer: bool) -> Instance:
    """Zwei Standorte: Mittel 100 und 60, Vorhaltung 1, Zukauf 2 (Grenze 50 und 30), Fehlmenge 3, Umlagerung 0,5, kein Budget."""
    return Instance(
        mu=(100.0, 60.0), cap_cost=1.0, spot=(2.0, 2.0), unmet=3.0, spot_limit=(50.0, 30.0),
        transfer_cost=((0.0, 0.5), (0.5, 0.0)), transfer=transfer, budget=1e9, sigma=0.3, rho=0.4,
    )


@pytest.fixture
def mini():
    return make_mini(True)


@pytest.fixture
def mini_no_transfer():
    return make_mini(False)
