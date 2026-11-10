"""Named catalog values extend # without changing Swedish defaults or numeric lookup."""
import unittest
from unittest.mock import patch
import i18n_py as I


class NamedMessages(unittest.TestCase):
    def check(self, source, expected, catalog, lang='cs'):
        with patch.object(I, '_dict', return_value=catalog):
            self.assertEqual(I.tr(source, lang), expected)

    def test_phone_name_kept(self):
        self.check('Första telefonen i Home Assistant (mobile_app_michal_ipad)',
                   'První telefon (mobile_app_michal_ipad)',
                   {'Första telefonen i Home Assistant ({name})': 'První telefon ({name})'})

    def test_currency_and_number_are_kept(self):
        self.check('Avgifter vid köp (Kč/kWh, inkl. moms)', 'Poplatky (Kč/kWh)',
                   {'Avgifter vid köp ({currency}/kWh, inkl. moms)': 'Poplatky ({currency}/kWh)'})

    def test_reordering(self):
        self.check('Kontakt mellan HA och bilen', 'Auto bilen, server HA',
                   {'Kontakt mellan {server} och {car}': 'Auto {car}, server {server}'})

    def test_repeated_values_must_agree(self):
        d = {'Valuta {unit} och {unit}': 'Měna {unit} a {unit}'}
        self.check('Valuta Kč och Kč', 'Měna Kč a Kč', d)
        self.check('Valuta Kč och EUR', 'Valuta Kč och EUR', d)

    def test_invalid_translation_is_ignored(self):
        self.check('Kontakt med HA', 'Kontakt med HA', {'Kontakt med {name}': 'Kontakt {wrong}'})

    def test_literals_are_escaped(self):
        d = {'Pris ({unit}): {value}.': 'Cena ({unit}): {value}.'}
        self.check('Pris (Kč): -1,25.', 'Cena (Kč): -1,25.', d)
        self.check('Pris xKčx: -1,25x', 'Pris xKčx: -1,25x', d)

    def test_swedish_is_unchanged(self):
        self.check('Kontakt med HA', 'Kontakt med HA', {'Kontakt med {name}': 'Connected to {name}'}, 'sv')

    def test_numeric_hash_unchanged(self):
        self.check('Laddar 3,7 kW', 'Charging 3.7 kW', {'Laddar # kW': 'Charging # kW'}, 'en')

    def test_english_legacy_rule_unchanged(self):
        self.check('GPS: Tesla närmar sig hemmet! (Avstånd: 2 km)',
                   'GPS: Tesla is approaching home! (Distance: 2 km)', {}, 'en')

    def test_short_service_template(self):
        self.check('till notify.mobile_app_michal', 'pro notify.mobile_app_michal', {'till {service}': 'pro {service}'})


if __name__ == '__main__':
    unittest.main()
