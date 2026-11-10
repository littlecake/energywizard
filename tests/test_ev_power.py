import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "smartbox"))
import ev_power


def test_without_max_charge_kw_matches_old_formula():
    for phases in (1, 3):
        for kw in (1.4, 3.7, 6.9, 11.0):
            old = int(round((kw * 1000) / (230 * phases)))
            assert ev_power.amps_for_kw(kw, None, 16, phases) == old


def test_two_phase_car_gets_realistic_amps():
    # ID.4-like: 7.4 kW at 16 A. Old maths (3 phases) would say 10.7 A for 7.4 kW; correct is 16 A.
    assert ev_power.amps_for_kw(7.4, 7.4, 16, 3) == 16
    assert ev_power.amps_for_kw(3.7, 7.4, 16, 3) == 8


def test_roundtrip_planner_and_engine_agree():
    kpa = ev_power.kw_per_amp(7.4, 16, 3)
    assert abs(6 * kpa - 2.775) < 1e-9          # planner min power = 6 A
    assert ev_power.amps_for_kw(6 * kpa, 7.4, 16, 3) == 6


def test_bad_values_fall_back_to_old_behaviour():
    for bad in (None, 0, -3, "x", ""):
        assert ev_power.kw_per_amp(bad, 16, 3) == 230 * 3 / 1000.0
    assert ev_power.kw_per_amp(7.4, 0, 3) == 230 * 3 / 1000.0


def test_zero_or_negative_kw_is_zero_amps():
    assert ev_power.amps_for_kw(0, 7.4, 16, 3) == 0
    assert ev_power.amps_for_kw(-1, 7.4, 16, 3) == 0
    assert ev_power.amps_for_kw(None, 7.4, 16, 3) == 0
