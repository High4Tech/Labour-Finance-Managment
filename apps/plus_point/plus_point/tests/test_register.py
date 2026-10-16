"""Native registers use this pure verification before the ERPNext integration run."""
import unittest
from decimal import Decimal
from plus_point.finance import day_units, daily_amounts


class RegisterRulesTests(unittest.TestCase):
    def test_zero_day_cost_is_zero(self):
        self.assertEqual(daily_amounts(2000, 3000, 0), (Decimal('0.00'), Decimal('0.00')))

    def test_half_day(self):
        self.assertEqual(daily_amounts(2000, 3000, '0.5'), (Decimal('1000.00'), Decimal('1500.00')))

    def test_one_day(self):
        self.assertEqual(daily_amounts(2000, 3000, '1'), (Decimal('2000.00'), Decimal('3000.00')))

    def test_bad_day_values_rejected(self):
        for value in ['nan', '-1', '1.5', '0.25']:
            with self.assertRaises(ValueError):
                day_units(value)


if __name__ == '__main__':
    unittest.main()
