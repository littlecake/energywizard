# Named catalog values (optional extension)

EnergyWizard keeps Swedish source texts and the existing JSON catalogs. Numeric `#` placeholders and the existing English fallback rules remain unchanged. No UI or control code must adopt a new framework.

A catalog can additionally describe a dynamic string using named values:

```json
{
  "Första telefonen i Home Assistant ({name})": "First phone in Home Assistant ({name})",
  "Avgifter vid köp ({currency}/kWh, inkl. moms)": "Buying fees ({currency}/kWh, incl. VAT)"
}
```

The browser and Python translator use the same matching rules. Values such as entity IDs, user names and currency symbols are preserved. Translators may reorder values; every named value must remain present. Invalid templates are ignored. Repeated values must match, literal regex punctuation is escaped, matching is anchored and limited to catalog-declared templates. Swedish remains the source and is returned unchanged.

This closes observed gaps in country/fee labels and phone-selection messages without adding a Czech-only runtime branch. The English catalog receives corresponding entries. Czech additions are included in the maintained fork; the initial Czech catalog is proposed separately in PR #238.

Validation: 10 Python cases, 21 JavaScript cases, and 1,885 unchanged legacy catalog cases compared against the original JS runtime. No PostgreSQL or HA access is needed for these translation tests.

Run `PYTHONPATH=smartbox python -m unittest discover -s tests -p test_i18n_named.py` and `node scripts/test_i18n_named.cjs`. The JS runner can also accept original runtime and original catalog paths as arguments for before/after regression comparison.
