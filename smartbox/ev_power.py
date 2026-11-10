"""ev_power.py - bilens maxeffekt (evs[].max_charge_kw) <-> laddström.

Planeraren och motorn räknade tidigare kW <-> A som 230 V x antal faser (1 eller 3). Det stämmer inte för en bil som
drar två faser (t.ex. ID.4 med tvåfasig ombordladdare: 16 A ger ~7,4 kW, inte 11 kW) eller en som själv begränsar sig.

max_charge_kw = den effekt bilen faktiskt drar när laddaren erbjuder max_a ampere. Då är kW per ampere
max_charge_kw / max_a, oavsett hur många faser bilen drar - och samma tal används åt båda hållen (plan: kW per kvart,
motor: kW -> ampere till laddaren), så planen och laddgränsen hänger ihop.
Utan max_charge_kw är beteendet exakt som förut (230 V x faser).

Rena funktioner utan I/O - testas i tests/test_ev_power.py.
"""

V_PHASE = 230.0


def _pos(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return v if v > 0 else 0.0


def kw_per_amp(max_charge_kw, max_a, phases):
    """kW per ampere (laddarens gräns per fas)."""
    p, a = _pos(max_charge_kw), _pos(max_a)
    if p > 0 and a > 0:
        return p / a
    return V_PHASE * phases / 1000.0


def amps_for_kw(kw, max_charge_kw, max_a, phases):
    """Heltalsampere som motsvarar kw (0 om kw <= 0)."""
    if kw is None or kw <= 0:
        return 0
    return int(round(kw / kw_per_amp(max_charge_kw, max_a, phases)))
