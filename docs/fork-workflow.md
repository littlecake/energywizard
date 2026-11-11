# Fork contributions and language policy

This fork adapts EnergyWizard to Czech electricity contracts while preserving the
upstream architecture. See [Czech tariffs and HDO](czech-ote-hdo.md) for behavior,
configuration and validation limits, and the [English release notes](../ha-addon/smartbox/CHANGELOG.md)
for the changes shipped in each fork version.

## Languages

- Every new user-facing label, hint, validation message and installation guide
  must work in Czech, English and Swedish in the same change.
- Follow upstream's existing approach: Swedish UI source strings, an English
  catalog and a Czech catalog. Swedish displays the source text; do not add a
  second Swedish catalog or introduce Czech-only UI text in the source code.
- Preserve the names and values of entities, currencies, numbers and template
  placeholders. Check dynamic labels with Kč as well as kr, including after
  changing the country or purchase mode.
- Use English for new diagnostics and background messages that cannot follow a
  selected language. Use English for new technical documentation, commit and PR
  messages, release notes and code comments. User-requested Czech documentation
  may accompany the English documentation.
- Validation errors displayed in the UI belong in the translation catalogs.
  Keep their Swedish lookup keys consistent with upstream's translation system.
- Existing upstream translated logs keep their language selection. Do not change
  their source strings merely to make them English, or rewrite upstream history.
- Keep new fork release notes in English in the add-on CHANGELOG. Retain the
  original upstream release history and distinguish fork changes clearly.

## Branches and upstream review

`main` contains the personal HA build, including forced shadow mode and fork
packaging. Upstream proposals must use separate branches based on upstream/main,
with no personal deployment settings or hardware configuration.

The initial Czech catalog is proposed in [PR #238](https://github.com/murre87/energywizard/pull/238).
Named catalog values are proposed separately in [PR #240](https://github.com/murre87/energywizard/pull/240).
Pricing and HDO work remains in this fork. The existing tariff feature branch is
a starting point; the latest changes on main must be isolated and reviewed before
opening a pricing PR. Do not send the fork's entire main branch upstream.

To bring in upstream changes: fetch upstream/main, merge it into fork main,
resolve conflicts, run relevant checks, then increase the add-on version before
updating HA. Do not discard fork commits. Upstream synchronization and deployment
are manual. Passing focused checks does not replace the upstream PostgreSQL suite.

## Svenska

Alla nya texter i gränssnittet ska fungera på svenska, engelska och tjeckiska.
Vi behåller svenska källtexter och projektets befintliga översättningssystem;
engelska och tjeckiska kataloger uppdateras samtidigt. Namn, valutor och platshållare
bevaras. Nya tekniska loggar utan språkval, dokumentation, commit-meddelanden,
PR-beskrivningar och versionsanteckningar skrivs på engelska.

Tjeckiska elavtal och HDO är valfria landsinställningar. Forkens HA-paketering och
tvingade skuggläge hålls åtskilda från förslag till upstream. Varje förslag ska vara
begränsat, granskningsbart och verifierat; befintlig svensk funktion ska bevaras.

České pokyny: [Vlastní instalace a příspěvky autorovi](fork-workflow-cs.md).
