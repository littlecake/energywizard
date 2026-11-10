"""ev_block.py - enkelblock-laddning (evs[].charge_block: single).

Planeraren (decisions.calculate_ev_charge_plan) väljer annars de billigaste 15-minutersluckorna var för sig,
vilket kan ge många korta start/stopp. Några bilar (och laddare) mår bättre av ETT sammanhängande fönster.

contiguous_slot_order() ger den ordning planeraren går igenom luckorna i:
  1. det billigaste sammanhängande fönstret som ryms (längd = energin / bilens maxeffekt, avrundat uppåt),
     mätt som summan av luckornas score (lägre = billigare); vid lika summa vinner det SENARE fönstret
     (bilen står kortare tid med laddad batteri innan avresa),
  2. sedan växer fönstret åt det billigare hållet, en lucka i taget, så att eventuell rest (om någon lucka
     inte kan ta full effekt p.g.a. effektvakten) hamnar intill blocket,
  3. sist övriga luckor efter score (bara om blocket inte räcker - säkerhetsnät, då är det inte längre ett block).
Returnerar None om inget sammanhängande fönster av rätt längd finns (planeraren går då tillbaka till
kvartsvis planering, så att bilen hellre blir laddad i flera delar än inte alls).

Rena funktioner utan I/O - testas i tests/test_ev_block.py.
"""
import math
from datetime import timedelta


def contiguous_slot_order(slots, kwh_needed, car_max_kw, slot_minutes=15):
    """slots: DataFrame med kolumnerna 't_slot' och 'score' (index = planeringens radindex). Returnerar en lista med
    index i den ordning luckorna ska fyllas, eller None."""
    if slots is None or len(slots) == 0 or kwh_needed <= 0 or car_max_kw <= 0:
        return None
    df = slots.sort_values("t_slot")
    index = df.index.tolist()
    times = df["t_slot"].tolist()
    scores = [float(s) for s in df["score"].tolist()]
    step = timedelta(minutes=slot_minutes)

    runs, run_start = [], 0                      # sammanhängande körningar (15-minutersluckor utan hål)
    for pos in range(1, len(times) + 1):
        if pos == len(times) or (times[pos] - times[pos - 1]) != step:
            runs.append((run_start, pos))
            run_start = pos

    kwh_per_slot = car_max_kw * slot_minutes / 60.0
    needed = max(1, math.ceil(round(kwh_needed / kwh_per_slot, 6)))

    best = None
    for run_start, run_end in runs:
        if run_end - run_start < needed:
            continue
        window = sum(scores[run_start:run_start + needed])
        for start in range(run_start, run_end - needed + 1):
            if start > run_start:
                window += scores[start + needed - 1] - scores[start - 1]
            key = (round(window, 9), -start)
            if best is None or key < best[0]:
                best = (key, start, run_start, run_end)
    if best is None:
        return None

    _, start, run_start, run_end = best
    order = list(range(start, start + needed))
    left, right = start - 1, start + needed
    while left >= run_start or right < run_end:
        take_left = right >= run_end or (left >= run_start and scores[left] < scores[right])
        if take_left:
            order.append(left)
            left -= 1
        else:
            order.append(right)
            right += 1
    used = set(order)
    rest = sorted((p for p in range(len(index)) if p not in used), key=lambda p: scores[p])
    return [index[p] for p in order + rest]
