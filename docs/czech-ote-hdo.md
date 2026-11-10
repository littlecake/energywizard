# Czech OTE prices and optional HDO distribution

This extends the existing country settings, HA price-source adapter, time-of-use
surcharge and shared Python/SQL cost functions. The default remains Swedish spot
pricing; existing installations need no migration. No new control driver, external
price service, credential or HA write is introduced.

## Czech setup

Select Česko / CZ: currency CZK (Kč), default VAT 21%, editable. Select the **raw spot**
electricity sensor supplied by `rnovacek/homeassistant_cz_energy_spot_prices` in HA,
configured in CZK/kWh or Kč/MWh. Its timestamp-to-price attributes contain today and
tomorrow. Do not select a buy/sell template sensor which already includes fees.
No automatic EUR/CZK conversion is performed. Raw Czech spot defaults to excluding
VAT; explicitly select "already includes VAT" if applicable to the chosen source.

The parser accepts the integration's actual top-level timestamp attributes (the
previous generic parser only accepted timestamp dictionaries nested in attributes).
Quarter-hour prices and negative prices are retained. Missing tomorrow data is
retried by the existing price refresh loop; it is never replaced with Swedish data.

## Contracts and distribution

Buy and sell can independently use spot or a fixed price. Fixed buy is the energy
component including VAT. Existing buy fees are added, then optional HDO distribution
and the existing time-of-use surcharge. Fixed sell is the final contract price; the
sell adjustment is still added, without applying VAT again. For spot export with a
contract deduction of 0.30 CZK/kWh, set the sell adjustment to -0.30.

Select a ČEZ HDO `sensor.cez_hdo_schedule_*` schedule from HA. The adapter reads the
explicit future NT/VT intervals, including their timezone offsets. Enter ONLY the
variable distribution rates per kWh incl. VAT; do not copy the HDO app's current
**total** electricity price. Remove the same distribution component from the common
buy fee. Monthly standing charges are not marginal consumption costs and are not
included in this optimizer.

The adapter does not change the tariff or any device in HA. Schedule reads are
cached for 60 seconds. On missing, invalid, overlapping or expired coverage, the
higher configured distribution rate is used. A current NT binary sensor is never
projected over tomorrow. HDO only affects buying. The shared SQL expression uses
the same half-open interval boundaries as the Python calculation. Historical
intervals outside the available schedule conservatively use the higher rate;
this is not an invoice reconstruction system.

The existing time-of-use surcharge and demand-charge settings are preserved. Blank prices are never turned into zero; enabling a fixed contract or HDO requires explicit price values.
Other countries can keep their existing time-of-use schedules; this first adapter
specifically supports the ČEZ HDO schedule format rather than guessing the formats
of unrelated integrations. The fixed-price and distribution options are optional.

## Validation

`python3 scripts/test_cz_tariffs_without_db.py` runs 15 focused unittest cases
against the real tariff/parser code, stubbing unused database imports only.
In the full project environment, run `PYTHONPATH=smartbox python -m unittest discover
-s tests -p test_cz_tariffs.py`, and the existing price-country, source, VAT and
TOU pytest suites. Full upstream PostgreSQL-backed tests require its normal CI
services and dependencies; they were not run on this local partial checkout.

References:
- https://github.com/rnovacek/homeassistant_cz_energy_spot_prices
- https://github.com/Cmajda/ha_cez_distribuce (schedule sensor adapter)
- PPAS 2026 household electricity price list: https://www.ppas.cz/ceniky_data/actual/elektrina/domacnost/100_Spot/EE_Cenik_Spot_PRE_2026-01-01.pdf
