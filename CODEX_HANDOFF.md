# EnergyWizard fork handoff

Read `AGENTS.md` and `docs/fork-workflow.md` before changing this repository.
This file transfers project context; it is not an export of the entire chat.
Refresh GitHub PR status and the installed HA version before continuing.

## Repositories and scope

- Personal fork: https://github.com/littlecake/energywizard
- Upstream: https://github.com/murre87/energywizard
- Fork `main` contains Czech tariffs, personal HA packaging and forced shadow mode.
- Upstream contribution branches start from upstream/main. Never submit the
  personal fork's entire main branch as a contribution.
- Prefer existing maintained Home Assistant integrations. Keep changes focused,
  preserve existing countries/devices, and distinguish synthetic tests from real
  hardware verification. Do not introduce another battery optimizer.

## Language policy

All new UI labels, status/error messages and setup instructions must support
Swedish, English and Czech in the same change. Follow the existing translator:
Swedish source strings plus English/Czech catalogs. Preserve entity IDs, sensor
names and placeholders. New technical documentation, non-localized background
messages, commit/PR descriptions and release notes are English.

## Published work

- Czech translation: upstream PR #238, merged.
- Named translation values: draft PR #240,
  `fix/translatable-dynamic-messages`.
- Hybrid inverter discovery: draft PR #247, `fix/hybrid-solar-discovery`.
  Prevents grid/battery/load sensors being selected as PV. This isolated fix has
  not yet been applied to fork main. The affected installation's saved solar
  mapping was corrected separately; do not overwrite it with wizard defaults.
- Solcast through HA: draft PR #248, `feat/solcast-ha-forecast`.
  Feature commit: `57d5fbd1f9cb1af7f8afb8127b1a9f7f8bebfc98`.
- Fork release `1.2.65-cz.5` includes Solcast and the existing Czech work.
  Release commit: `a9878c438097af6affb77b7e9ccbb655befd1153`.

PRs: https://github.com/murre87/energywizard/pull/240,
https://github.com/murre87/energywizard/pull/247,
https://github.com/murre87/energywizard/pull/248.

## Solcast design

See `docs/solcast-ha.md`. The adapter reads aggregate daily sensor attributes
`detailedForecast` (30-minute average kW) or `detailedHourly` (hourly average kW)
from HA. It does not call Solcast, store another API key or trigger updates.
Settings are `solar_forecast_source` (`internal` / `solcast_ha`) and
`solar_forecast_entities`, stored through `ew_settings`.

Zero is valid. Missing, stale (>36 hours), conflicting or uncovered intervals
fall back to the existing internal model. Do not sum aggregate and rooftop
sensors. Preserve native quarter-hour planning and weighted hourly integration.
Clear-sky references and measured PV inputs remain separate from forecasts.

## Personal HA deployment

Only one personal EnergyWizard add-on should be installed:
`04683fe6_smartbox`, named EnergyWizard CZ (Koláček fork).
Docker forces `SHADOW_MODE=true`; preserve that protection. This deployment must
not send hardware commands. Updating an existing add-on preserves its data;
never uninstall/reinstall it as an update procedure.

Deployment verified on 2026-11-10: HA reports `1.2.65-cz.5` and the add-on is
running. The live Solar page selects Solcast via HA, all seven aggregate daily
sensors are selected, and the adapter reports data available. At night measured
PV and the current forecast are both 0.00 kW, with 2.0 kWh measured today. The
Settings page confirms shadow mode is enabled and its checkbox is disabled
because `SHADOW_MODE` is forced by the environment. The Supervisor update/build
completed successfully. Daytime forecast accuracy and the complete application
regression suite remain unverified.

The owner provides the HA URL/access separately. Do not commit connection
details, tokens, passwords, household configuration or real telemetry. A partial
HA backup of the add-on was made before the cz.5 update; use HA's backup UI for
recovery. Also preserve the separate solar-configuration backup.

## Validation and remaining work

- 15 focused Solcast tests and 87 translation checks passed locally.
- Python compilation and JavaScript syntax checks passed.
- Safari desktop preview verified source switching, missing-selection validation,
  saving, translated status and Czech installation instructions. This used a
  synthetic API and the real validator, not the running FastAPI application.
- The add-on Docker build runs the new Solcast tests together with the existing
  Czech tariff and named-translation tests using real installed dependencies.
- The complete upstream PostgreSQL suite has not been run in this session.
- Keep PRs as drafts until broader integration checks and maintainer feedback
  justify review. No PR has been merged by this assistant.

## Continuing in Codex

Use a complete clone of the fork, not a partial source snapshot from the old chat
workspace. Read this file and AGENTS.md, inspect the current branch/status, then
continue the owner's specific request. Upstream synchronization is manual; merge
upstream/main into fork main, retain fork commits, resolve conflicts and validate
before increasing the add-on version and deploying.

Do not assume old test totals, PR states or installation status are still current.
