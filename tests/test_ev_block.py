import os, sys
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "smartbox"))
import ev_block


def make(scores, start=datetime(2026, 11, 7, 0, 0), skip=()):
    rows, t = [], start
    for i, s in enumerate(scores):
        if i not in skip:
            rows.append({"t_slot": t, "score": s})
        t += timedelta(minutes=15)
    return pd.DataFrame(rows)


def times(df, order):
    return [df.loc[i, "t_slot"] for i in order]


def test_picks_cheapest_contiguous_window():
    df = make([5, 4, 1, 1, 1, 4, 5, 2, 9, 9])           # cheapest 3-slot run is slots 2..4
    order = ev_block.contiguous_slot_order(df, kwh_needed=2.0, car_max_kw=3.0)   # 0.75 kWh/slot -> 3 slots
    assert order[:3] == [2, 3, 4]


def test_does_not_pick_scattered_cheap_slots():
    df = make([1, 9, 1, 9, 1, 9, 2, 2, 2, 9])           # three cheap slots exist but are scattered
    order = ev_block.contiguous_slot_order(df, kwh_needed=2.0, car_max_kw=3.0)
    assert sorted(order[:3]) == [6, 7, 8]


def test_gap_breaks_contiguity():
    df = make([1, 1, 1, 1, 1, 1], skip=(2,))            # a missing slot splits the run into 2 + 3
    order = ev_block.contiguous_slot_order(df, kwh_needed=2.0, car_max_kw=3.0)
    ts = times(df, order[:3])
    assert all(b - a == timedelta(minutes=15) for a, b in zip(ts, ts[1:]))


def test_tie_prefers_later_window():
    df = make([1, 1, 1, 1, 1, 1])
    order = ev_block.contiguous_slot_order(df, kwh_needed=1.5, car_max_kw=3.0)   # 2 slots
    assert order[:2] == [4, 5]


def test_expansion_stays_adjacent_to_block():
    df = make([9, 9, 3, 1, 1, 3, 9, 9])
    order = ev_block.contiguous_slot_order(df, kwh_needed=1.5, car_max_kw=3.0)   # block = slots 3,4
    assert order[:2] == [3, 4]
    assert set(order[2:4]) == {2, 5}                     # next two are the neighbours, not slot 0/1/6/7


def test_none_when_no_window_long_enough():
    df = make([1, 1, 1])
    assert ev_block.contiguous_slot_order(df, kwh_needed=5.0, car_max_kw=3.0) is None


def test_none_on_empty_or_zero_need():
    assert ev_block.contiguous_slot_order(make([]), 1.0, 3.0) is None
    assert ev_block.contiguous_slot_order(make([1, 1]), 0.0, 3.0) is None


def test_every_slot_appears_exactly_once():
    df = make([5, 4, 1, 1, 1, 4, 5, 2, 9, 9])
    order = ev_block.contiguous_slot_order(df, kwh_needed=2.0, car_max_kw=3.0)
    assert sorted(order) == sorted(df.index.tolist())
