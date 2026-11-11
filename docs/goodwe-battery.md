# GoodWe battery mode discovery

EnergyWizard's GoodWe preset uses the Home Assistant **Inverter operation mode** select. Available options vary by integration, inverter family, and firmware.

A new discovery scan reads the select's actual `options` attribute. The preset only suggests these known mappings when those exact options are present:

| EnergyWizard intent | Home Assistant option |
|---|---|
| Auto / normal operation | `general` |
| Charge | `eco_charge` |
| Discharge | `eco_discharge` |

`general` must be available before the preset suggests any control modes, so there is a known normal-operation mapping. When the option list is missing, invalid, or lacks `general`, the suggestion retains monitoring entities but has no automatic control mapping. If only `general` exists, charging/discharging are not offered.

`backup`, `eco`, and `peak_shaving` are not guessed substitutes for charging or holding. Their behavior is not established by their names alone. The discovery card displays a note explaining the capability check and remaining verification needs.

## Existing configurations

This changes new discovery suggestions and generated configuration; it does not rewrite previously saved manual mode mappings. After an HA integration/firmware change, rescan and review the generated mapping against the select's current options. Older cached discovery results without option metadata need a fresh scan.

The presence of `eco_charge` or `eco_discharge` proves only that HA advertises those choices. It does not prove that firmware performs the requested operation or honors the configured power and SOC limits. In particular, the wider compatibility problem reported in [#181](https://github.com/murre87/energywizard/issues/181) still needs the affected inverter model/firmware, HA integration/version, advertised options, and a verified alternative control path. This safeguard does not resolve those upstream behaviors.
