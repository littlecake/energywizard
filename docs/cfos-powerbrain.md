# cFos Power Brain through Home Assistant

Rescan devices after installing the discovery update, select the suggested generic
charger, and review its entities before saving. This supports the
[mb-software Powerbrain integration](https://github.com/mb-software/homeassistant-powerbrain).

Discovery requires a cFos/Power Brain device with these entities:

| Entity | Purpose |
| --- | --- |
| State sensor | Connection/charging status, including the integration's numbered states |
| Charging Enabled switch | Start/stop charging |
| Current Limit Override number, in A | Session current limit |

Charging Power (W or kW) and Current L1 (A) are optional measurements. L1 is
reported as one phase's measured current, not the sum of all phases. The integration
converts its ampere override into the charger's underlying milliampere interface.
A number exposed in mA is deliberately not mapped as an ampere control.

Charging Rules Enabled, User Rules Enabled and Maximum Current are not selected.
If required entities are missing, inspect the HA integration and rescan after they
are available. OCPP devices retain their existing OCPP discovery path.

Verification covers discovery, status normalization, generated configuration and
mocked HA service calls. Real charger operation has not been hardware tested.
