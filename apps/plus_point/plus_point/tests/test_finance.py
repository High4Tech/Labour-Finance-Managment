import unittest
from decimal import Decimal

from plus_point.finance import day_units, daily_amounts, project_gross_contribution, money


class FinanceTests(unittest.TestCase):
    def test_daily_contract(self):
        self.assertEqual(daily_amounts(1800, 2800, 1), (Decimal("1800.00"), Decimal("2800.00")))
        self.assertEqual(project_gross_contribution("Daily", [(1800, 2800)] * 10)["gross_contribution_before_other_costs"], Decimal("10000.00"))

    def test_fixed_contract_does_not_bill_days(self):
        data=project_gross_contribution("Fixed",[(1800,0)] * 20,[30000,40000])
        self.assertEqual(data["earned_revenue"],Decimal("70000.00"))
        self.assertEqual(data["labour_cost"],Decimal("36000.00"))

    def test_half_day(self):
        self.assertEqual(daily_amounts(1801.25,2801.25,0.5),(Decimal("900.63"),Decimal("1400.63")))

    def test_invalid_fraction(self):
        for bad in [0.1,0.6,1.5,-1,"NaN"]:
            with self.assertRaises(ValueError): day_units(bad)

    def test_invalid_currency(self):
        for bad in ["nan","Infinity","bad"]:
            with self.assertRaises(ValueError):money(bad)

    def test_no_double_count_in_fixed(self):
        daily=[(1800,2000)]*3
        result=project_gross_contribution("Fixed",daily,[10000])
        self.assertEqual(result["earned_revenue"],Decimal("10000.00"))


if __name__=="__main__": unittest.main()
